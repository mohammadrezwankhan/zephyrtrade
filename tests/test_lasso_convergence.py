"""Keep CV Lasso retries bounded without changing successful numerical fits."""

from __future__ import annotations

import warnings

import numpy as np
import pytest
from numpy.typing import NDArray
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import Lasso, Ridge
from sklearn.metrics import mean_squared_error

from zephyrtrade import phase2

Fold = tuple[
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
]


@pytest.fixture
def fold() -> Fold:
    return (
        np.array([[0, 1], [1, 0], [2, 1], [3, 2], [4, 1], [5, 3]], dtype=float),
        np.array([1, 2.5, 2, 4, 4.5, 6], dtype=float),
        np.array([[2.5, 1.5], [4.5, 2.5]], dtype=float),
        np.array([3, 5.5], dtype=float),
    )


def test_converged_lasso_keeps_original_fit_and_exact_outputs(
    monkeypatch: pytest.MonkeyPatch, fold: Fold
) -> None:
    features, target, score_features, score_target = fold
    expected = Lasso(
        alpha=0.1,
        max_iter=50_000,
        tol=1e-5,
        selection="cyclic",
        random_state=42,
    ).fit(features, target)
    original_fit = Lasso.fit
    attempts: list[Lasso] = []

    def record_fit(
        estimator: Lasso, x: NDArray[np.float64], y: NDArray[np.float64]
    ) -> Lasso:
        attempts.append(estimator)
        return original_fit(estimator, x, y)

    monkeypatch.setattr(Lasso, "fit", record_fit)
    before = list(warnings.filters)
    alpha, scores = phase2._search_regularization_alpha(
        "lasso", np.array([0.1]), [fold], 42
    )

    assert warnings.filters == before
    assert len(attempts) == 1
    actual = attempts[0]
    assert actual.get_params() == expected.get_params()
    assert actual.n_iter_ == expected.n_iter_
    assert actual.dual_gap_ == expected.dual_gap_
    assert actual.intercept_ == expected.intercept_
    np.testing.assert_array_equal(actual.coef_, expected.coef_)
    np.testing.assert_array_equal(
        actual.predict(score_features), expected.predict(score_features)
    )
    assert alpha == 0.1
    assert float(scores["fold_1_rmse_mw"].iloc[0]) == float(
        np.sqrt(mean_squared_error(score_target, expected.predict(score_features)))
    )


def test_failed_lasso_retries_fresh_with_only_a_larger_iteration_budget(
    monkeypatch: pytest.MonkeyPatch, fold: Fold
) -> None:
    original_fit = Lasso.fit
    attempts: list[Lasso] = []
    parameters: list[dict[str, object]] = []
    fitted_state_present: list[bool] = []

    def fail_initial_fit(
        estimator: Lasso, x: NDArray[np.float64], y: NDArray[np.float64]
    ) -> Lasso:
        attempts.append(estimator)
        parameters.append(estimator.get_params())
        fitted_state_present.append(hasattr(estimator, "coef_"))
        if len(attempts) == 1:
            estimator.coef_ = np.full(x.shape[1], np.nan)
            warnings.warn("Initial budget exhausted", ConvergenceWarning, stacklevel=2)
        return original_fit(estimator, x, y)

    monkeypatch.setattr(Lasso, "fit", fail_initial_fit)
    with warnings.catch_warnings(record=True) as emitted:
        warnings.simplefilter("always", ConvergenceWarning)
        before = list(warnings.filters)
        alpha, scores = phase2._search_regularization_alpha(
            "lasso", np.array([0.1]), [fold], 42
        )
        assert warnings.filters == before

    assert len(attempts) == 2
    assert attempts[0] is not attempts[1]
    assert fitted_state_present == [False, False]
    assert parameters[0]["max_iter"] == 50_000
    assert parameters[1] == parameters[0] | {"max_iter": 1_000_000}
    assert emitted == []
    assert alpha == 0.1
    assert np.isfinite(float(scores["fold_1_rmse_mw"].iloc[0]))
    assert np.isfinite(attempts[1].coef_).all()


def test_retry_nonconvergence_propagates_before_scoring(
    monkeypatch: pytest.MonkeyPatch, fold: Fold
) -> None:
    original_fit = Lasso.fit
    attempts: list[Lasso] = []

    def fail_every_fit(
        estimator: Lasso, x: NDArray[np.float64], y: NDArray[np.float64]
    ) -> Lasso:
        attempts.append(estimator)
        warnings.warn(
            f"Budget {estimator.get_params()['max_iter']} exhausted",
            ConvergenceWarning,
            stacklevel=2,
        )
        return original_fit(estimator, x, y)

    monkeypatch.setattr(Lasso, "fit", fail_every_fit)
    with warnings.catch_warnings():
        warnings.simplefilter("always", ConvergenceWarning)
        before = list(warnings.filters)
        with pytest.raises(ConvergenceWarning, match="Budget 1000000 exhausted"):
            phase2._search_regularization_alpha("lasso", np.array([0.1]), [fold], 42)
        assert warnings.filters == before

    assert len(attempts) == 2
    assert attempts[0] is not attempts[1]


def test_other_lasso_warnings_keep_the_callers_policy_without_retry(
    monkeypatch: pytest.MonkeyPatch, fold: Fold
) -> None:
    original_fit = Lasso.fit
    attempts: list[Lasso] = []

    def unrelated_warning(
        estimator: Lasso, x: NDArray[np.float64], y: NDArray[np.float64]
    ) -> Lasso:
        attempts.append(estimator)
        warnings.warn("Unrelated numerical issue", RuntimeWarning, stacklevel=2)
        return original_fit(estimator, x, y)

    monkeypatch.setattr(Lasso, "fit", unrelated_warning)
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        before = list(warnings.filters)
        with pytest.raises(RuntimeWarning, match="Unrelated numerical issue"):
            phase2._search_regularization_alpha("lasso", np.array([0.1]), [fold], 42)
        assert warnings.filters == before

    assert len(attempts) == 1


def test_ridge_keeps_its_original_fit_and_warning_policy(
    monkeypatch: pytest.MonkeyPatch, fold: Fold
) -> None:
    features, target, score_features, score_target = fold
    expected = Ridge(alpha=0.1).fit(features, target)
    original_fit = Ridge.fit
    attempts: list[Ridge] = []

    def record_ridge_fit(
        estimator: Ridge, x: NDArray[np.float64], y: NDArray[np.float64]
    ) -> Ridge:
        attempts.append(estimator)
        warnings.warn("Ridge warning boundary", ConvergenceWarning, stacklevel=2)
        return original_fit(estimator, x, y)

    monkeypatch.setattr(Ridge, "fit", record_ridge_fit)
    with warnings.catch_warnings(record=True) as emitted:
        warnings.simplefilter("always", ConvergenceWarning)
        before = list(warnings.filters)
        alpha, scores = phase2._search_regularization_alpha(
            "ridge", np.array([0.1]), [fold], 42
        )
        assert warnings.filters == before

    assert len(attempts) == 1
    assert len(emitted) == 1
    assert emitted[0].category is ConvergenceWarning
    assert attempts[0].get_params() == expected.get_params()
    assert attempts[0].intercept_ == expected.intercept_
    np.testing.assert_array_equal(attempts[0].coef_, expected.coef_)
    assert alpha == 0.1
    assert float(scores["fold_1_rmse_mw"].iloc[0]) == float(
        np.sqrt(mean_squared_error(score_target, expected.predict(score_features)))
    )
