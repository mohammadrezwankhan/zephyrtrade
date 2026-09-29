"""Regression checks for defects identified in the supplied source."""

import numpy as np
import pytest

from zephyrtrade.direct import CapacityBracketEncoder, probability_quantile_classes
from zephyrtrade.evaluate import (
    realized_market_revenue,
    regression_metrics,
    revenue_metrics,
)
from zephyrtrade.optimize import expected_scenario_revenue, solve_single_period_offer_lp


def market_args():
    return dict(
        offer_mw=np.array([0.0, 0.0]),
        actual_power_mw=np.array([0.0, 0.0]),
        day_ahead_price_dkk_mwh=np.array([400.0, 400.0]),
        up_regulation_price_dkk_mwh=np.array([600.0, 600.0]),
        down_regulation_price_dkk_mwh=np.array([300.0, 300.0]),
    )


def test_zero_generation_has_undefined_capture_not_crash():
    result = revenue_metrics(**market_args())
    assert result["total_revenue_dkk"] == 0
    assert result["revenue_capture_pct"] is None


@pytest.mark.parametrize("duration", [float("nan"), float("inf"), -1, 0])
def test_duration_must_be_finite_positive(duration):
    with pytest.raises(ValueError):
        realized_market_revenue(**market_args(), interval_hours=duration)


def test_single_interval_r2_is_explicitly_undefined():
    result = regression_metrics(np.array([3.0]), np.array([4.0]))
    assert result["rmse_mw"] == 1
    assert result["r2"] is None


@pytest.mark.parametrize(
    "probabilities", [np.array([1.2, -0.2]), np.array([-0.5, 1.5])]
)
def test_expected_revenue_rejects_negative_probability(probabilities):
    with pytest.raises(ValueError, match="nonnegative"):
        expected_scenario_revenue(
            5.0, np.array([2.0, 8.0]), probabilities, 400.0, 600.0, 300.0
        )


@pytest.mark.parametrize("offer", [float("nan"), float("inf"), -1])
def test_expected_revenue_rejects_invalid_offer(offer):
    with pytest.raises(ValueError, match="offer"):
        expected_scenario_revenue(
            offer, np.array([2.0, 8.0]), np.array([0.5, 0.5]), 400.0, 600.0, 300.0
        )


def test_expected_revenue_rejects_invalid_price_order():
    with pytest.raises(ValueError, match="down-regulation"):
        expected_scenario_revenue(
            5.0, np.array([2.0, 8.0]), np.array([0.5, 0.5]), 400.0, 300.0, 500.0
        )


@pytest.mark.parametrize("capacity", [float("nan"), float("inf")])
def test_lp_rejects_nonfinite_capacity_at_boundary(capacity):
    with pytest.raises(ValueError):
        solve_single_period_offer_lp(
            np.array([2.0, 8.0]), np.array([0.5, 0.5]), 400.0, 600.0, 300.0, capacity
        )


def test_quantile_one_cannot_wrap_to_lowest_class():
    result = probability_quantile_classes(
        np.array([[0.2, 0.3, 0.49999999]]), np.array([0, 1, 2]), 1.0
    )
    assert result.tolist() == [2]


@pytest.mark.parametrize("classes", [np.array([0, 0]), np.array([-1, 1])])
def test_probability_classes_are_unique_nonnegative(classes):
    with pytest.raises(ValueError, match="unique and nonnegative"):
        probability_quantile_classes(np.array([[0.5, 0.5]]), classes, 0.5)


@pytest.mark.parametrize("capacity", [float("nan"), 0, -1])
def test_encoder_transform_validates_capacity_before_fit(capacity):
    with pytest.raises(ValueError):
        CapacityBracketEncoder(3, capacity).transform(np.array([0.0]))
