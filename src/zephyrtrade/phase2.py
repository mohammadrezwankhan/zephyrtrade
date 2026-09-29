"""Run the complete Phase 2 indirect forecast-and-optimize experiment."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import matplotlib
import numpy as np
import pandas as pd
from sklearn.linear_model import Lasso, Ridge
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from zephyrtrade.evaluate import regression_metrics, revenue_metrics
from zephyrtrade.models import (
    ClosedFormLinearRegression,
    ClusteredRidgeRegressor,
    GradientDescentLinearRegression,
    LocallyWeightedLinearRegression,
    polynomial_ols_pipeline,
    polynomial_regularized_pipeline,
)
from zephyrtrade.optimize import optimize_offers_from_residuals
from zephyrtrade.preprocessing import FEATURE_COLUMNS, PRICE_COLUMNS, TARGET_COLUMN

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

MODEL_LABELS = {
    "persistence_24h": "24-hour persistence",
    "linear_ols": "Linear OLS",
    "polynomial_ols": "Polynomial OLS",
    "locally_weighted": "Locally weighted linear",
    "ridge_polynomial": "Polynomial Ridge",
    "lasso_polynomial": "Polynomial Lasso",
    "clustered_ridge": "K-means local Ridge",
}


@dataclass(frozen=True)
class Phase2Config:
    """Configure the deterministic Phase 2 backtest."""

    processed_data_dir: Path = Path("data/processed")
    output_dir: Path = Path("artifacts/phase2")
    figure_dir: Path = Path("docs/figures")
    polynomial_degree: int = 2
    local_neighbors: int = 192
    gradient_sample_size: int = 100
    cv_splits: int = 3
    random_state: int = 42


def _load_split(path: Path) -> pd.DataFrame:
    """Load one processed split and restore its UTC timestamp."""
    if not path.exists():
        raise FileNotFoundError(
            f"Processed split not found: {path}. Run zephyr-preprocess first."
        )
    frame = pd.read_csv(path)
    frame["timestamp_utc"] = pd.to_datetime(frame["timestamp_utc"], utc=True)
    return frame


def load_phase2_data(
    processed_data_dir: Path,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    """Load and validate Phase 1 splits and their feature schema."""
    processed_data_dir = Path(processed_data_dir)
    schema_path = processed_data_dir / "feature_schema.json"
    if not schema_path.exists():
        raise FileNotFoundError(
            f"Feature schema not found: {schema_path}. Run zephyr-preprocess first."
        )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if schema["feature_columns"] != FEATURE_COLUMNS:
        raise ValueError("Persisted feature order differs from the package contract.")
    splits = {
        name: _load_split(processed_data_dir / f"{name}_scaled.csv.gz")
        for name in ("train", "validation", "test")
    }
    if not (
        splits["train"]["timestamp_utc"].max()
        < splits["validation"]["timestamp_utc"].min()
        < splits["test"]["timestamp_utc"].min()
    ):
        raise ValueError("Phase 2 input splits are not strictly chronological.")
    return splits, schema


def _gradient_descent_equivalence(
    train_features: np.ndarray,
    train_target: np.ndarray,
    sample_size: int,
) -> dict[str, Any]:
    """Compare batch gradient descent with OLS on evenly spaced observations."""
    if sample_size > train_features.shape[0]:
        raise ValueError("The OLS demonstration sample exceeds the training rows.")
    indices = np.linspace(
        0,
        train_features.shape[0] - 1,
        sample_size,
        dtype=int,
    )
    sample_features = train_features[indices]
    sample_target = train_target[indices]
    closed_form = ClosedFormLinearRegression().fit(sample_features, sample_target)
    gradient_descent = GradientDescentLinearRegression(
        max_iter=500_000,
        tol=1e-11,
    ).fit(sample_features, sample_target)
    closed_predictions = closed_form.predict(sample_features)
    gradient_predictions = gradient_descent.predict(sample_features)
    coefficient_difference = np.concatenate(
        (
            np.array([gradient_descent.intercept_ - closed_form.intercept_]),
            gradient_descent.coef_ - closed_form.coef_,
        )
    )
    max_prediction_difference = float(
        np.max(np.abs(gradient_predictions - closed_predictions))
    )
    return {
        "sample_size": sample_size,
        "sampling": "100 evenly spaced rows across the chronological training set",
        "feature_count": sample_features.shape[1],
        "closed_form_objective": closed_form.objective_,
        "gradient_descent_objective": gradient_descent.objective_,
        "objective_absolute_difference": abs(
            gradient_descent.objective_ - closed_form.objective_
        ),
        "maximum_absolute_coefficient_difference": float(
            np.max(np.abs(coefficient_difference))
        ),
        "maximum_absolute_prediction_difference_mw": max_prediction_difference,
        "gradient_iterations": gradient_descent.n_iter_,
        "gradient_learning_rate": gradient_descent.learning_rate_,
        "gradient_converged": gradient_descent.converged_,
        "identical_within_1e_7_mw": max_prediction_difference <= 1e-7,
    }


def _polynomial_cv_folds(
    train_features: np.ndarray,
    train_target: np.ndarray,
    degree: int,
    split_count: int,
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    """Precompute leakage-safe standardized polynomial folds for alpha search."""
    splitter = TimeSeriesSplit(n_splits=split_count)
    folds: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []
    for fit_indices, score_indices in splitter.split(train_features):
        polynomial = PolynomialFeatures(degree=degree, include_bias=False)
        fit_polynomial = polynomial.fit_transform(train_features[fit_indices])
        score_polynomial = polynomial.transform(train_features[score_indices])
        scaler = StandardScaler().fit(fit_polynomial)
        folds.append(
            (
                scaler.transform(fit_polynomial),
                train_target[fit_indices],
                scaler.transform(score_polynomial),
                train_target[score_indices],
            )
        )
    return folds


def _search_regularization_alpha(
    penalty: Literal["ridge", "lasso"],
    alphas: np.ndarray,
    folds: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
    random_state: int,
) -> tuple[float, pd.DataFrame]:
    """Evaluate an alpha grid with expanding-window time-series validation."""
    rows: list[dict[str, float | str]] = []
    for alpha in alphas:
        fold_rmse: list[float] = []
        for fit_features, fit_target, score_features, score_target in folds:
            if penalty == "ridge":
                estimator: Ridge | Lasso = Ridge(alpha=float(alpha))
            else:
                estimator = Lasso(
                    alpha=float(alpha),
                    max_iter=50_000,
                    tol=1e-5,
                    selection="cyclic",
                    random_state=random_state,
                )
            estimator.fit(fit_features, fit_target)
            prediction = estimator.predict(score_features)
            fold_rmse.append(
                float(np.sqrt(mean_squared_error(score_target, prediction)))
            )
        row: dict[str, float | str] = {
            "penalty": penalty,
            "alpha": float(alpha),
            "mean_cv_rmse_mw": float(np.mean(fold_rmse)),
            "std_cv_rmse_mw": float(np.std(fold_rmse)),
        }
        row.update(
            {
                f"fold_{index}_rmse_mw": value
                for index, value in enumerate(fold_rmse, start=1)
            }
        )
        rows.append(row)
    results = pd.DataFrame(rows).sort_values("alpha").reset_index(drop=True)
    best_row = results.loc[results["mean_cv_rmse_mw"].idxmin()]
    return float(best_row["alpha"]), results


def _select_cluster_count(
    train_features: np.ndarray,
    train_target: np.ndarray,
    cluster_feature_indices: tuple[int, ...],
    random_state: int,
) -> tuple[int, pd.DataFrame]:
    """Select k on an inner chronological holdout without using validation data."""
    inner_cut = int(np.floor(0.80 * train_features.shape[0]))
    fit_features = train_features[:inner_cut]
    fit_target = train_target[:inner_cut]
    score_features = train_features[inner_cut:]
    score_target = train_target[inner_cut:]
    rows: list[dict[str, float | int]] = []
    for cluster_count in range(2, 7):
        estimator = ClusteredRidgeRegressor(
            n_clusters=cluster_count,
            alpha=0.1,
            random_state=random_state,
            cluster_feature_indices=cluster_feature_indices,
        ).fit(fit_features, fit_target)
        prediction = estimator.predict(score_features)
        rows.append(
            {
                "n_clusters": cluster_count,
                "inner_holdout_rmse_mw": float(
                    np.sqrt(mean_squared_error(score_target, prediction))
                ),
                "minimum_cluster_rows": min(estimator.cluster_counts_.values()),
                "maximum_cluster_rows": max(estimator.cluster_counts_.values()),
            }
        )
    results = pd.DataFrame(rows)
    best_cluster_count = int(
        results.loc[results["inner_holdout_rmse_mw"].idxmin(), "n_clusters"]
    )
    return best_cluster_count, results


def _clip_power(prediction: np.ndarray, capacity_mw: float) -> np.ndarray:
    """Enforce physical production limits on a model prediction."""
    return np.clip(np.asarray(prediction, dtype=float), 0.0, capacity_mw)


def _fit_phase2_models(
    splits: dict[str, pd.DataFrame],
    schema: dict[str, Any],
    config: Phase2Config,
) -> tuple[
    dict[str, np.ndarray],
    dict[str, np.ndarray],
    dict[str, Any],
    pd.DataFrame,
    pd.DataFrame,
    dict[str, Any],
]:
    """Train every indirect model and return validation/test predictions."""
    train = splits["train"]
    validation = splits["validation"]
    test = splits["test"]
    x_train = train.loc[:, FEATURE_COLUMNS].to_numpy(dtype=float)
    y_train = train[TARGET_COLUMN].to_numpy(dtype=float)
    x_validation = validation.loc[:, FEATURE_COLUMNS].to_numpy(dtype=float)
    x_test = test.loc[:, FEATURE_COLUMNS].to_numpy(dtype=float)
    capacity_mw = float(train["capacity_mw"].max())

    gd_comparison = _gradient_descent_equivalence(
        x_train,
        y_train,
        config.gradient_sample_size,
    )
    polynomial_folds = _polynomial_cv_folds(
        x_train,
        y_train,
        config.polynomial_degree,
        config.cv_splits,
    )
    ridge_alpha, ridge_path = _search_regularization_alpha(
        "ridge",
        np.logspace(-3, 3, 9),
        polynomial_folds,
        config.random_state,
    )
    lasso_alpha, lasso_path = _search_regularization_alpha(
        "lasso",
        np.logspace(-4, 0, 9),
        polynomial_folds,
        config.random_state,
    )
    regularization_path = pd.concat(
        (ridge_path, lasso_path),
        ignore_index=True,
    )

    regime_features = (
        "wind_speed_100m_ms",
        "wind_direction_sin",
        "wind_direction_cos",
        "temperature_2m_c",
        "surface_pressure_hpa",
        "hour_sin",
        "hour_cos",
    )
    regime_indices = tuple(FEATURE_COLUMNS.index(name) for name in regime_features)
    best_cluster_count, cluster_selection = _select_cluster_count(
        x_train,
        y_train,
        regime_indices,
        config.random_state,
    )

    models: dict[str, Any] = {
        "linear_ols": ClosedFormLinearRegression(),
        "polynomial_ols": polynomial_ols_pipeline(config.polynomial_degree),
        "locally_weighted": LocallyWeightedLinearRegression(
            n_neighbors=config.local_neighbors,
            ridge=1e-5,
        ),
        "ridge_polynomial": polynomial_regularized_pipeline(
            "ridge",
            alpha=ridge_alpha,
            degree=config.polynomial_degree,
            random_state=config.random_state,
        ),
        "lasso_polynomial": polynomial_regularized_pipeline(
            "lasso",
            alpha=lasso_alpha,
            degree=config.polynomial_degree,
            random_state=config.random_state,
        ),
        "clustered_ridge": ClusteredRidgeRegressor(
            n_clusters=best_cluster_count,
            alpha=0.1,
            random_state=config.random_state,
            cluster_feature_indices=regime_indices,
        ),
    }
    validation_predictions: dict[str, np.ndarray] = {}
    test_predictions: dict[str, np.ndarray] = {}

    lag_mean = schema["scaling"]["training_feature_means"]["actual_power_lag_24h_mw"]
    lag_scale = schema["scaling"]["training_feature_scales"]["actual_power_lag_24h_mw"]
    lag_index = FEATURE_COLUMNS.index("actual_power_lag_24h_mw")
    validation_predictions["persistence_24h"] = _clip_power(
        x_validation[:, lag_index] * lag_scale + lag_mean,
        capacity_mw,
    )
    test_predictions["persistence_24h"] = _clip_power(
        x_test[:, lag_index] * lag_scale + lag_mean,
        capacity_mw,
    )

    for model_name, model in models.items():
        print(f"Fitting {MODEL_LABELS[model_name]}...")
        model.fit(x_train, y_train)
        validation_predictions[model_name] = _clip_power(
            model.predict(x_validation),
            capacity_mw,
        )
        test_predictions[model_name] = _clip_power(
            model.predict(x_test),
            capacity_mw,
        )

    tuning_summary = {
        "ridge_alpha": ridge_alpha,
        "lasso_alpha": lasso_alpha,
        "cluster_count": best_cluster_count,
        "cluster_regime_features": regime_features,
    }
    return (
        validation_predictions,
        test_predictions,
        models,
        regularization_path,
        cluster_selection,
        {"gradient_descent": gd_comparison, "tuning": tuning_summary},
    )


def _coefficient_analysis(
    models: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Extract regularized polynomial coefficients and summarize shrinkage."""
    rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    for model_name in ("ridge_polynomial", "lasso_polynomial"):
        pipeline = models[model_name]
        polynomial = pipeline.named_steps["polynomial"]
        regressor = pipeline.named_steps["regressor"]
        feature_names = polynomial.get_feature_names_out(FEATURE_COLUMNS)
        coefficients = np.asarray(regressor.coef_, dtype=float)
        zero_tolerance = 1e-10
        zero_mask = np.abs(coefficients) <= zero_tolerance
        for feature_name, coefficient, is_zero in zip(
            feature_names,
            coefficients,
            zero_mask,
            strict=True,
        ):
            rows.append(
                {
                    "model": model_name,
                    "feature": feature_name,
                    "coefficient": coefficient,
                    "absolute_coefficient": abs(coefficient),
                    "is_zero": bool(is_zero),
                }
            )
        order = np.argsort(np.abs(coefficients))[::-1][:10]
        summary[model_name] = {
            "coefficient_count": coefficients.size,
            "zero_coefficient_count": int(zero_mask.sum()),
            "zero_coefficient_share": float(zero_mask.mean()),
            "top_coefficients": [
                {
                    "feature": str(feature_names[index]),
                    "coefficient": float(coefficients[index]),
                }
                for index in order
            ],
        }
    return pd.DataFrame(rows), summary


def _evaluate_predictions_and_revenue(
    splits: dict[str, pd.DataFrame],
    validation_predictions: dict[str, np.ndarray],
    test_predictions: dict[str, np.ndarray],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Compute test forecast metrics and LP-based realized revenue for every model."""
    validation = splits["validation"]
    test = splits["test"]
    validation_actual = validation[TARGET_COLUMN].to_numpy(dtype=float)
    test_actual = test[TARGET_COLUMN].to_numpy(dtype=float)
    day_ahead = test[PRICE_COLUMNS[0]].to_numpy(dtype=float)
    up_regulation = test[PRICE_COLUMNS[1]].to_numpy(dtype=float)
    down_regulation = test[PRICE_COLUMNS[2]].to_numpy(dtype=float)
    capacity = test["capacity_mw"].to_numpy(dtype=float)
    prediction_output = test[
        [
            "timestamp_utc",
            "farm_id",
            TARGET_COLUMN,
            "capacity_mw",
            *PRICE_COLUMNS,
        ]
    ].copy()
    metric_rows: list[dict[str, Any]] = []
    revenue_rows: list[dict[str, Any]] = []

    for model_name in MODEL_LABELS:
        test_prediction = test_predictions[model_name]
        validation_residuals = validation_actual - validation_predictions[model_name]
        offers = optimize_offers_from_residuals(
            test_prediction,
            validation_residuals,
            day_ahead,
            up_regulation,
            down_regulation,
            capacity,
        )
        forecast_metrics = regression_metrics(test_actual, test_prediction)
        metric_rows.append(
            {
                "model": model_name,
                "label": MODEL_LABELS[model_name],
                **forecast_metrics,
            }
        )
        market_metrics = revenue_metrics(
            offers,
            test_actual,
            day_ahead,
            up_regulation,
            down_regulation,
        )
        interval_revenue = market_metrics.pop("interval_revenue_dkk")
        revenue_rows.append(
            {
                "model": model_name,
                "label": MODEL_LABELS[model_name],
                **market_metrics,
            }
        )
        prediction_output[f"{model_name}_prediction_mw"] = test_prediction
        prediction_output[f"{model_name}_offer_mw"] = offers
        prediction_output[f"{model_name}_revenue_dkk"] = interval_revenue

    prediction_metrics = pd.DataFrame(metric_rows)
    prediction_metrics["rmse_rank"] = (
        prediction_metrics["rmse_mw"].rank(method="min").astype(int)
    )
    prediction_metrics = prediction_metrics.sort_values("rmse_rank").reset_index(
        drop=True
    )
    revenue_table = pd.DataFrame(revenue_rows)
    revenue_table["revenue_rank"] = (
        revenue_table["total_revenue_dkk"]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    revenue_table = revenue_table.sort_values("revenue_rank").reset_index(drop=True)
    return prediction_metrics, revenue_table, prediction_output


def _plot_phase2_results(
    prediction_metrics: pd.DataFrame,
    revenue_table: pd.DataFrame,
    coefficient_table: pd.DataFrame,
    cluster_selection: pd.DataFrame,
    figure_dir: Path,
) -> dict[str, Path]:
    """Create publication-ready Phase 2 comparison figures."""
    figure_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")
    colors = "#2B7A78"
    paths = {
        "forecast_metrics": figure_dir / "phase2_forecast_rmse.png",
        "revenue_regret": figure_dir / "phase2_revenue_regret.png",
        "coefficients": figure_dir / "phase2_regularized_coefficients.png",
        "cluster_selection": figure_dir / "phase2_cluster_selection.png",
    }

    ordered = prediction_metrics.sort_values("rmse_mw", ascending=True)
    fig, axis = plt.subplots(figsize=(9.0, 5.0))
    axis.barh(ordered["label"], ordered["rmse_mw"], color=colors)
    axis.set_xlabel("Test RMSE (MW)")
    axis.set_title("Wind-power forecast error by model")
    fig.tight_layout()
    fig.savefig(paths["forecast_metrics"], dpi=180)
    plt.close(fig)

    ordered = revenue_table.sort_values("revenue_regret_dkk", ascending=False)
    fig, axis = plt.subplots(figsize=(9.0, 5.0))
    axis.barh(
        ordered["label"],
        ordered["revenue_regret_dkk"] / 1_000_000.0,
        color="#D97B29",
    )
    axis.set_xlabel("Revenue regret versus perfect foresight (million DKK)")
    axis.set_title("Economic loss by indirect trading model")
    fig.tight_layout()
    fig.savefig(paths["revenue_regret"], dpi=180)
    plt.close(fig)

    pivot = coefficient_table.pivot(
        index="feature",
        columns="model",
        values="absolute_coefficient",
    ).fillna(0.0)
    important = pivot.max(axis=1).nlargest(15).index
    comparison = pivot.loc[important].sort_values(
        "ridge_polynomial",
        ascending=True,
    )
    fig, axis = plt.subplots(figsize=(10.0, 6.5))
    y_positions = np.arange(len(comparison))
    axis.barh(
        y_positions - 0.18,
        comparison["ridge_polynomial"],
        height=0.35,
        label="Ridge",
        color="#2B7A78",
    )
    axis.barh(
        y_positions + 0.18,
        comparison["lasso_polynomial"],
        height=0.35,
        label="Lasso",
        color="#D97B29",
    )
    axis.set_yticks(y_positions, comparison.index)
    axis.set_xlabel("Absolute standardized coefficient")
    axis.set_title("Largest regularized polynomial coefficients")
    axis.legend()
    fig.tight_layout()
    fig.savefig(paths["coefficients"], dpi=180)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(7.5, 4.5))
    axis.plot(
        cluster_selection["n_clusters"],
        cluster_selection["inner_holdout_rmse_mw"],
        marker="o",
        color=colors,
    )
    axis.set_xlabel("Number of k-means clusters")
    axis.set_ylabel("Inner chronological holdout RMSE (MW)")
    axis.set_title("Cluster-count selection")
    axis.set_xticks(cluster_selection["n_clusters"])
    fig.tight_layout()
    fig.savefig(paths["cluster_selection"], dpi=180)
    plt.close(fig)
    return paths


def _json_ready(value: Any) -> Any:
    """Recursively convert NumPy and path values into JSON-compatible objects."""
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    return value


def run_phase2(config: Phase2Config) -> dict[str, Path]:
    """Execute Phase 2, persist all result tables, and generate report figures."""
    splits, schema = load_phase2_data(config.processed_data_dir)
    (
        validation_predictions,
        test_predictions,
        models,
        regularization_path,
        cluster_selection,
        experiment_details,
    ) = _fit_phase2_models(splits, schema, config)
    coefficient_table, coefficient_summary = _coefficient_analysis(models)
    prediction_metrics, revenue_table, prediction_output = (
        _evaluate_predictions_and_revenue(
            splits,
            validation_predictions,
            test_predictions,
        )
    )

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "prediction_metrics": output_dir / "prediction_metrics.csv",
        "revenue_metrics": output_dir / "revenue_metrics.csv",
        "regularization_path": output_dir / "regularization_path.csv",
        "coefficient_analysis": output_dir / "coefficient_analysis.csv",
        "cluster_selection": output_dir / "cluster_selection.csv",
        "test_predictions": output_dir / "test_predictions.csv.gz",
        "summary": output_dir / "summary.json",
    }
    prediction_metrics.to_csv(paths["prediction_metrics"], index=False)
    revenue_table.to_csv(paths["revenue_metrics"], index=False)
    regularization_path.to_csv(paths["regularization_path"], index=False)
    coefficient_table.to_csv(paths["coefficient_analysis"], index=False)
    cluster_selection.to_csv(paths["cluster_selection"], index=False)
    prediction_output.to_csv(
        paths["test_predictions"],
        index=False,
        compression="gzip",
        date_format="%Y-%m-%dT%H:%M:%SZ",
    )
    figure_paths = _plot_phase2_results(
        prediction_metrics,
        revenue_table,
        coefficient_table,
        cluster_selection,
        Path(config.figure_dir),
    )
    summary = {
        "phase": 2,
        "configuration": asdict(config),
        "input_rows": {name: len(frame) for name, frame in splits.items()},
        "gradient_descent_equivalence": experiment_details["gradient_descent"],
        "tuning": experiment_details["tuning"],
        "coefficient_summary": coefficient_summary,
        "prediction_metrics": prediction_metrics.to_dict(orient="records"),
        "revenue_metrics": revenue_table.to_dict(orient="records"),
        "figures": figure_paths,
        "evaluation_protocol": {
            "forecast_metrics": "chronological test split only",
            "regularization_selection": (
                "three expanding-window folds within the training split"
            ),
            "cluster_selection": (
                "last 20% of training as an inner chronological holdout"
            ),
            "offer_scenarios": (
                "equiprobable empirical residuals from the untouched validation split"
            ),
            "price_information": (
                "historical realized prices used as a controlled ex-post input to "
                "isolate production-model value"
            ),
        },
    }
    paths["summary"].write_text(
        json.dumps(_json_ready(summary), indent=2),
        encoding="utf-8",
    )
    print("Phase 2 complete.")
    print(prediction_metrics.to_string(index=False))
    print(revenue_table.to_string(index=False))
    return paths | {f"figure_{name}": path for name, path in figure_paths.items()}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the Phase 2 experiment."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--processed-data-dir",
        type=Path,
        default=Path("data/processed"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/phase2"),
    )
    parser.add_argument(
        "--figure-dir",
        type=Path,
        default=Path("docs/figures"),
    )
    parser.add_argument("--local-neighbors", type=int, default=192)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the complete indirect-model experiment from the command line."""
    args = _parse_args(argv)
    paths = run_phase2(
        Phase2Config(
            processed_data_dir=args.processed_data_dir,
            output_dir=args.output_dir,
            figure_dir=args.figure_dir,
            local_neighbors=args.local_neighbors,
        )
    )
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
