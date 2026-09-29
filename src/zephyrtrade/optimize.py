"""Linear-program trading optimizer for day-ahead and balancing markets."""

from __future__ import annotations

import numpy as np
from scipy.optimize import linprog


def _as_finite_vector(values: np.ndarray, name: str) -> np.ndarray:
    """Convert values to a finite one-dimensional float array."""
    vector = np.asarray(values, dtype=float)
    if vector.ndim != 1 or vector.size == 0:
        raise ValueError(f"{name} must be a nonempty one-dimensional array.")
    if not np.isfinite(vector).all():
        raise ValueError(f"{name} must contain only finite values.")
    return vector


def validate_price_order(
    day_ahead_price: np.ndarray,
    up_regulation_price: np.ndarray,
    down_regulation_price: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Validate the no-arbitrage ordering used by the trading formulation."""
    day_ahead = np.asarray(day_ahead_price, dtype=float)
    up_regulation = np.asarray(up_regulation_price, dtype=float)
    down_regulation = np.asarray(down_regulation_price, dtype=float)
    day_ahead, up_regulation, down_regulation = np.broadcast_arrays(
        day_ahead,
        up_regulation,
        down_regulation,
    )
    if not (
        np.isfinite(day_ahead).all()
        and np.isfinite(up_regulation).all()
        and np.isfinite(down_regulation).all()
    ):
        raise ValueError("Market prices must be finite.")
    if (down_regulation > day_ahead).any() or (day_ahead > up_regulation).any():
        raise ValueError(
            "Expected down-regulation <= day-ahead <= up-regulation prices."
        )
    if (up_regulation <= down_regulation).any():
        raise ValueError("Up-regulation prices must exceed down-regulation prices.")
    return day_ahead, up_regulation, down_regulation


def critical_fractile(
    day_ahead_price: np.ndarray,
    up_regulation_price: np.ndarray,
    down_regulation_price: np.ndarray,
) -> np.ndarray:
    """Return the LP's optimal production-distribution quantile at each interval."""
    day_ahead, up_regulation, down_regulation = validate_price_order(
        day_ahead_price,
        up_regulation_price,
        down_regulation_price,
    )
    fractile = (day_ahead - down_regulation) / (up_regulation - down_regulation)
    return np.clip(fractile, 0.0, 1.0)


def perfect_foresight_offers(
    actual_power_mw: np.ndarray,
    day_ahead_price_dkk_mwh: np.ndarray,
    up_regulation_price_dkk_mwh: np.ndarray,
    down_regulation_price_dkk_mwh: np.ndarray,
    capacity_mw: float | np.ndarray,
) -> np.ndarray:
    """Return exact deterministic-LP offers for known production.

    With one production scenario and the no-arbitrage ordering
    ``down <= day-ahead <= up``, increasing an offer up to realized production
    earns the day-ahead price instead of the down-regulation price, while an
    offer above production incurs the up-regulation price. The optimum is
    therefore realized production itself (up to harmless ties at equal prices).
    """
    actual = _as_finite_vector(actual_power_mw, "actual_power_mw")
    capacities = np.broadcast_to(np.asarray(capacity_mw, dtype=float), actual.shape)
    if not np.isfinite(capacities).all() or (capacities <= 0.0).any():
        raise ValueError("Capacity values must be finite and positive.")
    if (actual < 0.0).any() or (actual > capacities).any():
        raise ValueError("Actual production must lie within physical capacity.")

    day_ahead = np.asarray(day_ahead_price_dkk_mwh, dtype=float)
    up_regulation = np.asarray(up_regulation_price_dkk_mwh, dtype=float)
    down_regulation = np.asarray(down_regulation_price_dkk_mwh, dtype=float)
    if not (
        day_ahead.shape == up_regulation.shape == down_regulation.shape == actual.shape
    ):
        raise ValueError("Every price vector must match the production shape.")
    validate_price_order(day_ahead, up_regulation, down_regulation)
    return actual.copy()


def solve_single_period_offer_lp(
    production_scenarios_mw: np.ndarray,
    scenario_probabilities: np.ndarray,
    day_ahead_price_dkk_mwh: float,
    up_regulation_price_dkk_mwh: float,
    down_regulation_price_dkk_mwh: float,
    capacity_mw: float,
) -> dict[str, float | np.ndarray]:
    """Solve one stochastic day-ahead offering problem as an explicit LP.

    Variables are the day-ahead offer and nonnegative surplus and shortfall
    quantities for each production scenario. The balancing identity is
    ``offer + surplus - shortfall = production``.
    """
    scenarios = _as_finite_vector(
        production_scenarios_mw,
        "production_scenarios_mw",
    )
    probabilities = _as_finite_vector(
        scenario_probabilities,
        "scenario_probabilities",
    )
    if scenarios.size != probabilities.size:
        raise ValueError("Scenarios and probabilities must have the same length.")
    if (probabilities < 0.0).any() or not np.isclose(probabilities.sum(), 1.0):
        raise ValueError("Scenario probabilities must be nonnegative and sum to one.")
    if not np.isfinite(capacity_mw) or capacity_mw <= 0.0:
        raise ValueError("capacity_mw must be finite and positive.")
    if (scenarios < 0.0).any() or (scenarios > capacity_mw).any():
        raise ValueError("Production scenarios must lie within physical capacity.")

    day_ahead, up_regulation, down_regulation = validate_price_order(
        np.array([day_ahead_price_dkk_mwh]),
        np.array([up_regulation_price_dkk_mwh]),
        np.array([down_regulation_price_dkk_mwh]),
    )
    day_ahead_value = float(day_ahead[0])
    up_value = float(up_regulation[0])
    down_value = float(down_regulation[0])
    scenario_count = scenarios.size

    objective = np.concatenate(
        (
            np.array([-day_ahead_value]),
            -probabilities * down_value,
            probabilities * up_value,
        )
    )
    equality_matrix = np.zeros((scenario_count, 1 + 2 * scenario_count))
    equality_matrix[:, 0] = 1.0
    equality_matrix[:, 1 : 1 + scenario_count] = np.eye(scenario_count)
    equality_matrix[:, 1 + scenario_count :] = -np.eye(scenario_count)
    bounds = [(0.0, capacity_mw)] + [(0.0, None)] * (2 * scenario_count)

    result = linprog(
        c=objective,
        A_eq=equality_matrix,
        b_eq=scenarios,
        bounds=bounds,
        method="highs",
    )
    if not result.success:
        raise RuntimeError(f"Trading LP failed: {result.message}")

    surplus = result.x[1 : 1 + scenario_count]
    shortfall = result.x[1 + scenario_count :]
    return {
        "offer_mw": float(result.x[0]),
        "expected_revenue_dkk": float(-result.fun),
        "surplus_mw": surplus,
        "shortfall_mw": shortfall,
    }


def optimize_offers_from_residuals(
    point_forecasts_mw: np.ndarray,
    calibration_residuals_mw: np.ndarray,
    day_ahead_price_dkk_mwh: np.ndarray,
    up_regulation_price_dkk_mwh: np.ndarray,
    down_regulation_price_dkk_mwh: np.ndarray,
    capacity_mw: float | np.ndarray,
) -> np.ndarray:
    """Apply the exact LP quantile solution using empirical residual scenarios.

    Calibration residuals are treated as equiprobable errors around every point
    forecast. Under the validated price ordering, the stochastic LP solution is
    the empirical production quantile at the interval-specific critical
    fractile. Physical clipping commutes with this monotone quantile operation.
    """
    forecasts = _as_finite_vector(point_forecasts_mw, "point_forecasts_mw")
    residuals = _as_finite_vector(
        calibration_residuals_mw,
        "calibration_residuals_mw",
    )
    day_ahead = np.asarray(day_ahead_price_dkk_mwh, dtype=float)
    up_regulation = np.asarray(up_regulation_price_dkk_mwh, dtype=float)
    down_regulation = np.asarray(down_regulation_price_dkk_mwh, dtype=float)
    if not (
        day_ahead.shape
        == up_regulation.shape
        == down_regulation.shape
        == forecasts.shape
    ):
        raise ValueError("Every price vector must match the point-forecast shape.")

    capacities = np.broadcast_to(np.asarray(capacity_mw, dtype=float), forecasts.shape)
    if not np.isfinite(capacities).all() or (capacities <= 0.0).any():
        raise ValueError("Capacity values must be finite and positive.")
    fractiles = critical_fractile(day_ahead, up_regulation, down_regulation)
    residual_adjustments = np.quantile(
        residuals,
        fractiles,
        method="inverted_cdf",
    )
    return np.clip(forecasts + residual_adjustments, 0.0, capacities)


def expected_scenario_revenue(
    offer_mw: float,
    production_scenarios_mw: np.ndarray,
    scenario_probabilities: np.ndarray,
    day_ahead_price_dkk_mwh: float,
    up_regulation_price_dkk_mwh: float,
    down_regulation_price_dkk_mwh: float,
) -> float:
    """Evaluate the expected objective value for a fixed offer and scenarios."""
    scenarios = _as_finite_vector(
        production_scenarios_mw,
        "production_scenarios_mw",
    )
    probabilities = _as_finite_vector(
        scenario_probabilities,
        "scenario_probabilities",
    )
    if (
        scenarios.size != probabilities.size
        or (probabilities < 0.0).any()
        or not np.isclose(probabilities.sum(), 1.0)
    ):
        raise ValueError(
            "Scenario probabilities must be nonnegative, align and sum to one."
        )
    if not np.isfinite(offer_mw) or offer_mw < 0.0:
        raise ValueError("offer_mw must be finite and nonnegative.")
    if (scenarios < 0.0).any():
        raise ValueError("Production scenarios must be nonnegative.")
    validate_price_order(
        np.array([day_ahead_price_dkk_mwh]),
        np.array([up_regulation_price_dkk_mwh]),
        np.array([down_regulation_price_dkk_mwh]),
    )
    surplus = np.maximum(scenarios - offer_mw, 0.0)
    shortfall = np.maximum(offer_mw - scenarios, 0.0)
    scenario_revenue = (
        day_ahead_price_dkk_mwh * offer_mw
        + down_regulation_price_dkk_mwh * surplus
        - up_regulation_price_dkk_mwh * shortfall
    )
    return float(np.dot(probabilities, scenario_revenue))
