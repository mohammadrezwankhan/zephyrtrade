"""Tests for custom and regime-specific regression estimators."""

from __future__ import annotations

import numpy as np

from zephyrtrade.models import (
    ClosedFormLinearRegression,
    ClusteredRidgeRegressor,
    GradientDescentLinearRegression,
    LocallyWeightedLinearRegression,
)


def test_gradient_descent_matches_closed_form_ols() -> None:
    """Batch gradient descent should reproduce closed-form OLS predictions."""
    rng = np.random.default_rng(9)
    features = rng.normal(size=(100, 4))
    target = 2.5 + features @ np.array([1.2, -0.7, 0.3, 2.0])
    closed_form = ClosedFormLinearRegression().fit(features, target)
    gradient_descent = GradientDescentLinearRegression(
        max_iter=200_000,
        tol=1e-12,
    ).fit(features, target)

    assert gradient_descent.converged_
    assert np.allclose(
        gradient_descent.predict(features),
        closed_form.predict(features),
        atol=1e-9,
    )
    assert np.allclose(gradient_descent.coef_, closed_form.coef_, atol=1e-9)


def test_locally_weighted_regression_follows_a_nonlinear_curve() -> None:
    """Local linear fits should approximate a smooth nonlinear response."""
    features = np.linspace(-2.0, 2.0, 240).reshape(-1, 1)
    target = features[:, 0] ** 2
    model = LocallyWeightedLinearRegression(n_neighbors=40, ridge=1e-6).fit(
        features,
        target,
    )
    query = np.array([[-1.5], [-0.5], [0.75], [1.5]])
    prediction = model.predict(query)

    assert np.max(np.abs(prediction - query[:, 0] ** 2)) < 0.08


def test_clustered_regression_predicts_piecewise_regimes() -> None:
    """Clustered local models should learn distinct linear operating regimes."""
    rng = np.random.default_rng(12)
    left = rng.normal(loc=-2.0, scale=0.25, size=(120, 2))
    right = rng.normal(loc=2.0, scale=0.25, size=(120, 2))
    features = np.vstack((left, right))
    target = np.concatenate((1.0 + 0.5 * left[:, 0], 4.0 - 0.8 * right[:, 0]))
    model = ClusteredRidgeRegressor(
        n_clusters=2,
        alpha=1e-5,
        random_state=4,
    ).fit(features, target)
    predictions = model.predict(features)

    assert np.sqrt(np.mean((target - predictions) ** 2)) < 0.03
    assert sum(model.cluster_counts_.values()) == features.shape[0]
