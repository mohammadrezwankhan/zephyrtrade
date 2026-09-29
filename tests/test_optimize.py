"""Tests for the stochastic trading linear program."""

from __future__ import annotations

import numpy as np
import pytest

from zephyrtrade.optimize import (
    critical_fractile,
    expected_scenario_revenue,
    optimize_offers_from_residuals,
    perfect_foresight_offers,
    solve_single_period_offer_lp,
)


def test_critical_fractile_and_explicit_lp_have_equal_value() -> None:
    """The empirical quantile rule should attain the explicit LP optimum."""
    scenarios = np.array([2.0, 5.0, 9.0, 13.0, 18.0])
    probabilities = np.full(scenarios.size, 1.0 / scenarios.size)
    day_ahead = 420.0
    up_regulation = 610.0
    down_regulation = 310.0
    lp_solution = solve_single_period_offer_lp(
        scenarios,
        probabilities,
        day_ahead,
        up_regulation,
        down_regulation,
        capacity_mw=20.0,
    )
    fractile = critical_fractile(
        np.array([day_ahead]),
        np.array([up_regulation]),
        np.array([down_regulation]),
    )[0]
    quantile_offer = float(np.quantile(scenarios, fractile, method="inverted_cdf"))
    quantile_revenue = expected_scenario_revenue(
        quantile_offer,
        scenarios,
        probabilities,
        day_ahead,
        up_regulation,
        down_regulation,
    )

    assert quantile_revenue == pytest.approx(
        lp_solution["expected_revenue_dkk"],
        abs=1e-8,
    )


def test_residual_optimizer_is_vectorized_and_capacity_bounded() -> None:
    """Residual scenarios should produce one feasible offer per forecast interval."""
    forecasts = np.array([3.0, 10.0, 19.0])
    residuals = np.array([-4.0, -1.0, 0.0, 2.0, 6.0])
    offers = optimize_offers_from_residuals(
        forecasts,
        residuals,
        day_ahead_price_dkk_mwh=np.array([400.0, 450.0, 500.0]),
        up_regulation_price_dkk_mwh=np.array([600.0, 650.0, 700.0]),
        down_regulation_price_dkk_mwh=np.array([300.0, 350.0, 400.0]),
        capacity_mw=20.0,
    )

    assert offers.shape == forecasts.shape
    assert np.all((offers >= 0.0) & (offers <= 20.0))


def test_lp_rejects_arbitrage_price_order() -> None:
    """A price order that makes simultaneous imbalances attractive must fail."""
    with pytest.raises(ValueError, match="down-regulation"):
        solve_single_period_offer_lp(
            np.array([5.0, 10.0]),
            np.array([0.5, 0.5]),
            day_ahead_price_dkk_mwh=400.0,
            up_regulation_price_dkk_mwh=450.0,
            down_regulation_price_dkk_mwh=500.0,
            capacity_mw=20.0,
        )


def test_perfect_foresight_targets_match_explicit_lps() -> None:
    """The vector label rule should match explicit single-scenario LP solves."""
    actual = np.array([3.0, 11.0, 24.0])
    day_ahead = np.array([350.0, 420.0, 510.0])
    up_regulation = day_ahead + np.array([120.0, 140.0, 180.0])
    down_regulation = day_ahead - np.array([60.0, 80.0, 90.0])
    vector_offers = perfect_foresight_offers(
        actual,
        day_ahead,
        up_regulation,
        down_regulation,
        capacity_mw=30.0,
    )
    lp_offers = np.array(
        [
            solve_single_period_offer_lp(
                np.array([power]),
                np.array([1.0]),
                day_ahead[index],
                up_regulation[index],
                down_regulation[index],
                capacity_mw=30.0,
            )["offer_mw"]
            for index, power in enumerate(actual)
        ]
    )

    np.testing.assert_allclose(vector_offers, lp_offers, atol=1e-10)
