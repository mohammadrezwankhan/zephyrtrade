"""Exercise the public research workflow and reconcile its physical outputs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from zephyrtrade import pipeline
from zephyrtrade.preprocessing import FEATURE_COLUMNS, PRICE_COLUMNS, TARGET_COLUMN


def _record(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    result: dict[str, object] = {}
    for key, item in value.items():
        assert isinstance(key, str)
        result[key] = item
    return result


def _read_record(path: Path) -> dict[str, object]:
    return _record(json.loads(path.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def research_run(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Run every default research model on a fresh bounded synthetic period."""
    root = tmp_path_factory.mktemp("zephyr-research")
    assert (
        pipeline.main(
            [
                "--start",
                "2024-01-01",
                "--end",
                "2024-03-01",
                "--seed",
                "42",
                "--raw-data-dir",
                str(root / "raw"),
                "--processed-data-dir",
                str(root / "processed"),
                "--artifact-dir",
                str(root / "artifacts"),
                "--figure-dir",
                str(root / "figures"),
            ]
        )
        == 0
    )
    return root


def test_pipeline_manifest_binds_real_inputs_and_stage_receipts(
    research_run: Path,
) -> None:
    manifest = _read_record(research_run / "artifacts/run_manifest.json")
    assert manifest["project"] == "ZephyrTrade"
    assert _record(manifest["configuration"])["seed"] == 42
    versions = _record(_record(manifest["runtime"])["dependencies"])
    assert all(
        isinstance(value, str) and value != "not-installed"
        for value in versions.values()
    )
    hashes = _record(manifest["sha256"])
    paths = {
        "raw_provenance": research_run / "raw/provenance.json",
        "feature_schema": research_run / "processed/feature_schema.json",
        "phase2_summary": research_run / "artifacts/phase2/summary.json",
        "phase3_summary": research_run / "artifacts/phase3/summary.json",
    }
    for name, path in paths.items():
        assert hashes[name] == hashlib.sha256(path.read_bytes()).hexdigest()
    retained = _record(manifest["row_counts"])["retained_market_prices"]
    assert isinstance(retained, int) and retained > 0


def test_training_tuning_and_test_periods_keep_chronological_contracts(
    research_run: Path,
) -> None:
    frames = {
        split: pd.read_csv(research_run / "processed" / f"{split}_scaled.csv.gz")
        for split in ("train", "validation", "test")
    }
    assert (
        frames["train"]["timestamp_utc"].max()
        < frames["validation"]["timestamp_utc"].min()
    )
    assert (
        frames["validation"]["timestamp_utc"].max()
        < frames["test"]["timestamp_utc"].min()
    )
    np.testing.assert_allclose(
        frames["train"][FEATURE_COLUMNS].mean().to_numpy(),
        0.0,
        atol=1e-10,
    )
    summary = _read_record(research_run / "artifacts/phase3/summary.json")
    protocol = _record(summary["evaluation_protocol"])
    assert protocol["inference_features"] == FEATURE_COLUMNS
    assert not set(PRICE_COLUMNS) & set(FEATURE_COLUMNS)
    assert TARGET_COLUMN not in FEATURE_COLUMNS
    target_audit = _record(summary["target_engineering"])
    assert target_audit["explicit_lp_rows"] == 25
    assert target_audit["vector_target_equals_actual_share"] == 1.0
    assert target_audit["maximum_explicit_lp_difference_mw"] == 0.0


@pytest.mark.parametrize(
    ("phase", "filename", "expected_strategies"),
    [
        ("phase2", "test_predictions.csv.gz", 7),
        ("phase3", "test_direct_predictions.csv.gz", 4),
    ],
)
def test_saved_offers_and_settlement_reconcile_with_physical_observations(
    research_run: Path,
    phase: str,
    filename: str,
    expected_strategies: int,
) -> None:
    frame = pd.read_csv(research_run / "artifacts" / phase / filename)
    offer_columns = [name for name in frame.columns if name.endswith("_offer_mw")]
    assert len(offer_columns) == expected_strategies
    assert frame["timestamp_utc"].is_unique
    assert frame["timestamp_utc"].is_monotonic_increasing
    actual = frame[TARGET_COLUMN].to_numpy(dtype=float)
    capacity = frame["capacity_mw"].to_numpy(dtype=float)
    da, up, down = [frame[name].to_numpy(dtype=float) for name in PRICE_COLUMNS]
    assert np.all((actual >= 0) & (actual <= capacity))
    assert np.all((down <= da) & (da <= up))
    for name in offer_columns:
        offer = frame[name].to_numpy(dtype=float)
        assert np.isfinite(offer).all()
        assert np.all((offer >= 0) & (offer <= capacity))
        imbalance = actual - offer
        settlement = da * offer + np.where(imbalance >= 0, down, up) * imbalance
        saved = frame[name.removesuffix("_offer_mw") + "_revenue_dkk"]
        np.testing.assert_allclose(saved, settlement, rtol=1e-12, atol=1e-8)


def test_research_figures_and_all_declared_outputs_are_materialized(
    research_run: Path,
) -> None:
    manifest = _read_record(research_run / "artifacts/run_manifest.json")
    for section in _record(manifest["outputs"]).values():
        for path_value in _record(section).values():
            assert isinstance(path_value, str)
            path = Path(path_value)
            assert path.is_file() and path.stat().st_size > 0
            if path.suffix == ".png":
                assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    phase2 = pd.read_csv(research_run / "artifacts/phase2/prediction_metrics.csv")
    phase3 = pd.read_csv(research_run / "artifacts/phase3/strategy_comparison.csv")
    assert len(phase2) == 7
    assert len(phase3) == 4
    assert set(phase2["model"]) >= {"linear_ols", "locally_weighted", "clustered_ridge"}
