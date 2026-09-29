"""Run Phase 3 direct offer regression and classification experiments."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import pandas as pd
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
)
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
)

from zephyrtrade.direct import CapacityBracketEncoder, probability_quantile_offers
from zephyrtrade.evaluate import (
    realized_market_revenue,
    regression_metrics,
    revenue_metrics,
)
from zephyrtrade.optimize import (
    perfect_foresight_offers,
    solve_single_period_offer_lp,
)
from zephyrtrade.phase2 import load_phase2_data
from zephyrtrade.preprocessing import FEATURE_COLUMNS, PRICE_COLUMNS, TARGET_COLUMN

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

STRATEGY_LABELS = {
    "perfect_foresight": "Perfect foresight",
    "indirect_locally_weighted": "Model 1: predict then optimize",
    "direct_regression": "Model 2: continuous regression",
    "direct_classification": "Model 2: bid-bracket classification",
}


@dataclass(frozen=True)
class Phase3Config:
    """Configure deterministic direct-strategy training and evaluation."""

    processed_data_dir: Path = Path("data/processed")
    phase2_prediction_path: Path = Path("artifacts/phase2/test_predictions.csv.gz")
    output_dir: Path = Path("artifacts/phase3")
    figure_dir: Path = Path("docs/figures")
    inner_train_fraction: float = 0.8
    regression_quantiles: tuple[float, ...] = (0.2, 0.35, 0.5, 0.65, 0.8)
    decision_quantiles: tuple[float, ...] = (0.2, 0.35, 0.5, 0.65, 0.8)
    leaf_candidates: tuple[int, ...] = (15, 31)
    bracket_candidates: tuple[int, ...] = (6, 10, 15)
    max_iter: int = 250
    learning_rate: float = 0.06
    min_samples_leaf: int = 30
    l2_regularization: float = 0.1
    random_state: int = 42


def _market_vectors(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    """Extract aligned target, price, and capacity vectors from a split."""
    return {
        "actual": frame[TARGET_COLUMN].to_numpy(dtype=float),
        "day_ahead": frame[PRICE_COLUMNS[0]].to_numpy(dtype=float),
        "up_regulation": frame[PRICE_COLUMNS[1]].to_numpy(dtype=float),
        "down_regulation": frame[PRICE_COLUMNS[2]].to_numpy(dtype=float),
        "capacity": frame["capacity_mw"].to_numpy(dtype=float),
    }


def _perfect_targets(frame: pd.DataFrame) -> np.ndarray:
    """Construct perfect-foresight labels with the exact deterministic LP rule."""
    market = _market_vectors(frame)
    return perfect_foresight_offers(
        market["actual"],
        market["day_ahead"],
        market["up_regulation"],
        market["down_regulation"],
        market["capacity"],
    )


def _economic_sample_weights(frame: pd.DataFrame) -> np.ndarray:
    """Weight training examples by the observed imbalance-price spread."""
    spread = frame[PRICE_COLUMNS[1]].to_numpy(dtype=float) - frame[
        PRICE_COLUMNS[2]
    ].to_numpy(dtype=float)
    if (spread <= 0.0).any() or not np.isfinite(spread).all():
        raise ValueError("Economic sample weights require positive finite spreads.")
    return spread / spread.mean()


def _regressor(
    config: Phase3Config,
    max_leaf_nodes: int,
    loss: str,
    quantile: float | None,
) -> HistGradientBoostingRegressor:
    """Build one deterministic continuous-offer candidate."""
    parameters: dict[str, Any] = {
        "loss": loss,
        "learning_rate": config.learning_rate,
        "max_iter": config.max_iter,
        "max_leaf_nodes": max_leaf_nodes,
        "min_samples_leaf": config.min_samples_leaf,
        "l2_regularization": config.l2_regularization,
        "early_stopping": False,
        "random_state": config.random_state,
    }
    if loss == "quantile":
        parameters["quantile"] = quantile
    return HistGradientBoostingRegressor(**parameters)


def _classifier(
    config: Phase3Config,
    max_leaf_nodes: int,
) -> HistGradientBoostingClassifier:
    """Build one deterministic bid-bracket probability model."""
    return HistGradientBoostingClassifier(
        loss="log_loss",
        learning_rate=config.learning_rate,
        max_iter=config.max_iter,
        max_leaf_nodes=max_leaf_nodes,
        min_samples_leaf=config.min_samples_leaf,
        l2_regularization=config.l2_regularization,
        early_stopping=False,
        random_state=config.random_state,
    )


def _score_offer(
    offer_mw: np.ndarray,
    frame: pd.DataFrame,
    target_mw: np.ndarray,
) -> dict[str, float]:
    """Return strategy error and realized-revenue metrics for an offer vector."""
    market = _market_vectors(frame)
    strategy = regression_metrics(target_mw, offer_mw)
    market_metrics = revenue_metrics(
        offer_mw,
        market["actual"],
        market["day_ahead"],
        market["up_regulation"],
        market["down_regulation"],
    )
    market_metrics.pop("interval_revenue_dkk")
    return strategy | market_metrics


def _select_regression(
    x_train: np.ndarray,
    target: np.ndarray,
    train_frame: pd.DataFrame,
    config: Phase3Config,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Select a continuous direct model by inner-holdout realized revenue."""
    boundary = int(len(train_frame) * config.inner_train_fraction)
    if not 0 < boundary < len(train_frame):
        raise ValueError("inner_train_fraction must create two nonempty periods.")
    fit_x, score_x = x_train[:boundary], x_train[boundary:]
    fit_target, score_target = target[:boundary], target[boundary:]
    fit_weights = _economic_sample_weights(train_frame.iloc[:boundary])
    score_frame = train_frame.iloc[boundary:]
    capacity = float(train_frame["capacity_mw"].max())
    candidates = [
        ("squared_error", None),
        *[("quantile", q) for q in config.regression_quantiles],
    ]
    rows: list[dict[str, Any]] = []

    for max_leaf_nodes in config.leaf_candidates:
        for loss, quantile in candidates:
            model = _regressor(
                config,
                max_leaf_nodes=max_leaf_nodes,
                loss=loss,
                quantile=quantile,
            )
            model.fit(fit_x, fit_target, sample_weight=fit_weights)
            offer = np.clip(model.predict(score_x), 0.0, capacity)
            metrics = _score_offer(offer, score_frame, score_target)
            rows.append(
                {
                    "loss": loss,
                    "quantile": quantile,
                    "max_leaf_nodes": max_leaf_nodes,
                    **metrics,
                }
            )

    table = pd.DataFrame(rows).sort_values(
        ["total_revenue_dkk", "rmse_mw"],
        ascending=[False, True],
    )
    selected = table.iloc[0]
    selection = {
        "loss": str(selected["loss"]),
        "quantile": (
            None if pd.isna(selected["quantile"]) else float(selected["quantile"])
        ),
        "max_leaf_nodes": int(selected["max_leaf_nodes"]),
        "inner_holdout_revenue_dkk": float(selected["total_revenue_dkk"]),
        "inner_holdout_rmse_mw": float(selected["rmse_mw"]),
    }
    return selection, table.reset_index(drop=True)


def _select_classification(
    x_train: np.ndarray,
    target: np.ndarray,
    train_frame: pd.DataFrame,
    config: Phase3Config,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Select capacity brackets and probability decision quantile by revenue."""
    boundary = int(len(train_frame) * config.inner_train_fraction)
    fit_x, score_x = x_train[:boundary], x_train[boundary:]
    fit_target, score_target = target[:boundary], target[boundary:]
    fit_weights = _economic_sample_weights(train_frame.iloc[:boundary])
    score_frame = train_frame.iloc[boundary:]
    capacity = float(train_frame["capacity_mw"].max())
    rows: list[dict[str, Any]] = []

    for n_brackets in config.bracket_candidates:
        encoder = CapacityBracketEncoder(n_brackets, capacity).fit(fit_target)
        fit_labels = encoder.transform(fit_target)
        for max_leaf_nodes in config.leaf_candidates:
            model = _classifier(config, max_leaf_nodes)
            model.fit(fit_x, fit_labels, sample_weight=fit_weights)
            probabilities = model.predict_proba(score_x)
            for decision_quantile in config.decision_quantiles:
                labels, offer = probability_quantile_offers(
                    probabilities,
                    model.classes_,
                    encoder,
                    decision_quantile,
                )
                metrics = _score_offer(offer, score_frame, score_target)
                true_labels = encoder.transform(score_target)
                rows.append(
                    {
                        "n_brackets": n_brackets,
                        "max_leaf_nodes": max_leaf_nodes,
                        "decision_quantile": decision_quantile,
                        "accuracy": accuracy_score(true_labels, labels),
                        "macro_f1": f1_score(
                            true_labels,
                            labels,
                            average="macro",
                            zero_division=0,
                        ),
                        **metrics,
                    }
                )

    table = pd.DataFrame(rows).sort_values(
        ["total_revenue_dkk", "rmse_mw"],
        ascending=[False, True],
    )
    selected = table.iloc[0]
    selection = {
        "n_brackets": int(selected["n_brackets"]),
        "max_leaf_nodes": int(selected["max_leaf_nodes"]),
        "decision_quantile": float(selected["decision_quantile"]),
        "inner_holdout_revenue_dkk": float(selected["total_revenue_dkk"]),
        "inner_holdout_rmse_mw": float(selected["rmse_mw"]),
    }
    return selection, table.reset_index(drop=True)


def _load_indirect_offer(
    test_frame: pd.DataFrame,
    phase2_prediction_path: Path,
) -> np.ndarray:
    """Load and rigorously align the Phase 2 winning offer to Phase 3 test rows."""
    path = Path(phase2_prediction_path)
    if not path.exists():
        raise FileNotFoundError(f"Phase 2 test predictions not found: {path}")
    indirect = pd.read_csv(path)
    required = {
        "timestamp_utc",
        "farm_id",
        TARGET_COLUMN,
        "locally_weighted_offer_mw",
        *PRICE_COLUMNS,
    }
    missing = required.difference(indirect.columns)
    if missing:
        raise ValueError(f"Phase 2 predictions are missing columns: {sorted(missing)}")
    indirect["timestamp_utc"] = pd.to_datetime(indirect["timestamp_utc"], utc=True)
    aligned = test_frame[
        ["timestamp_utc", "farm_id", TARGET_COLUMN, *PRICE_COLUMNS]
    ].merge(
        indirect[
            [
                "timestamp_utc",
                "farm_id",
                TARGET_COLUMN,
                *PRICE_COLUMNS,
                "locally_weighted_offer_mw",
            ]
        ],
        on=["timestamp_utc", "farm_id"],
        how="left",
        validate="one_to_one",
        suffixes=("_phase3", "_phase2"),
    )
    if aligned["locally_weighted_offer_mw"].isna().any() or len(aligned) != len(
        test_frame
    ):
        raise ValueError("Phase 2 predictions do not align with the Phase 3 test set.")
    for column in [TARGET_COLUMN, *PRICE_COLUMNS]:
        if not np.allclose(
            aligned[f"{column}_phase3"],
            aligned[f"{column}_phase2"],
            rtol=1e-10,
            atol=1e-10,
        ):
            raise ValueError(f"Phase 2 and Phase 3 disagree on {column}.")
    return aligned["locally_weighted_offer_mw"].to_numpy(dtype=float)


def _explicit_lp_audit(train_frame: pd.DataFrame, target: np.ndarray) -> dict[str, Any]:
    """Verify analytical perfect-foresight labels against sampled explicit LPs."""
    price_strict = (
        train_frame[PRICE_COLUMNS[0]] > train_frame[PRICE_COLUMNS[2]] + 1e-9
    ) & (train_frame[PRICE_COLUMNS[1]] > train_frame[PRICE_COLUMNS[0]] + 1e-9)
    eligible = np.flatnonzero(price_strict.to_numpy())
    audit_count = min(25, eligible.size)
    if audit_count == 0:
        raise ValueError("No strict-price rows are available for the LP target audit.")
    selected = eligible[np.linspace(0, eligible.size - 1, audit_count, dtype=int)]
    explicit = []
    for index in selected:
        row = train_frame.iloc[index]
        solution = solve_single_period_offer_lp(
            np.array([row[TARGET_COLUMN]], dtype=float),
            np.array([1.0]),
            float(row[PRICE_COLUMNS[0]]),
            float(row[PRICE_COLUMNS[1]]),
            float(row[PRICE_COLUMNS[2]]),
            float(row["capacity_mw"]),
        )
        explicit.append(float(solution["offer_mw"]))
    difference = np.abs(np.asarray(explicit) - target[selected])
    return {
        "explicit_lp_rows": audit_count,
        "maximum_explicit_lp_difference_mw": float(difference.max()),
        "vector_target_equals_actual_share": float(
            np.mean(target == train_frame[TARGET_COLUMN].to_numpy(dtype=float))
        ),
    }


def _strategy_comparison(
    test_frame: pd.DataFrame,
    perfect_target: np.ndarray,
    offers: dict[str, np.ndarray],
) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    """Compare direct and indirect strategies on the untouched test period."""
    market = _market_vectors(test_frame)
    rows: list[dict[str, Any]] = []
    interval_revenues: dict[str, np.ndarray] = {}
    for strategy, offer in offers.items():
        metrics = _score_offer(offer, test_frame, perfect_target)
        rows.append(
            {
                "strategy": strategy,
                "label": STRATEGY_LABELS[strategy],
                "model_family": (
                    "oracle"
                    if strategy == "perfect_foresight"
                    else "indirect"
                    if strategy == "indirect_locally_weighted"
                    else "direct"
                ),
                **metrics,
            }
        )
        interval_revenues[strategy] = realized_market_revenue(
            offer,
            market["actual"],
            market["day_ahead"],
            market["up_regulation"],
            market["down_regulation"],
        )
    table = pd.DataFrame(rows)
    table["revenue_rank"] = (
        table["total_revenue_dkk"].rank(method="min", ascending=False).astype(int)
    )
    return table.sort_values("revenue_rank").reset_index(drop=True), interval_revenues


def _plot_results(
    comparison: pd.DataFrame,
    predictions: pd.DataFrame,
    confusion: np.ndarray,
    class_representatives: np.ndarray,
    figure_dir: Path,
) -> dict[str, Path]:
    """Create publication-ready direct-strategy comparison figures."""
    figure_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")
    paths = {
        "revenue_regret": figure_dir / "phase3_strategy_revenue_regret.png",
        "offers": figure_dir / "phase3_offer_timeseries.png",
        "confusion": figure_dir / "phase3_confusion_matrix.png",
        "cumulative_delta": figure_dir / "phase3_cumulative_revenue_delta.png",
    }

    strategies = comparison[comparison["strategy"] != "perfect_foresight"].sort_values(
        "revenue_regret_dkk",
        ascending=False,
    )
    fig, axis = plt.subplots(figsize=(9.0, 4.8))
    axis.barh(
        strategies["label"],
        strategies["revenue_regret_dkk"] / 1_000_000.0,
        color=["#2B7A78", "#D97B29", "#6C5B7B"],
    )
    axis.set_xlabel("Revenue regret versus perfect foresight (million DKK)")
    axis.set_title("Direct and indirect strategy value")
    fig.tight_layout()
    fig.savefig(paths["revenue_regret"], dpi=180)
    plt.close(fig)

    window = predictions.iloc[:120]
    fig, axis = plt.subplots(figsize=(11.0, 5.2))
    axis.plot(
        window["timestamp_utc"],
        window["perfect_foresight_offer_mw"],
        label="Perfect target",
        color="#1F2933",
        linewidth=2.0,
    )
    axis.plot(
        window["timestamp_utc"],
        window["indirect_locally_weighted_offer_mw"],
        label="Indirect",
        color="#2B7A78",
        alpha=0.9,
    )
    axis.plot(
        window["timestamp_utc"],
        window["direct_regression_offer_mw"],
        label="Direct regression",
        color="#D97B29",
        alpha=0.9,
    )
    axis.step(
        window["timestamp_utc"],
        window["direct_classification_offer_mw"],
        where="mid",
        label="Direct brackets",
        color="#6C5B7B",
        alpha=0.85,
    )
    axis.set_ylabel("Offer (MW)")
    axis.set_title("Test-period offers: first 120 hours")
    axis.legend(ncol=2)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(paths["offers"], dpi=180)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(7.2, 6.2))
    image = axis.imshow(confusion, cmap="Blues", vmin=0.0, vmax=1.0)
    tick_labels = [f"{value:.1f}" for value in class_representatives]
    axis.set_xticks(np.arange(len(tick_labels)), tick_labels, rotation=45)
    axis.set_yticks(np.arange(len(tick_labels)), tick_labels)
    axis.set_xlabel("Predicted representative offer (MW)")
    axis.set_ylabel("Perfect-target bracket representative (MW)")
    axis.set_title("Normalized bid-bracket confusion matrix")
    fig.colorbar(image, ax=axis, label="Row share")
    fig.tight_layout()
    fig.savefig(paths["confusion"], dpi=180)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(10.0, 4.8))
    for strategy, label, color in (
        ("direct_regression", "Direct regression", "#D97B29"),
        ("direct_classification", "Direct brackets", "#6C5B7B"),
    ):
        axis.plot(
            predictions["timestamp_utc"],
            predictions[f"{strategy}_minus_indirect_cumulative_dkk"] / 1_000.0,
            label=label,
            color=color,
        )
    axis.axhline(0.0, color="#1F2933", linewidth=0.9)
    axis.set_ylabel("Cumulative revenue minus indirect (thousand DKK)")
    axis.set_title("Incremental value of direct strategies")
    axis.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(paths["cumulative_delta"], dpi=180)
    plt.close(fig)
    return paths


def _json_ready(value: Any) -> Any:
    """Recursively convert result objects to strict JSON-compatible values."""
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def run_phase3(config: Phase3Config) -> dict[str, Path]:
    """Execute Phase 3 and persist direct-strategy models, metrics, and figures."""
    splits, _ = load_phase2_data(config.processed_data_dir)
    train = splits["train"]
    test = splits["test"]
    x_train = train.loc[:, FEATURE_COLUMNS].to_numpy(dtype=float)
    x_test = test.loc[:, FEATURE_COLUMNS].to_numpy(dtype=float)
    train_target = _perfect_targets(train)
    test_target = _perfect_targets(test)
    capacity = float(train["capacity_mw"].max())

    target_audit = _explicit_lp_audit(train, train_target)
    regression_selection, regression_table = _select_regression(
        x_train,
        train_target,
        train,
        config,
    )
    classification_selection, classification_table = _select_classification(
        x_train,
        train_target,
        train,
        config,
    )

    weights = _economic_sample_weights(train)
    direct_regressor = _regressor(
        config,
        regression_selection["max_leaf_nodes"],
        regression_selection["loss"],
        regression_selection["quantile"],
    )
    direct_regressor.fit(x_train, train_target, sample_weight=weights)
    regression_offer = np.clip(direct_regressor.predict(x_test), 0.0, capacity)

    encoder = CapacityBracketEncoder(
        classification_selection["n_brackets"],
        capacity,
    ).fit(train_target)
    train_classes = encoder.transform(train_target)
    direct_classifier = _classifier(
        config,
        classification_selection["max_leaf_nodes"],
    )
    direct_classifier.fit(x_train, train_classes, sample_weight=weights)
    class_probabilities = direct_classifier.predict_proba(x_test)
    predicted_classes, classification_offer = probability_quantile_offers(
        class_probabilities,
        direct_classifier.classes_,
        encoder,
        classification_selection["decision_quantile"],
    )
    true_classes = encoder.transform(test_target)
    classification_metrics = {
        "accuracy": float(accuracy_score(true_classes, predicted_classes)),
        "balanced_accuracy": float(
            balanced_accuracy_score(true_classes, predicted_classes)
        ),
        "macro_f1": float(
            f1_score(
                true_classes,
                predicted_classes,
                average="macro",
                zero_division=0,
            )
        ),
        "class_representatives_mw": encoder.representatives_,
    }
    normalized_confusion = confusion_matrix(
        true_classes,
        predicted_classes,
        labels=np.arange(encoder.n_brackets),
        normalize="true",
    )

    indirect_offer = _load_indirect_offer(test, config.phase2_prediction_path)
    offers = {
        "perfect_foresight": test_target,
        "indirect_locally_weighted": indirect_offer,
        "direct_regression": regression_offer,
        "direct_classification": classification_offer,
    }
    comparison, interval_revenues = _strategy_comparison(
        test,
        test_target,
        offers,
    )
    predictions = test[
        [
            "timestamp_utc",
            "farm_id",
            TARGET_COLUMN,
            "capacity_mw",
            *PRICE_COLUMNS,
        ]
    ].copy()
    predictions["perfect_target_class"] = true_classes
    predictions["predicted_offer_class"] = predicted_classes
    for strategy, offer in offers.items():
        predictions[f"{strategy}_offer_mw"] = offer
        predictions[f"{strategy}_revenue_dkk"] = interval_revenues[strategy]
    for strategy in ("direct_regression", "direct_classification"):
        predictions[f"{strategy}_minus_indirect_cumulative_dkk"] = np.cumsum(
            interval_revenues[strategy] - interval_revenues["indirect_locally_weighted"]
        )

    figure_paths = _plot_results(
        comparison,
        predictions,
        normalized_confusion,
        encoder.representatives_,
        Path(config.figure_dir),
    )
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "regression_selection": output_dir / "regression_selection.csv",
        "classification_selection": output_dir / "classification_selection.csv",
        "strategy_comparison": output_dir / "strategy_comparison.csv",
        "test_predictions": output_dir / "test_direct_predictions.csv.gz",
        "summary": output_dir / "summary.json",
    }
    regression_table.to_csv(paths["regression_selection"], index=False)
    classification_table.to_csv(paths["classification_selection"], index=False)
    comparison.to_csv(paths["strategy_comparison"], index=False)
    predictions.to_csv(
        paths["test_predictions"],
        index=False,
        compression="gzip",
        date_format="%Y-%m-%dT%H:%M:%SZ",
    )
    summary = {
        "phase": 3,
        "configuration": asdict(config),
        "input_rows": {name: len(frame) for name, frame in splits.items()},
        "target_engineering": {
            "definition": "perfect-foresight deterministic-LP offer",
            "analytical_result": (
                "offer equals realized production under down <= day-ahead <= up"
            ),
            **target_audit,
        },
        "regression_selection": regression_selection,
        "classification_selection": classification_selection,
        "classification_test_metrics": classification_metrics,
        "strategy_comparison": comparison.to_dict(orient="records"),
        "figures": figure_paths,
        "evaluation_protocol": {
            "selection": (
                "candidate models selected by realized revenue on the final 20% "
                "of the chronological training split"
            ),
            "final_fit": "selected models refit on the complete training split",
            "test": "untouched chronological test split shared with Phase 2",
            "inference_features": FEATURE_COLUMNS,
            "price_information": (
                "realized prices affect training weights and historical selection "
                "scores but are never model inputs at inference"
            ),
            "indirect_benchmark_caveat": (
                "Phase 2 LP uses realized test price spreads ex post, favoring the "
                "indirect benchmark relative to a deployable forecast-price policy"
            ),
        },
    }
    paths["summary"].write_text(
        json.dumps(_json_ready(summary), indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print("Phase 3 complete.")
    print("Selected direct regression:", regression_selection)
    print("Selected direct classification:", classification_selection)
    print(comparison.to_string(index=False))
    return paths | {f"figure_{key}": value for key, value in figure_paths.items()}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the Phase 3 experiment."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--processed-data-dir",
        type=Path,
        default=Path("data/processed"),
    )
    parser.add_argument(
        "--phase2-prediction-path",
        type=Path,
        default=Path("artifacts/phase2/test_predictions.csv.gz"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/phase3"))
    parser.add_argument("--figure-dir", type=Path, default=Path("docs/figures"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run Phase 3 from the command line."""
    args = _parse_args(argv)
    run_phase3(
        Phase3Config(
            processed_data_dir=args.processed_data_dir,
            phase2_prediction_path=args.phase2_prediction_path,
            output_dir=args.output_dir,
            figure_dir=args.figure_dir,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
