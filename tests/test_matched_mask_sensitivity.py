"""Illustrate ranking reversal under selection using the same settlement rows."""

from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from zephyrtrade.data_loader import filter_negative_price_intervals
from zephyrtrade.evaluate import realized_market_revenue


def test_price_filter_can_reverse_a_paired_synthetic_strategy_ranking() -> None:
    prices = pd.DataFrame(
        {
            "timestamp_utc": pd.date_range("2024-07-01", periods=4, freq="h", tz="UTC"),
            "day_ahead_price_dkk_mwh": [100.0, -100.0, 200.0, 0.0],
            "up_reg_price_dkk_mwh": [160.0, -40.0, 250.0, 100.0],
            "down_reg_price_dkk_mwh": [40.0, -160.0, 100.0, -30.0],
        }
    )
    actual = np.array([2.0, 5.0, 8.0, 0.0])
    first_offers = np.array([3.0, 4.0, 8.0, 0.0])
    second_offers = np.array([2.0, 0.0, 8.0, 0.0])
    retained_prices, _summary = filter_negative_price_intervals(prices)
    mask = prices["timestamp_utc"].isin(retained_prices["timestamp_utc"]).to_numpy()
    np.testing.assert_array_equal(mask, [True, False, True, False])

    def settled(offers: NDArray[np.float64]) -> NDArray[np.float64]:
        return realized_market_revenue(
            offers,
            actual,
            prices["day_ahead_price_dkk_mwh"].to_numpy(dtype=float),
            prices["up_reg_price_dkk_mwh"].to_numpy(dtype=float),
            prices["down_reg_price_dkk_mwh"].to_numpy(dtype=float),
        )

    first_revenue = settled(first_offers)
    second_revenue = settled(second_offers)
    assert float(first_revenue[mask].sum()) == 1740.0
    assert float(second_revenue[mask].sum()) == 1800.0
    assert float(first_revenue.sum()) == 1180.0
    assert float(second_revenue.sum()) == 1000.0
    assert second_revenue[mask].sum() > first_revenue[mask].sum()
    assert first_revenue.sum() > second_revenue.sum()
