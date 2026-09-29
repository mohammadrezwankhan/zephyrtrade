"""Regression checks for defects identified in the supplied source."""
import numpy as np
import pytest
from zephyrtrade.evaluate import realized_market_revenue, revenue_metrics, regression_metrics
from zephyrtrade.optimize import expected_scenario_revenue, solve_single_period_offer_lp
from zephyrtrade.direct import probability_quantile_classes, CapacityBracketEncoder


def market_args():
    return dict(offer_mw=np.array([0., 0.]), actual_power_mw=np.array([0., 0.]),
                day_ahead_price_dkk_mwh=np.array([400., 400.]),
                up_regulation_price_dkk_mwh=np.array([600., 600.]),
                down_regulation_price_dkk_mwh=np.array([300., 300.]))


def test_zero_generation_has_undefined_capture_not_crash():
    result = revenue_metrics(**market_args())
    assert result['total_revenue_dkk'] == 0
    assert result['revenue_capture_pct'] is None


@pytest.mark.parametrize('duration', [float('nan'), float('inf'), -1, 0])
def test_duration_must_be_finite_positive(duration):
    with pytest.raises(ValueError):
        realized_market_revenue(**market_args(), interval_hours=duration)


def test_single_interval_r2_is_explicitly_undefined():
    result = regression_metrics(np.array([3.]), np.array([4.]))
    assert result['rmse_mw'] == 1
    assert result['r2'] is None


@pytest.mark.parametrize('probabilities', [np.array([1.2, -.2]), np.array([-.5, 1.5])])
def test_expected_revenue_rejects_negative_probability(probabilities):
    with pytest.raises(ValueError, match='nonnegative'):
        expected_scenario_revenue(5., np.array([2., 8.]), probabilities, 400., 600., 300.)


@pytest.mark.parametrize('offer', [float('nan'), float('inf'), -1])
def test_expected_revenue_rejects_invalid_offer(offer):
    with pytest.raises(ValueError, match='offer'):
        expected_scenario_revenue(offer, np.array([2., 8.]), np.array([.5, .5]), 400., 600., 300.)


def test_expected_revenue_rejects_invalid_price_order():
    with pytest.raises(ValueError, match='down-regulation'):
        expected_scenario_revenue(5., np.array([2., 8.]), np.array([.5, .5]), 400., 300., 500.)


@pytest.mark.parametrize('capacity', [float('nan'), float('inf')])
def test_lp_rejects_nonfinite_capacity_at_boundary(capacity):
    with pytest.raises(ValueError):
        solve_single_period_offer_lp(np.array([2., 8.]), np.array([.5, .5]), 400., 600., 300., capacity)


def test_quantile_one_cannot_wrap_to_lowest_class():
    result = probability_quantile_classes(np.array([[.2, .3, .49999999]]), np.array([0, 1, 2]), 1.)
    assert result.tolist() == [2]


@pytest.mark.parametrize('classes', [np.array([0, 0]), np.array([-1, 1])])
def test_probability_classes_are_unique_nonnegative(classes):
    with pytest.raises(ValueError, match='unique and nonnegative'):
        probability_quantile_classes(np.array([[.5, .5]]), classes, .5)


@pytest.mark.parametrize('capacity', [float('nan'), 0, -1])
def test_encoder_transform_validates_capacity_before_fit(capacity):
    with pytest.raises(ValueError):
        CapacityBracketEncoder(3, capacity).transform(np.array([0.]))
