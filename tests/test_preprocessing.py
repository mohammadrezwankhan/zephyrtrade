"""Tests for leakage-safe feature engineering and chronological preprocessing."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from zephyrtrade.data_loader import (
    SyntheticDataConfig,
    generate_synthetic_data,
    write_data_bundle,
)
from zephyrtrade.preprocessing import (
    FEATURE_COLUMNS,
    PreprocessingConfig,
    chronological_split,
    engineer_features,
    prepare_dataset,
    scale_feature_splits,
)


def _quarter_year_bundle():
    """Return a stable fixture with enough history for weekly features."""
    config = SyntheticDataConfig(
        start="2024-01-01",
        end="2024-04-01",
        seed=23,
        negative_price_probability=0.02,
    )
    return generate_synthetic_data(config)


def test_history_features_exclude_the_current_target() -> None:
    """The 24-hour lag and weekly median should use only prior observations."""
    bundle = _quarter_year_bundle()
    config = PreprocessingConfig()
    features = engineer_features(
        bundle.wind_power,
        bundle.climate,
        bundle.market_prices,
        config,
    )
    row = features.iloc[len(features) // 2]
    farm_power = (
        bundle.wind_power.loc[bundle.wind_power["farm_id"] == config.farm_id]
        .set_index("timestamp_utc")["actual_power_mw"]
        .sort_index()
    )
    timestamp = pd.Timestamp(row["timestamp_utc"])
    expected_lag = farm_power.loc[timestamp - pd.Timedelta(24, unit="h")]
    expected_median = farm_power.loc[
        timestamp - pd.Timedelta(168, unit="h") : timestamp - pd.Timedelta(1, unit="h")
    ].quantile(0.50)

    assert np.isclose(row["actual_power_lag_24h_mw"], expected_lag)
    assert np.isclose(row["weekly_power_q50_mw"], expected_median)


def test_splits_are_ordered_and_scaler_is_fit_on_training_only() -> None:
    """Chronological partitions must not overlap and training means scale to zero."""
    bundle = _quarter_year_bundle()
    features = engineer_features(
        bundle.wind_power,
        bundle.climate,
        bundle.market_prices,
        PreprocessingConfig(),
    )
    splits = chronological_split(features, 0.70, 0.15)
    scaled, scaler = scale_feature_splits(splits)

    assert (
        splits["train"]["timestamp_utc"].max()
        < splits["validation"]["timestamp_utc"].min()
    )
    assert (
        splits["validation"]["timestamp_utc"].max()
        < splits["test"]["timestamp_utc"].min()
    )
    assert np.allclose(
        scaled["train"].loc[:, FEATURE_COLUMNS].mean().to_numpy(),
        0.0,
        atol=1e-10,
    )
    assert scaler.n_features_in_ == len(FEATURE_COLUMNS)


def test_end_to_end_preprocessing_writes_schema_and_splits(tmp_path) -> None:
    """The persisted pipeline should expose auditable schema and split artifacts."""
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    source_config = SyntheticDataConfig(
        start="2024-01-01",
        end="2024-04-01",
        seed=31,
        output_dir=raw_dir,
    )
    write_data_bundle(generate_synthetic_data(source_config), source_config)
    paths = prepare_dataset(
        PreprocessingConfig(raw_data_dir=raw_dir, output_dir=processed_dir)
    )

    assert all(path.exists() and path.stat().st_size > 0 for path in paths.values())
    schema = json.loads(paths["schema"].read_text(encoding="utf-8"))
    assert schema["feature_columns"] == FEATURE_COLUMNS
    assert schema["history_policy"]["current_target_excluded_from_rolling_statistics"]
    assert schema["split_policy"]["splits"]["test"]["rows"] > 0
