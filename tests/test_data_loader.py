"""Tests for the Phase 1 synthetic source-data pipeline."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from zephyrtrade.data_loader import (
    FARM_SPECS,
    PRICE_COLUMNS,
    SyntheticDataConfig,
    filter_negative_price_intervals,
    generate_synthetic_data,
    validate_data_bundle,
    write_data_bundle,
)


def test_generator_is_deterministic_and_respects_physical_bounds() -> None:
    """The same seed should reproduce valid four-farm numeric tables."""
    config = SyntheticDataConfig(
        start="2024-01-01",
        end="2024-02-15",
        seed=17,
        negative_price_probability=0.05,
    )
    first = generate_synthetic_data(config)
    second = generate_synthetic_data(config)

    assert set(first.wind_power["farm_id"].unique()) == {
        farm.farm_id for farm in FARM_SPECS
    }
    pd.testing.assert_frame_equal(first.wind_power, second.wind_power)
    pd.testing.assert_frame_equal(first.market_prices, second.market_prices)
    assert first.wind_power["actual_power_mw"].ge(0.0).all()
    assert (
        first.wind_power["actual_power_mw"] <= first.wind_power["capacity_mw"]
    ).all()
    assert first.market_prices.loc[:, PRICE_COLUMNS].ge(0.0).all().all()
    assert first.price_filter_summary["negative_price_rows_removed"] > 0


def test_writer_emits_complete_source_contract(tmp_path: Path) -> None:
    """Writing a bundle should create every documented Phase 1 source artifact."""
    config = SyntheticDataConfig(
        start="2024-01-01",
        end="2024-01-20",
        seed=5,
        negative_price_probability=0.03,
        output_dir=tmp_path,
    )
    bundle = generate_synthetic_data(config)
    paths = write_data_bundle(bundle, config)

    assert set(paths) == {
        "farm_metadata",
        "wind_power",
        "climate",
        "market_prices",
        "provenance",
    }
    assert all(path.exists() and path.stat().st_size > 0 for path in paths.values())


def test_negative_price_filter_rejects_fully_excluded_population() -> None:
    """Reject a zero-row evaluation population after valid negative-price filtering."""
    prices = pd.DataFrame(
        {
            "day_ahead_price_dkk_mwh": [-1.0, -2.0],
            "up_reg_price_dkk_mwh": [5.0, 6.0],
            "down_reg_price_dkk_mwh": [3.0, 4.0],
        }
    )
    with pytest.raises(ValueError, match="No nonnegative price intervals remain"):
        filter_negative_price_intervals(prices)


def test_negative_price_filter_rejects_empty_table() -> None:
    """Empty source rows must not cause an uninformative zero-division error."""
    prices = pd.DataFrame(columns=PRICE_COLUMNS)
    with pytest.raises(ValueError, match="at least one interval"):
        filter_negative_price_intervals(prices)


@pytest.mark.parametrize(
    ("second_timestamp", "message"),
    [
        (pd.Timestamp("2024-07-01T00:00:00Z"), "must be unique"),
        (pd.NaT, "must not be missing"),
    ],
)
def test_price_filter_rejects_invalid_delivery_keys_before_exclusions(
    second_timestamp: pd.Timestamp, message: str
) -> None:
    """Duplicate/missing timestamps must not vanish behind a negative-price mask."""
    prices = pd.DataFrame(
        {
            "timestamp_utc": [
                pd.Timestamp("2024-07-01T00:00:00Z"),
                second_timestamp,
            ],
            "day_ahead_price_dkk_mwh": [100.0, -50.0],
            "up_reg_price_dkk_mwh": [110.0, 40.0],
            "down_reg_price_dkk_mwh": [90.0, 20.0],
        }
    )
    with pytest.raises(ValueError, match=message):
        filter_negative_price_intervals(prices)


@pytest.mark.parametrize(
    "probability", [-0.01, 1.0, float("nan"), float("inf"), float("-inf")]
)
def test_generator_rejects_invalid_programmatic_probability(
    probability: float,
) -> None:
    """Library callers must meet the same parameter bounds as the CLI."""
    config = SyntheticDataConfig(negative_price_probability=probability)
    with pytest.raises(ValueError, match="Negative-price probability"):
        generate_synthetic_data(config)


@pytest.mark.parametrize("bad_price", [float("nan"), float("inf"), float("-inf")])
def test_negative_price_filter_rejects_nonfinite_source_prices(
    bad_price: float,
) -> None:
    """Missing/infinite prices must not be counted as negative or retained."""
    prices = pd.DataFrame(
        {
            "timestamp_utc": pd.date_range("2024-07-01", periods=3, freq="h", tz="UTC"),
            "day_ahead_price_dkk_mwh": [100.0, bad_price, -50.0],
            "up_reg_price_dkk_mwh": [110.0, 120.0, 60.0],
            "down_reg_price_dkk_mwh": [90.0, 100.0, 40.0],
        }
    )
    with pytest.raises(ValueError, match="finite"):
        filter_negative_price_intervals(prices)


def test_negative_price_filter_keeps_finite_zero_and_drops_negative() -> None:
    """Preserve historical finite-value selection semantics exactly."""
    prices = pd.DataFrame(
        {
            "day_ahead_price_dkk_mwh": [0.0, -1.0],
            "up_reg_price_dkk_mwh": [0.0, 1.0],
            "down_reg_price_dkk_mwh": [0.0, 1.0],
        }
    )
    retained, summary = filter_negative_price_intervals(prices)
    assert retained["day_ahead_price_dkk_mwh"].tolist() == [0.0]
    assert summary["negative_price_rows_removed"] == 1


@pytest.mark.parametrize(
    ("frame_name", "column"),
    [
        ("farm_metadata", "capacity_mw"),
        ("wind_power", "availability_fraction"),
        ("climate", "temperature_2m_c"),
        ("market_prices", "day_ahead_price_dkk_mwh"),
    ],
)
def test_bundle_validator_rejects_infinite_numeric_values(
    frame_name: str, column: str
) -> None:
    """An infinity must not pass as a valid observation or market price."""
    bundle = generate_synthetic_data(
        SyntheticDataConfig(
            start="2024-01-01",
            end="2024-01-10",
            seed=5,
            negative_price_probability=0.0,
        )
    )
    altered = getattr(bundle, frame_name).copy()
    altered.loc[altered.index[0], column] = float("inf")
    invalid = replace(bundle, **{frame_name: altered})
    with pytest.raises(
        ValueError, match=f"Nonfinite numeric values found in {frame_name}"
    ):
        validate_data_bundle(invalid)
