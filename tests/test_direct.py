"""Tests for direct-offer targets and classification utilities."""

from __future__ import annotations

import numpy as np
import pytest

from zephyrtrade.direct import (
    CapacityBracketEncoder,
    probability_quantile_classes,
    probability_quantile_offers,
)
from zephyrtrade.optimize import perfect_foresight_offers


def test_perfect_foresight_offer_equals_known_production() -> None:
    """The deterministic LP label should equal the realized power scenario."""
    actual = np.array([0.0, 5.0, 19.5, 30.0])
    offers = perfect_foresight_offers(
        actual,
        day_ahead_price_dkk_mwh=np.full(4, 400.0),
        up_regulation_price_dkk_mwh=np.full(4, 600.0),
        down_regulation_price_dkk_mwh=np.full(4, 300.0),
        capacity_mw=30.0,
    )

    np.testing.assert_array_equal(offers, actual)


def test_capacity_brackets_decode_to_training_medians() -> None:
    """Observed classes should use their median target as the bid amount."""
    target = np.array([1.0, 2.0, 8.0, 12.0, 18.0, 29.0])
    encoder = CapacityBracketEncoder(n_brackets=3, capacity_mw=30.0).fit(target)
    labels = encoder.transform(np.array([0.0, 10.0, 30.0]))

    np.testing.assert_array_equal(labels, np.array([0, 1, 2]))
    np.testing.assert_allclose(
        encoder.inverse_transform(labels),
        np.array([2.0, 15.0, 29.0]),
    )


def test_probability_quantile_selects_ordered_classes_and_offers() -> None:
    """Decision quantiles should map probability mass to discrete bid classes."""
    encoder = CapacityBracketEncoder(3, 30.0).fit(np.array([2.0, 12.0, 22.0]))
    probabilities = np.array([[0.2, 0.5, 0.3], [0.7, 0.1, 0.2]])
    classes = np.array([0, 1, 2])
    low = probability_quantile_classes(probabilities, classes, 0.2)
    labels, offers = probability_quantile_offers(
        probabilities,
        classes,
        encoder,
        0.8,
    )

    np.testing.assert_array_equal(low, np.array([0, 0]))
    np.testing.assert_array_equal(labels, np.array([2, 1]))
    np.testing.assert_allclose(offers, np.array([22.0, 12.0]))


def test_probability_quantile_rejects_invalid_rows() -> None:
    """Malformed class probabilities should fail early."""
    with pytest.raises(ValueError, match="sum to one"):
        probability_quantile_classes(
            np.array([[0.2, 0.2]]),
            np.array([0, 1]),
            0.5,
        )
