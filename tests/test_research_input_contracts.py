"""Reject stale, misaligned, or economically invalid research-stage inputs."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from zephyrtrade import phase2, phase3, preprocessing


def test_phase2_rejects_missing_or_changed_feature_schema(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Feature schema"):
        phase2.load_phase2_data(tmp_path)
    schema = tmp_path / "feature_schema.json"
    schema.write_text(json.dumps({"feature_columns": ["future-target"]}))
    with pytest.raises(ValueError, match="feature order"):
        phase2.load_phase2_data(tmp_path)
    schema.write_text(json.dumps({"feature_columns": preprocessing.FEATURE_COLUMNS}))
    with pytest.raises(FileNotFoundError, match="Processed split"):
        phase2.load_phase2_data(tmp_path)
    for split in ("train", "validation", "test"):
        pd.DataFrame({"timestamp_utc": ["2024-01-01", "2024-01-02"]}).to_csv(
            tmp_path / f"{split}_scaled.csv.gz",
            index=False,
        )
    with pytest.raises(ValueError, match="strictly chronological"):
        phase2.load_phase2_data(tmp_path)


def market_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp_utc": pd.date_range("2024-01-01", periods=3, freq="h", tz="UTC"),
            "farm_id": ["synthetic"] * 3,
            preprocessing.TARGET_COLUMN: [3.0, 4.0, 5.0],
            "capacity_mw": [30.0] * 3,
            preprocessing.PRICE_COLUMNS[0]: [400.0] * 3,
            preprocessing.PRICE_COLUMNS[1]: [600.0] * 3,
            preprocessing.PRICE_COLUMNS[2]: [200.0] * 3,
        }
    )


def test_indirect_benchmark_requires_exact_rows_and_market_observations(
    tmp_path: Path,
) -> None:
    frame = market_frame()
    path = tmp_path / "indirect.csv"
    with pytest.raises(FileNotFoundError, match="Phase 2"):
        phase3._load_indirect_offer(frame, path)
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError, match="missing columns"):
        phase3._load_indirect_offer(frame, path)
    benchmark = frame.assign(locally_weighted_offer_mw=[2.0, 3.0, 4.0])
    benchmark.to_csv(path, index=False)
    np.testing.assert_array_equal(
        phase3._load_indirect_offer(frame, path), [2.0, 3.0, 4.0]
    )
    benchmark.iloc[1:].to_csv(path, index=False)
    with pytest.raises(ValueError, match="align"):
        phase3._load_indirect_offer(frame, path)
    benchmark.loc[0, preprocessing.PRICE_COLUMNS[0]] = 401.0
    benchmark.to_csv(path, index=False)
    with pytest.raises(ValueError, match="disagree"):
        phase3._load_indirect_offer(frame, path)


def test_economic_weights_and_explicit_target_audit_require_their_stated_prices() -> (
    None
):
    frame = market_frame()
    np.testing.assert_array_equal(phase3._economic_sample_weights(frame), np.ones(3))
    frame[preprocessing.PRICE_COLUMNS[1]] = frame[preprocessing.PRICE_COLUMNS[2]]
    with pytest.raises(ValueError, match="positive finite spreads"):
        phase3._economic_sample_weights(frame)
    frame = market_frame()
    frame[preprocessing.PRICE_COLUMNS[0]] = frame[preprocessing.PRICE_COLUMNS[1]]
    with pytest.raises(ValueError, match="No strict-price rows"):
        phase3._explicit_lp_audit(
            frame, frame[preprocessing.TARGET_COLUMN].to_numpy(dtype=float)
        )
