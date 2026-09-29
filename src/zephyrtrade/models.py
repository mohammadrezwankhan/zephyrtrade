"""Reusable regression estimators for the ZephyrTrade indirect model."""

from __future__ import annotations

from typing import Literal

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.cluster import KMeans
from sklearn.linear_model import Lasso, LinearRegression, Ridge
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.utils.validation import check_array, check_is_fitted, check_X_y


class ClosedFormLinearRegression(BaseEstimator, RegressorMixin):
    """Ordinary least squares solved with a stable least-squares factorization."""

    def fit(
        self,
        x: np.ndarray,
        y: np.ndarray,
    ) -> ClosedFormLinearRegression:
        """Estimate intercept and coefficients by the Moore-Penrose OLS solution."""
        features, target = check_X_y(x, y, y_numeric=True)
        design = np.column_stack((np.ones(features.shape[0]), features))
        solution, _, rank, singular_values = np.linalg.lstsq(
            design,
            target,
            rcond=None,
        )
        self.intercept_ = float(solution[0])
        self.coef_ = solution[1:]
        self.rank_ = int(rank)
        self.singular_values_ = singular_values
        self.n_features_in_ = features.shape[1]
        residual = design @ solution - target
        self.objective_ = float(0.5 * np.mean(residual**2))
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        """Predict continuous power from a fitted closed-form model."""
        check_is_fitted(self, attributes=["coef_", "intercept_"])
        features = check_array(x)
        return self.intercept_ + features @ self.coef_


class GradientDescentLinearRegression(BaseEstimator, RegressorMixin):
    """Batch-gradient-descent ordinary least squares with a stable step size."""

    def __init__(
        self,
        learning_rate: float | None = None,
        max_iter: int = 500_000,
        tol: float = 1e-10,
    ) -> None:
        """Configure the optional step size, iteration cap, and gradient tolerance."""
        self.learning_rate = learning_rate
        self.max_iter = max_iter
        self.tol = tol

    def fit(
        self,
        x: np.ndarray,
        y: np.ndarray,
    ) -> GradientDescentLinearRegression:
        """Minimize mean squared error with deterministic batch updates."""
        features, target = check_X_y(x, y, y_numeric=True)
        if self.max_iter <= 0 or self.tol <= 0.0:
            raise ValueError("max_iter and tol must be positive.")
        design = np.column_stack((np.ones(features.shape[0]), features))
        hessian = design.T @ design / design.shape[0]
        linear_term = design.T @ target / design.shape[0]
        lipschitz_constant = float(np.linalg.eigvalsh(hessian).max())
        if lipschitz_constant <= 0.0:
            raise ValueError("The regression design has no informative direction.")
        step_size = (
            1.0 / lipschitz_constant
            if self.learning_rate is None
            else self.learning_rate
        )
        if not 0.0 < step_size <= 1.0 / lipschitz_constant:
            raise ValueError("learning_rate must be positive and no larger than 1/L.")

        solution = np.zeros(design.shape[1], dtype=float)
        converged = False
        iteration = 0
        for _ in range(self.max_iter):
            iteration += 1
            gradient = hessian @ solution - linear_term
            if np.linalg.norm(gradient, ord=np.inf) <= self.tol:
                converged = True
                break
            solution -= step_size * gradient

        self.intercept_ = float(solution[0])
        self.coef_ = solution[1:]
        self.n_features_in_ = features.shape[1]
        self.learning_rate_ = float(step_size)
        self.n_iter_ = iteration
        self.converged_ = converged
        residual = design @ solution - target
        self.objective_ = float(0.5 * np.mean(residual**2))
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        """Predict continuous power from fitted gradient-descent coefficients."""
        check_is_fitted(self, attributes=["coef_", "intercept_"])
        features = check_array(x)
        return self.intercept_ + features @ self.coef_


class LocallyWeightedLinearRegression(BaseEstimator, RegressorMixin):
    """K-nearest-neighbor local linear regression with a tricube kernel."""

    def __init__(self, n_neighbors: int = 192, ridge: float = 1e-5) -> None:
        """Configure neighborhood size and local numerical stabilization."""
        self.n_neighbors = n_neighbors
        self.ridge = ridge

    def fit(
        self,
        x: np.ndarray,
        y: np.ndarray,
    ) -> LocallyWeightedLinearRegression:
        """Store training observations and fit a nearest-neighbor search index."""
        features, target = check_X_y(x, y, y_numeric=True)
        if self.n_neighbors < features.shape[1] + 2:
            raise ValueError(
                "n_neighbors must exceed the local design dimension by one."
            )
        if self.ridge < 0.0:
            raise ValueError("ridge must be nonnegative.")
        self.X_train_ = features
        self.y_train_ = target
        self.n_features_in_ = features.shape[1]
        self.effective_neighbors_ = min(self.n_neighbors, features.shape[0])
        self.neighbor_index_ = NearestNeighbors(
            n_neighbors=self.effective_neighbors_,
            algorithm="auto",
            n_jobs=-1,
        ).fit(features)
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        """Fit a weighted local plane at each query and return its intercept."""
        check_is_fitted(
            self,
            attributes=["X_train_", "y_train_", "neighbor_index_"],
        )
        queries = check_array(x)
        distances, neighbor_indices = self.neighbor_index_.kneighbors(queries)
        predictions = np.empty(queries.shape[0], dtype=float)
        penalty = np.eye(self.n_features_in_ + 1)
        penalty[0, 0] = 0.0

        for row_index, query in enumerate(queries):
            local_features = self.X_train_[neighbor_indices[row_index]] - query
            local_target = self.y_train_[neighbor_indices[row_index]]
            design = np.column_stack((np.ones(local_features.shape[0]), local_features))
            radius = max(float(distances[row_index, -1]), np.finfo(float).eps)
            normalized_distance = np.clip(distances[row_index] / radius, 0.0, 1.0)
            weights = (1.0 - normalized_distance**3) ** 3
            weights = np.maximum(weights, 1e-10)
            weighted_design = design * np.sqrt(weights)[:, None]
            weighted_target = local_target * np.sqrt(weights)
            gram = weighted_design.T @ weighted_design + self.ridge * penalty
            right_hand_side = weighted_design.T @ weighted_target
            try:
                coefficients = np.linalg.solve(gram, right_hand_side)
            except np.linalg.LinAlgError:
                coefficients = np.linalg.lstsq(
                    gram,
                    right_hand_side,
                    rcond=None,
                )[0]
            predictions[row_index] = coefficients[0]
        return predictions


class ClusteredRidgeRegressor(BaseEstimator, RegressorMixin):
    """K-means regime segmentation followed by one Ridge model per cluster."""

    def __init__(
        self,
        n_clusters: int = 3,
        alpha: float = 0.1,
        random_state: int = 42,
        cluster_feature_indices: tuple[int, ...] | None = None,
    ) -> None:
        """Configure cluster count, local regularization, and regime features."""
        self.n_clusters = n_clusters
        self.alpha = alpha
        self.random_state = random_state
        self.cluster_feature_indices = cluster_feature_indices

    def fit(
        self,
        x: np.ndarray,
        y: np.ndarray,
    ) -> ClusteredRidgeRegressor:
        """Fit k-means and a local regression model for every populated regime."""
        features, target = check_X_y(x, y, y_numeric=True)
        if self.n_clusters < 2:
            raise ValueError("n_clusters must be at least two.")
        if self.alpha < 0.0:
            raise ValueError("alpha must be nonnegative.")
        indices = (
            np.arange(features.shape[1])
            if self.cluster_feature_indices is None
            else np.asarray(self.cluster_feature_indices, dtype=int)
        )
        if indices.ndim != 1 or indices.size == 0:
            raise ValueError(
                "cluster_feature_indices must select at least one feature."
            )
        if (indices < 0).any() or (indices >= features.shape[1]).any():
            raise ValueError("A cluster feature index is out of bounds.")

        self.cluster_feature_indices_ = indices
        self.kmeans_ = KMeans(
            n_clusters=self.n_clusters,
            n_init=20,
            random_state=self.random_state,
        ).fit(features[:, indices])
        labels = self.kmeans_.labels_
        self.global_model_ = Ridge(alpha=self.alpha).fit(features, target)
        self.local_models_: dict[int, Ridge] = {}
        self.cluster_counts_: dict[int, int] = {}
        minimum_cluster_size = features.shape[1] + 2
        for cluster_id in range(self.n_clusters):
            mask = labels == cluster_id
            count = int(mask.sum())
            self.cluster_counts_[cluster_id] = count
            if count >= minimum_cluster_size:
                self.local_models_[cluster_id] = Ridge(alpha=self.alpha).fit(
                    features[mask],
                    target[mask],
                )
        self.n_features_in_ = features.shape[1]
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        """Assign each observation to a regime and apply its local model."""
        check_is_fitted(self, attributes=["kmeans_", "global_model_"])
        features = check_array(x)
        labels = self.kmeans_.predict(features[:, self.cluster_feature_indices_])
        predictions = np.empty(features.shape[0], dtype=float)
        for cluster_id in range(self.n_clusters):
            mask = labels == cluster_id
            if not mask.any():
                continue
            model = self.local_models_.get(cluster_id, self.global_model_)
            predictions[mask] = model.predict(features[mask])
        return predictions


def polynomial_ols_pipeline(degree: int = 2) -> Pipeline:
    """Construct an unregularized polynomial-regression pipeline."""
    if degree < 1:
        raise ValueError("degree must be positive.")
    return Pipeline(
        steps=[
            ("polynomial", PolynomialFeatures(degree=degree, include_bias=False)),
            ("regressor", LinearRegression()),
        ]
    )


def polynomial_regularized_pipeline(
    penalty: Literal["ridge", "lasso"],
    alpha: float,
    degree: int = 2,
    random_state: int = 42,
) -> Pipeline:
    """Construct a standardized polynomial Ridge or Lasso regression pipeline."""
    if alpha < 0.0:
        raise ValueError("alpha must be nonnegative.")
    if penalty == "ridge":
        regressor: Ridge | Lasso = Ridge(alpha=alpha)
    elif penalty == "lasso":
        regressor = Lasso(
            alpha=alpha,
            max_iter=50_000,
            tol=1e-5,
            selection="cyclic",
            random_state=random_state,
        )
    else:
        raise ValueError("penalty must be 'ridge' or 'lasso'.")
    return Pipeline(
        steps=[
            ("polynomial", PolynomialFeatures(degree=degree, include_bias=False)),
            ("feature_scaler", StandardScaler()),
            ("regressor", regressor),
        ]
    )
