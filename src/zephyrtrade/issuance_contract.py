"""Illustrative issued-power contract; not used by archived ex-post studies.

The hypothetical previous-day noon gate in Europe/Copenhagen is a test
assumption, not a claim about a real market or actual forecast vintages.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from math import isfinite
from zoneinfo import ZoneInfo

_COPENHAGEN = ZoneInfo("Europe/Copenhagen")
_INTERVAL = timedelta(hours=1)


@dataclass(frozen=True)
class IssuedPowerForecast:
    """Forecast with explicit issue, availability and delivery timestamps."""

    delivery_utc: datetime
    issued_at_utc: datetime
    available_at_utc: datetime
    power_mw: float


def _aware_utc(value: datetime, field: str) -> datetime:
    """Normalize an aware timestamp to UTC; never guess an absent timezone."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(UTC)


def illustrative_gate_utc(delivery_utc: datetime) -> datetime:
    """Return hypothetical previous-local-day noon, DST-safe in Copenhagen."""
    delivery = _aware_utc(delivery_utc, "delivery_utc")
    previous_day = delivery.astimezone(_COPENHAGEN).date() - timedelta(days=1)
    local_gate = datetime.combine(previous_day, time(12), tzinfo=_COPENHAGEN)
    return local_gate.astimezone(UTC)


def illustrative_issued_offers(
    deliveries_utc: Sequence[datetime],
    forecasts: Sequence[IssuedPowerForecast],
    *,
    capacity_mw: float,
) -> tuple[float, ...]:
    """Select only forecast vintages available at the hypothetical gate.

    Reject missing/ambiguous eligible vintages and missing UTC delivery hours.
    Ex-post production and realised prices are deliberately not inputs.
    This is a deterministic synthetic control, not an optimized policy.
    """
    if not isfinite(capacity_mw) or capacity_mw <= 0.0:
        raise ValueError("capacity_mw must be finite and positive")
    deliveries = [_aware_utc(value, "delivery_utc") for value in deliveries_utc]
    if not deliveries:
        raise ValueError("At least one delivery interval is required")
    # Hourly settlement inputs must be aligned to the UTC hour, including
    # singleton sequences (which cannot fail a contiguity-only check).
    if any(
        delivery.minute or delivery.second or delivery.microsecond
        for delivery in deliveries
    ):
        raise ValueError("Delivery intervals must start on a whole UTC hour")
    if any(
        deliveries[i + 1] - deliveries[i] != _INTERVAL
        for i in range(len(deliveries) - 1)
    ):
        raise ValueError("Delivery intervals must be contiguous, unique UTC hours")

    by_delivery: dict[datetime, list[tuple[datetime, datetime, float]]] = {}
    for forecast in forecasts:
        target = _aware_utc(forecast.delivery_utc, "forecast.delivery_utc")
        issued = _aware_utc(forecast.issued_at_utc, "forecast.issued_at_utc")
        available = _aware_utc(forecast.available_at_utc, "forecast.available_at_utc")
        if available < issued:
            raise ValueError("Forecast cannot be available before it was issued")
        if not isfinite(forecast.power_mw):
            raise ValueError("Forecast power must be finite")
        by_delivery.setdefault(target, []).append(
            (issued, available, forecast.power_mw)
        )

    offers: list[float] = []
    for delivery in deliveries:
        gate = illustrative_gate_utc(delivery)
        eligible = [
            vintage
            for vintage in by_delivery.get(delivery, [])
            if vintage[0] <= gate and vintage[1] <= gate
        ]
        if not eligible:
            raise ValueError(f"No timely issued forecast for {delivery.isoformat()}")
        eligible.sort(key=lambda vintage: (vintage[0], vintage[1]))
        # An issuance timestamp identifies one source version, regardless of
        # when identical-timestamp records became available. Never choose an
        # arbitrary version from contradictory issue-time records.
        if len(eligible) > 1 and eligible[-1][0] == eligible[-2][0]:
            raise ValueError("Conflicting or duplicate newest forecast vintage")
        offers.append(min(max(eligible[-1][2], 0.0), capacity_mw))
    return tuple(offers)
