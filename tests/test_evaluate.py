"""Tests for forecast and market-revenue evaluation."""

from __future__ import annotations

import numpy as np
import pytest

from zephyrtrade.evaluate import (
    realized_market_revenue,
    regression_metrics,
    revenue_metrics,
)


def test_realized_revenue_uses_surplus_and_shortfall_prices() -> None:
    """Surplus should earn down price and shortfall should pay up price."""
    offers = np.array([8.0, 12.0, 10.0])
    actual = np.array([10.0, 9.0, 10.0])
    day_ahead = np.array([400.0, 400.0, 400.0])
    up_regulation = np.array([600.0, 600.0, 600.0])
    down_regulation = np.array([300.0, 300.0, 300.0])
    revenue = realized_market_revenue(
        offers,
        actual,
        day_ahead,
        up_regulation,
        down_regulation,
    )

    assert revenue[0] == pytest.approx(8.0 * 400.0 + 2.0 * 300.0)
    assert revenue[1] == pytest.approx(12.0 * 400.0 - 3.0 * 600.0)
    assert revenue[2] == pytest.approx(10.0 * 400.0)


def test_metrics_identify_perfect_forecast_and_offer() -> None:
    """Perfect production and offer predictions should have no error or regret."""
    actual = np.array([5.0, 10.0, 15.0])
    forecast_metrics = regression_metrics(actual, actual)
    market_metrics = revenue_metrics(
        actual,
        actual,
        day_ahead_price_dkk_mwh=np.array([400.0, 450.0, 500.0]),
        up_regulation_price_dkk_mwh=np.array([550.0, 600.0, 650.0]),
        down_regulation_price_dkk_mwh=np.array([300.0, 350.0, 400.0]),
    )

    assert forecast_metrics["rmse_mw"] == pytest.approx(0.0)
    assert forecast_metrics["mae_mw"] == pytest.approx(0.0)
    assert forecast_metrics["r2"] == pytest.approx(1.0)
    assert market_metrics["revenue_regret_dkk"] == pytest.approx(0.0)
    assert market_metrics["revenue_capture_pct"] == pytest.approx(100.0)
