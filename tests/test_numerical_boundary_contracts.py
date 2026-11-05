"""Check physical, probability, optimizer, and estimator failure boundaries."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest
from numpy.typing import ArrayLike

from zephyrtrade import optimize
from zephyrtrade.direct import CapacityBracketEncoder, probability_quantile_classes
from zephyrtrade.evaluate import regression_metrics
from zephyrtrade.models import (
    ClusteredRidgeRegressor,
    GradientDescentLinearRegression,
    LocallyWeightedLinearRegression,
    polynomial_ols_pipeline,
    polynomial_regularized_pipeline,
)


@dataclass(frozen=True)
class IncompleteSolution:
    """A failed or incomplete numerical backend receipt with real field types."""

    success: bool
    x: ArrayLike | None
    fun: float | None
    message: str


@pytest.mark.parametrize("target", [[], [[1.0]], [np.nan], [-0.1], [30.1]])
def test_capacity_encoder_rejects_nonphysical_targets(target: ArrayLike) -> None:
    with pytest.raises(ValueError):
        CapacityBracketEncoder(3, 30.0).fit(target)


@pytest.mark.parametrize("brackets,capacity", [(1, 30.0), (3, 0.0), (3, np.nan)])
def test_capacity_encoder_checks_configuration(brackets: int, capacity: float) -> None:
    with pytest.raises(ValueError):
        CapacityBracketEncoder(brackets, capacity).fit([1.0])
    with pytest.raises(ValueError):
        CapacityBracketEncoder(brackets, capacity).transform([1.0])


def test_capacity_encoding_before_fit_and_decoding_contract() -> None:
    encoder = CapacityBracketEncoder(3, 30.0)
    np.testing.assert_array_equal(
        encoder.transform([0.0, 10.0, 20.0, 30.0]), [0, 1, 2, 2]
    )
    with pytest.raises(RuntimeError, match="Fit"):
        encoder.inverse_transform([0])
    encoder.fit([0.0, 2.0, 28.0, 30.0])
    # Empty brackets use their midpoint; populated brackets use the training median.
    np.testing.assert_allclose(encoder.inverse_transform([0, 1, 2]), [1.0, 15.0, 29.0])


@pytest.mark.parametrize("labels", [[[0]], [0.5], [-1], [3]])
def test_capacity_decoder_rejects_invalid_class_identifiers(labels: ArrayLike) -> None:
    encoder = CapacityBracketEncoder(3, 30.0).fit([0.0, 15.0, 30.0])
    with pytest.raises(ValueError):
        encoder.inverse_transform(labels)


@pytest.mark.parametrize(
    "matrix,classes,quantile",
    [
        ([], [0], 0.5),
        ([1.0], [0], 0.5),
        ([[1.0]], [[0]], 0.5),
        ([[1.0]], [0, 1], 0.5),
        ([[1.0]], [0.5], 0.5),
        ([[1.0]], [0], 0.0),
        ([[1.0]], [0], 1.01),
        ([[np.nan]], [0], 0.5),
        ([[-1.0, 2.0]], [0, 1], 0.5),
    ],
)
def test_probability_decisions_reject_invalid_distribution_contracts(
    matrix: ArrayLike,
    classes: ArrayLike,
    quantile: float,
) -> None:
    with pytest.raises(ValueError):
        probability_quantile_classes(matrix, classes, quantile)


@pytest.mark.parametrize(
    "actual,prediction",
    [([], []), ([[1.0]], [[1.0]]), ([1.0], [1.0, 2.0]), ([np.inf], [1.0])],
)
def test_regression_metrics_require_finite_aligned_observations(
    actual: ArrayLike,
    prediction: ArrayLike,
) -> None:
    with pytest.raises(ValueError):
        regression_metrics(actual, prediction)


@pytest.mark.parametrize(
    "scenarios,probabilities,capacity",
    [
        ([], [], 30.0),
        ([np.nan], [1.0], 30.0),
        ([2.0, 8.0], [1.0], 30.0),
        ([2.0, 8.0], [-0.2, 1.2], 30.0),
        ([2.0, 8.0], [0.5, 0.5], 5.0),
    ],
)
def test_explicit_lp_rejects_invalid_scenario_contracts(
    scenarios: ArrayLike,
    probabilities: ArrayLike,
    capacity: float,
) -> None:
    with pytest.raises(ValueError):
        optimize.solve_single_period_offer_lp(
            scenarios, probabilities, 400, 600, 200, capacity
        )


@pytest.mark.parametrize(
    "success,vector,objective",
    [
        (False, None, None),
        (True, None, -3200.0),
        (True, np.array([8.0, 0.0, 0.0]), None),
    ],
)
def test_solver_failure_and_incomplete_success_never_publish_a_solution(
    monkeypatch: pytest.MonkeyPatch,
    success: bool,
    vector: ArrayLike | None,
    objective: float | None,
) -> None:
    def incomplete_solver(**_kwargs: object) -> IncompleteSolution:
        return IncompleteSolution(
            success, vector, objective, "incomplete solver receipt"
        )

    monkeypatch.setattr(optimize, "linprog", incomplete_solver)
    with pytest.raises(RuntimeError, match="Trading LP failed"):
        optimize.solve_single_period_offer_lp([8.0], [1.0], 400, 600, 200, 30)


def test_price_ties_capacity_and_forecast_alignment_are_explicit() -> None:
    with pytest.raises(ValueError, match="exceed"):
        optimize.validate_price_order([400], [400], [400])
    for production, capacity in [([-1.0], 30.0), ([31.0], 30.0), ([1.0], 0.0)]:
        with pytest.raises(ValueError):
            optimize.perfect_foresight_offers(production, [400], [600], [200], capacity)
    with pytest.raises(ValueError, match="point-forecast shape"):
        optimize.optimize_offers_from_residuals(
            [2.0, 3.0], [0.0], [400], [600], [200], 30
        )
    with pytest.raises(ValueError, match="Capacity"):
        optimize.optimize_offers_from_residuals([2.0], [0.0], [400], [600], [200], 0)
    with pytest.raises(ValueError, match="nonnegative"):
        optimize.expected_scenario_revenue(0, [-1.0], [1.0], 400, 600, 200)


def test_gradient_step_bound_and_iteration_cap_are_observable() -> None:
    features = np.array([[0.0], [1.0], [2.0], [3.0]])
    target = 1.0 + 2.0 * features[:, 0]
    with pytest.raises(ValueError, match="learning_rate"):
        GradientDescentLinearRegression(learning_rate=100).fit(features, target)
    model = GradientDescentLinearRegression(max_iter=1, tol=1e-20).fit(features, target)
    assert model.n_iter_ == 1
    assert not model.converged_
    assert np.isfinite(model.predict(features)).all()


def test_local_regression_handles_rank_deficiency_without_changing_constant_power() -> (
    None
):
    features = np.ones((6, 2))
    target = np.full(6, 7.0)
    with pytest.raises(ValueError, match="n_neighbors"):
        LocallyWeightedLinearRegression(n_neighbors=3).fit(features, target)
    model = LocallyWeightedLinearRegression(n_neighbors=6, ridge=0).fit(
        features, target
    )
    np.testing.assert_allclose(model.predict(features[:2]), [7.0, 7.0], atol=1e-12)


@pytest.mark.parametrize(
    "clusters,alpha,indices", [(1, 0.0, None), (2, -1.0, None), (2, 0.0, ())]
)
def test_regime_models_reject_invalid_partition_configuration(
    clusters: int,
    alpha: float,
    indices: tuple[int, ...] | None,
) -> None:
    features = np.array([[0.0], [1.0], [2.0], [3.0]])
    with pytest.raises(ValueError):
        ClusteredRidgeRegressor(clusters, alpha, cluster_feature_indices=indices).fit(
            features, features[:, 0]
        )


def test_sparse_regimes_fall_back_to_the_fitted_global_linear_relation() -> None:
    features = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [3.0, 3.0]])
    target = 1.0 + features @ np.array([2.0, 3.0])
    model = ClusteredRidgeRegressor(n_clusters=3, alpha=0).fit(features, target)
    assert not model.local_models_
    np.testing.assert_allclose(model.predict(features), target, atol=1e-12)
    with pytest.raises(ValueError, match="degree"):
        polynomial_ols_pipeline(0)
    with pytest.raises(ValueError, match="alpha"):
        polynomial_regularized_pipeline("ridge", -1.0)
