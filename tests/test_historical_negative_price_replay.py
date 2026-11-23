"""Reconcile the archived synthetic test mask with a fresh generator replay.

This is an ex-post reproducibility check for three fixed offers, not evidence
of an implementable day-ahead trading policy or fitted-model performance.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from zephyrtrade import data_loader
from zephyrtrade.evaluate import realized_market_revenue

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "artifacts/phase2/test_predictions.csv.gz"
ARCHIVE_SHA256 = "082476e06d676874f92332b1347393f5eb5f35bb64f19750362f506050a4ae72"
FARM = "bornholm_ronne_coastal"


def test_historical_mask_and_fixed_offers_on_the_same_generated_hours() -> None:
    """Explain excluded rows without inventing historical fitted-strategy offers."""
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == ARCHIVE_SHA256

    archived = pd.read_csv(ARCHIVE, parse_dates=["timestamp_utc"])
    observed = (
        archived.loc[archived["farm_id"] == FARM]
        .set_index("timestamp_utc")
        .sort_index()
    )
    assert observed.index.is_unique
    assert len(observed) == 3888

    captured: list[pd.DataFrame] = []
    original_filter = data_loader.filter_negative_price_intervals

    def capture_before_filter(
        market_prices: pd.DataFrame,
    ) -> tuple[pd.DataFrame, dict[str, float | int]]:
        captured.append(market_prices.copy())
        return original_filter(market_prices)

    with patch.object(
        data_loader, "filter_negative_price_intervals", capture_before_filter
    ):
        bundle = data_loader.generate_synthetic_data(data_loader.SyntheticDataConfig())

    assert len(captured) == 1
    prices = (
        captured[0]
        .set_index("timestamp_utc")
        .sort_index()
        .loc[observed.index.min() : observed.index.max()]
    )
    power = (
        bundle.wind_power.loc[bundle.wind_power["farm_id"] == FARM]
        .set_index("timestamp_utc")["actual_power_mw"]
        .loc[prices.index]
    )
    retained = prices.loc[:, list(data_loader.PRICE_COLUMNS)].ge(0.0).all(axis=1)
    assert len(prices) == 3941
    assert int(retained.sum()) == 3888
    assert int((~retained).sum()) == 53
    assert (
        prices.loc[~retained, list(data_loader.PRICE_COLUMNS)].lt(0.0).any(axis=1)
    ).all()
    pd.testing.assert_index_equal(prices.index[retained], observed.index)

    for column in (*data_loader.PRICE_COLUMNS, "actual_power_mw"):
        source = power if column == "actual_power_mw" else prices[column]
        np.testing.assert_allclose(
            source.loc[observed.index].to_numpy(),
            observed[column].to_numpy(),
            rtol=0.0,
            atol=1e-8,
        )

    # The same generated timestamps/power/prices are evaluated for each fixed
    # offer. The fitted historical strategies have no archived excluded-hour
    # offers, so this deliberately makes no claim about their full-mask ranking.
    for offer, expected_retained, expected_all, expected_excluded in (
        (0.0, 14651587.72, 14503605.49, -147982.23),
        (15.0, 16180038.18, 15933193.55, -246844.63),
        (30.0, 12603900.85, 12002850.81, -601050.04),
    ):
        settled = realized_market_revenue(
            np.full(len(prices), offer, dtype=float),
            power.to_numpy(dtype=float),
            *(
                prices[column].to_numpy(dtype=float)
                for column in data_loader.PRICE_COLUMNS
            ),
        )
        np.testing.assert_allclose(
            [
                float(settled[retained.to_numpy()].sum()),
                float(settled.sum()),
                float(settled[~retained.to_numpy()].sum()),
            ],
            [expected_retained, expected_all, expected_excluded],
            rtol=0.0,
            atol=0.02,
        )
