"""Forecast and market-value evaluation utilities for ZephyrTrade."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def _aligned_vectors(**vectors: np.ndarray) -> dict[str, np.ndarray]:
    """Validate and return finite aligned one-dimensional float vectors."""
    converted = {
        name: np.asarray(value, dtype=float) for name, value in vectors.items()
    }
    lengths = {value.size for value in converted.values()}
    if len(lengths) != 1:
        raise ValueError("Evaluation vectors must have identical lengths.")
    for name, value in converted.items():
        if value.ndim != 1 or value.size == 0:
            raise ValueError(f"{name} must be a nonempty one-dimensional vector.")
        if not np.isfinite(value).all():
            raise ValueError(f"{name} contains nonfinite values.")
    return converted


def regression_metrics(
    actual_mw: np.ndarray,
    predicted_mw: np.ndarray,
) -> dict[str, float | None]:
    """Return physical-scale errors; R-squared is None for a single interval."""
    values = _aligned_vectors(actual_mw=actual_mw, predicted_mw=predicted_mw)
    actual = values["actual_mw"]
    predicted = values["predicted_mw"]
    return {
        "rmse_mw": float(np.sqrt(mean_squared_error(actual, predicted))),
        "mae_mw": float(mean_absolute_error(actual, predicted)),
        "r2": float(r2_score(actual, predicted)) if actual.size >= 2 else None,
    }


def realized_market_revenue(
    offer_mw: np.ndarray,
    actual_power_mw: np.ndarray,
    day_ahead_price_dkk_mwh: np.ndarray,
    up_regulation_price_dkk_mwh: np.ndarray,
    down_regulation_price_dkk_mwh: np.ndarray,
    interval_hours: float = 1.0,
) -> np.ndarray:
    """Calculate realized day-ahead plus two-price imbalance revenue by interval."""
    if not np.isfinite(interval_hours) or interval_hours <= 0.0:
        raise ValueError("interval_hours must be finite and positive.")
    values = _aligned_vectors(
        offer_mw=offer_mw,
        actual_power_mw=actual_power_mw,
        day_ahead_price=day_ahead_price_dkk_mwh,
        up_regulation_price=up_regulation_price_dkk_mwh,
        down_regulation_price=down_regulation_price_dkk_mwh,
    )
    offer = values["offer_mw"]
    actual = values["actual_power_mw"]
    surplus = np.maximum(actual - offer, 0.0)
    shortfall = np.maximum(offer - actual, 0.0)
    return interval_hours * (
        values["day_ahead_price"] * offer
        + values["down_regulation_price"] * surplus
        - values["up_regulation_price"] * shortfall
    )


def revenue_metrics(
    offer_mw: np.ndarray,
    actual_power_mw: np.ndarray,
    day_ahead_price_dkk_mwh: np.ndarray,
    up_regulation_price_dkk_mwh: np.ndarray,
    down_regulation_price_dkk_mwh: np.ndarray,
    interval_hours: float = 1.0,
) -> dict[str, Any]:
    """Summarize realized revenue, imbalance, and perfect-foresight regret."""
    values = _aligned_vectors(
        offer_mw=offer_mw,
        actual_power_mw=actual_power_mw,
        day_ahead_price=day_ahead_price_dkk_mwh,
        up_regulation_price=up_regulation_price_dkk_mwh,
        down_regulation_price=down_regulation_price_dkk_mwh,
    )
    interval_revenue = realized_market_revenue(
        values["offer_mw"],
        values["actual_power_mw"],
        values["day_ahead_price"],
        values["up_regulation_price"],
        values["down_regulation_price"],
        interval_hours=interval_hours,
    )
    oracle_revenue = (
        interval_hours * values["day_ahead_price"] * values["actual_power_mw"]
    )
    total_revenue = float(interval_revenue.sum())
    total_oracle = float(oracle_revenue.sum())
    imbalance = values["actual_power_mw"] - values["offer_mw"]
    return {
        "total_revenue_dkk": total_revenue,
        "mean_revenue_dkk_per_interval": float(interval_revenue.mean()),
        "perfect_foresight_revenue_dkk": total_oracle,
        "revenue_capture_pct": (
            100.0 * total_revenue / total_oracle if total_oracle > 0.0 else None
        ),
        "revenue_regret_dkk": total_oracle - total_revenue,
        "mean_offer_mw": float(values["offer_mw"].mean()),
        "mean_signed_imbalance_mw": float(imbalance.mean()),
        "total_absolute_imbalance_mwh": float(interval_hours * np.abs(imbalance).sum()),
        "interval_revenue_dkk": interval_revenue,
    }
