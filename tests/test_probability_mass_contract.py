"""Regression tests for accepted but slightly unnormalised scenario weights."""

from __future__ import annotations

import numpy as np
import pytest

from zephyrtrade.optimize import (
    expected_scenario_revenue,
    solve_single_period_offer_lp,
)


@pytest.mark.parametrize(
    ("scenarios", "weights"),
    [
        ([5.0], [1.000005]),
        ([2.0, 8.0], [0.5, 0.500005]),
        ([2.0, 8.0], [0.0, 1.000005]),
    ],
)
def test_tolerated_probability_mass_is_normalized_consistently(
    scenarios: list[float], weights: list[float]
) -> None:
    """LP and direct evaluation must represent the same probability measure."""
    production = np.asarray(scenarios, dtype=float)
    probabilities = np.asarray(weights, dtype=float)
    normalized = probabilities / probabilities.sum()
    params = (100.0, 200.0, 0.0)
    result = solve_single_period_offer_lp(
        production, probabilities, *params, capacity_mw=10.0
    )
    reference = solve_single_period_offer_lp(
        production, normalized, *params, capacity_mw=10.0
    )
    expected = expected_scenario_revenue(
        float(result["offer_mw"]), production, probabilities, *params
    )
    assert result["expected_revenue_dkk"] == pytest.approx(
        reference["expected_revenue_dkk"], abs=1e-8
    )
    assert expected == pytest.approx(result["expected_revenue_dkk"], abs=1e-8)


def test_scenario_weight_roundoff_does_not_change_deterministic_revenue() -> None:
    """A single known-production scenario retains its 500 DKK optimum."""
    result = solve_single_period_offer_lp(
        [5.0], [1.000005], 100.0, 200.0, 0.0, capacity_mw=10.0
    )
    assert result["offer_mw"] == pytest.approx(5.0)
    assert result["expected_revenue_dkk"] == pytest.approx(500.0)
    assert expected_scenario_revenue(
        5.0, [5.0], [1.000005], 100.0, 200.0, 0.0
    ) == pytest.approx(500.0)
