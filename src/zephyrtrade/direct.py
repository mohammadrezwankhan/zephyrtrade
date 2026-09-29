"""Utilities for direct wind-energy offer learning."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _finite_vector(values: np.ndarray, name: str) -> np.ndarray:
    """Return a validated, one-dimensional float vector."""
    vector = np.asarray(values, dtype=float)
    if vector.ndim != 1 or vector.size == 0:
        raise ValueError(f"{name} must be a nonempty one-dimensional vector.")
    if not np.isfinite(vector).all():
        raise ValueError(f"{name} must contain only finite values.")
    return vector


@dataclass
class CapacityBracketEncoder:
    """Encode continuous offers as fixed capacity brackets.

    Bracket edges are uniformly spaced over the physical capacity. Each class
    is decoded to the median training target observed in that bracket, with the
    bracket midpoint used only when the training set contains no such target.
    """

    n_brackets: int
    capacity_mw: float

    def fit(self, target_mw: np.ndarray) -> CapacityBracketEncoder:
        """Estimate one representative offer for each capacity bracket."""
        if self.n_brackets < 2:
            raise ValueError("n_brackets must be at least two.")
        if not np.isfinite(self.capacity_mw) or self.capacity_mw <= 0.0:
            raise ValueError("capacity_mw must be finite and positive.")
        target = self._validate_target(target_mw)
        self.edges_ = np.linspace(0.0, self.capacity_mw, self.n_brackets + 1)
        labels = self.transform(target)
        midpoints = 0.5 * (self.edges_[:-1] + self.edges_[1:])
        representatives = midpoints.copy()
        for class_id in range(self.n_brackets):
            class_values = target[labels == class_id]
            if class_values.size:
                representatives[class_id] = np.median(class_values)
        self.representatives_ = representatives
        return self

    def transform(self, target_mw: np.ndarray) -> np.ndarray:
        """Map feasible continuous targets to integer bracket labels."""
        target = self._validate_target(target_mw)
        if not hasattr(self, "edges_"):
            self.edges_ = np.linspace(
                0.0,
                self.capacity_mw,
                self.n_brackets + 1,
            )
        return np.digitize(target, self.edges_[1:-1], right=False).astype(int)

    def inverse_transform(self, labels: np.ndarray) -> np.ndarray:
        """Decode integer classes to their learned discrete offer values."""
        if not hasattr(self, "representatives_"):
            raise RuntimeError("Fit the bracket encoder before decoding labels.")
        encoded = np.asarray(labels)
        if encoded.ndim != 1 or not np.issubdtype(encoded.dtype, np.integer):
            raise ValueError("labels must be a one-dimensional integer vector.")
        if (encoded < 0).any() or (encoded >= self.n_brackets).any():
            raise ValueError("labels contain a class outside the fitted brackets.")
        return self.representatives_[encoded]

    def _validate_target(self, target_mw: np.ndarray) -> np.ndarray:
        """Validate targets against the physical offer interval."""
        if not isinstance(self.n_brackets, (int, np.integer)) or self.n_brackets < 2:
            raise ValueError("n_brackets must be an integer of at least two.")
        if not np.isfinite(self.capacity_mw) or self.capacity_mw <= 0.0:
            raise ValueError("capacity_mw must be finite and positive.")
        target = _finite_vector(target_mw, "target_mw")
        if (target < 0.0).any() or (target > self.capacity_mw).any():
            raise ValueError("Targets must lie between zero and capacity_mw.")
        return target


def probability_quantile_classes(
    probabilities: np.ndarray,
    classes: np.ndarray,
    decision_quantile: float,
) -> np.ndarray:
    """Choose discrete classes from a predictive cumulative distribution."""
    matrix = np.asarray(probabilities, dtype=float)
    class_ids = np.asarray(classes)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError("probabilities must be a nonempty two-dimensional matrix.")
    if class_ids.ndim != 1 or class_ids.size != matrix.shape[1]:
        raise ValueError("classes must align with probability columns.")
    if not np.issubdtype(class_ids.dtype, np.integer):
        raise ValueError("classes must be integer identifiers.")
    if (class_ids < 0).any() or np.unique(class_ids).size != class_ids.size:
        raise ValueError("classes must be unique and nonnegative.")
    if not 0.0 < decision_quantile <= 1.0:
        raise ValueError("decision_quantile must lie in (0, 1].")
    if not np.isfinite(matrix).all() or (matrix < 0.0).any():
        raise ValueError("probabilities must be finite and nonnegative.")
    row_sums = matrix.sum(axis=1)
    if not np.allclose(row_sums, 1.0, atol=1e-7):
        raise ValueError("Each probability row must sum to one.")

    order = np.argsort(class_ids)
    sorted_classes = class_ids[order]
    # Accepted floating-point roundoff must not make q=1 wrap to class zero.
    normalized = matrix / row_sums[:, None]
    cumulative = np.cumsum(normalized[:, order], axis=1)
    cumulative[:, -1] = 1.0
    selected_indices = np.argmax(cumulative + 1e-12 >= decision_quantile, axis=1)
    return sorted_classes[selected_indices].astype(int)


def probability_quantile_offers(
    probabilities: np.ndarray,
    classes: np.ndarray,
    encoder: CapacityBracketEncoder,
    decision_quantile: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Convert class probabilities into labels and feasible discrete offers."""
    labels = probability_quantile_classes(
        probabilities,
        classes,
        decision_quantile,
    )
    return labels, encoder.inverse_transform(labels)
