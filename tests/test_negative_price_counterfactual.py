"""Separate retained-price backtests from synthetic all-price stress fixtures."""

from __future__ import annotations

import numpy as np
import pandas as pd

from zephyrtrade.data_loader import filter_negative_price_intervals
from zephyrtrade.evaluate import realized_market_revenue


def test_negative_price_exclusion_changes_the_evaluation_population() -> None:
    """A matched all-hours stress must not masquerade as the archived sample."""
    prices = pd.DataFrame(
        {
            "timestamp_utc": pd.date_range("2024-07-01", periods=4, freq="h", tz="UTC"),
            "day_ahead_price_dkk_mwh": [100.0, -100.0, 200.0, 0.0],
            "up_reg_price_dkk_mwh": [160.0, -40.0, 250.0, 100.0],
            "down_reg_price_dkk_mwh": [40.0, -160.0, 100.0, -30.0],
        }
    )
    kept, summary = filter_negative_price_intervals(prices)
    assert summary["rows_before_filter"] == 4
    assert summary["rows_after_filter"] == 2
    assert summary["negative_price_rows_removed"] == 2
    retained = prices["timestamp_utc"].isin(kept["timestamp_utc"]).to_numpy()
    np.testing.assert_array_equal(retained, [True, False, True, False])

    actual = np.array([2.0, 5.0, 8.0, 0.0])
    prices_da = prices["day_ahead_price_dkk_mwh"].to_numpy(dtype=float)
    prices_up = prices["up_reg_price_dkk_mwh"].to_numpy(dtype=float)
    prices_down = prices["down_reg_price_dkk_mwh"].to_numpy(dtype=float)

    # Both strategies use exactly the same timestamps, prices and settlement rules.
    for offers in (np.array([3.0, 4.0, 8.0, 0.0]), actual.copy()):
        all_hour_revenue = realized_market_revenue(
            offers, actual, prices_da, prices_up, prices_down
        )
        retained_hour_revenue = realized_market_revenue(
            offers[retained],
            actual[retained],
            prices_da[retained],
            prices_up[retained],
            prices_down[retained],
        )
        np.testing.assert_allclose(retained_hour_revenue, all_hour_revenue[retained])
        assert float(retained_hour_revenue.sum()) != float(all_hour_revenue.sum())

    # The single non-oracle synthetic case demonstrates positive-only selection bias.
    offers = np.array([3.0, 4.0, 8.0, 0.0])
    revenue = realized_market_revenue(
        offers, actual, prices_da, prices_up, prices_down
    )
    np.testing.assert_array_equal(revenue, [140.0, -560.0, 1600.0, 0.0])
    assert float(revenue.sum()) == 1180.0
    assert float(revenue[retained].sum()) == 1740.0
