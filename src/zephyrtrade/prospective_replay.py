"""Small, fail-closed controls for decision-time forecast replay.

This module is separate from the retrospective Phase 1-3 study. It does not
connect to a market, submit orders, or evaluate metered farm performance.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from math import isfinite, sqrt
from statistics import fmean
from zoneinfo import ZoneInfo

_QUARTER_HOUR = timedelta(minutes=15)
_UTC_HOUR = timedelta(hours=1)


@dataclass(frozen=True)
class PriceForecastPoint:
    """A prior-day price feature mapped to a target delivery interval."""

    area: str
    input_delivery_utc: datetime
    delivery_utc: datetime
    price_eur_mwh: float


@dataclass(frozen=True)
class ClearingPricePoint:
    """A timestamped day-ahead auction outcome used only for scoring."""

    area: str
    delivery_utc: datetime
    price_eur_mwh: float


@dataclass(frozen=True)
class ProxySchedulePoint:
    """One deterministic proxy schedule row, keyed by UTC delivery start."""

    delivery_utc: datetime
    wind_speed_100m_ms: float
    prior_day_price_eur_mwh: float
    scheduled_mw: float


def _aware_utc(value: datetime, field: str) -> datetime:
    """Normalize an aware timestamp without guessing missing timezone data."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(UTC)


def _local_utc_candidates(local_naive: datetime, zone: ZoneInfo) -> set[datetime]:
    candidates: set[datetime] = set()
    for fold in (0, 1):
        candidate = local_naive.replace(tzinfo=zone, fold=fold)
        timestamp = candidate.astimezone(UTC)
        round_trip = timestamp.astimezone(zone).replace(tzinfo=None)
        if round_trip == local_naive:
            candidates.add(timestamp)
    return candidates


def _clock_is_ambiguous(local_naive: datetime, zone: ZoneInfo) -> bool:
    return len(_local_utc_candidates(local_naive, zone)) > 1


def expected_delivery_starts_utc(
    delivery_date: date,
    timezone_name: str,
    *,
    interval_minutes: int = 15,
) -> tuple[datetime, ...]:
    """Enumerate a local delivery day as UTC starts, including DST day length."""
    if interval_minutes <= 0 or 60 % interval_minutes:
        raise ValueError("interval_minutes must be a positive divisor of 60")
    zone = ZoneInfo(timezone_name)
    local_start = datetime.combine(delivery_date, time.min, tzinfo=zone)
    local_end = datetime.combine(
        delivery_date + timedelta(days=1), time.min, tzinfo=zone
    )
    start_utc = local_start.astimezone(UTC)
    end_utc = local_end.astimezone(UTC)
    step = timedelta(minutes=interval_minutes)
    if end_utc <= start_utc or (end_utc - start_utc) % step:
        raise ValueError("local delivery day has an invalid UTC duration")
    return tuple(
        start_utc + index * step for index in range(int((end_utc - start_utc) / step))
    )


def parse_open_meteo_hourly(
    local_time_labels: Sequence[str | datetime],
    wind_speed_ms: Sequence[float],
    *,
    timezone_name: str,
) -> dict[datetime, float]:
    """Convert Open-Meteo local labels to contiguous UTC hours.

    Ambiguous fall-back labels are rejected unless the source supplies explicit
    UTC offsets. Nonexistent spring-forward labels and missing UTC hours also
    fail closed rather than being inferred or filled.
    """
    if len(local_time_labels) != len(wind_speed_ms) or not local_time_labels:
        raise ValueError("weather times and wind speeds must be non-empty and aligned")
    zone = ZoneInfo(timezone_name)
    result: dict[datetime, float] = {}
    for index, (label, raw_speed) in enumerate(
        zip(local_time_labels, wind_speed_ms, strict=True)
    ):
        local = label if isinstance(label, datetime) else datetime.fromisoformat(label)
        if local.tzinfo is not None and local.utcoffset() is not None:
            timestamp_utc = local.astimezone(UTC)
        else:
            candidates = _local_utc_candidates(local, zone)
            if not candidates:
                raise ValueError(f"nonexistent local timestamp: {local.isoformat()}")
            if len(candidates) != 1:
                raise ValueError(f"ambiguous local timestamp: {local.isoformat()}")
            timestamp_utc = candidates.pop()

        speed = float(raw_speed)
        if not isfinite(speed) or speed < 0.0:
            raise ValueError("weather wind speed must be finite and non-negative")
        if timestamp_utc in result:
            raise ValueError("weather contains duplicate UTC hours")
        result[timestamp_utc] = speed
        if index and timestamp_utc - list(result)[-2] != _UTC_HOUR:
            raise ValueError("weather UTC hours must be contiguous without gaps")
    return result


def same_local_interval_next_day_utc(
    source_delivery_utc: datetime,
    target_date: date,
    *,
    timezone_name: str,
) -> datetime:
    """Map a source interval to the same local clock time on the next day.

    If the target clock time is skipped or repeated by a DST transition, fail
    closed because the local-clock persistence rule does not identify one UTC
    interval.
    """
    source = _aware_utc(source_delivery_utc, "source_delivery_utc")
    if source.minute % 15 or source.second or source.microsecond:
        raise ValueError("source delivery time must be aligned to a UTC quarter-hour")
    zone = ZoneInfo(timezone_name)
    local_source = source.astimezone(zone)
    if local_source.date() + timedelta(days=1) != target_date:
        raise ValueError("source interval must be on the previous local calendar day")
    local_target = datetime.combine(
        target_date, local_source.timetz().replace(tzinfo=None)
    )
    candidates = _local_utc_candidates(local_target, zone)
    if not candidates:
        raise ValueError(f"nonexistent local target: {local_target.isoformat()}")
    if len(candidates) > 1:
        raise ValueError(f"ambiguous local target: {local_target.isoformat()}")
    return candidates.pop()


def require_pre_gate_availability(
    gate_utc: datetime,
    *,
    weather_issued_at_utc: datetime,
    weather_observed_at_utc: datetime,
    price_source_updated_at_utc: datetime,
    price_observed_at_utc: datetime,
) -> None:
    """Require issue/update and receipt times to precede the decision gate."""
    gate = _aware_utc(gate_utc, "gate_utc")
    weather_issued = _aware_utc(weather_issued_at_utc, "weather_issued_at_utc")
    weather_observed = _aware_utc(weather_observed_at_utc, "weather_observed_at_utc")
    price_updated = _aware_utc(
        price_source_updated_at_utc, "price_source_updated_at_utc"
    )
    price_observed = _aware_utc(price_observed_at_utc, "price_observed_at_utc")
    if weather_observed < weather_issued:
        raise ValueError("weather was observed before the model run was issued")
    if price_observed < price_updated:
        raise ValueError("price input was observed before its source version")
    if weather_issued > gate:
        raise ValueError("weather model run was issued after the gate")
    if weather_observed > gate:
        raise ValueError("weather input was observed after the gate")
    if price_updated > gate:
        raise ValueError("price source version was updated after the gate")
    if price_observed > gate:
        raise ValueError("price input was observed after the gate")


def _power_curve_fraction(wind_speed_ms: float) -> float:
    """Return the source's generic 3/12/25 m/s normalized power curve."""
    if wind_speed_ms < 3.0 or wind_speed_ms > 25.0:
        return 0.0
    if wind_speed_ms >= 12.0:
        return 1.0
    return (wind_speed_ms**3 - 3.0**3) / (12.0**3 - 3.0**3)


def build_proxy_schedule(
    deliveries_utc: Sequence[datetime],
    weather_hourly_utc: Mapping[datetime, float],
    price_forecasts: Mapping[datetime, PriceForecastPoint],
    *,
    capacity_mw: float,
    wake_efficiency: float,
    availability: float = 1.0,
) -> tuple[ProxySchedulePoint, ...]:
    """Build a deterministic proxy schedule from inputs available at the gate.

    This is an educational power-curve control, not a fitted strategy. It must
    receive no realized weather, generation, auction outcome, or settlement.
    """
    if not isfinite(capacity_mw) or capacity_mw <= 0.0:
        raise ValueError("capacity_mw must be finite and positive")
    if not isfinite(wake_efficiency) or not 0.0 <= wake_efficiency <= 1.0:
        raise ValueError("wake_efficiency must be finite and between zero and one")
    if not isfinite(availability) or not 0.0 <= availability <= 1.0:
        raise ValueError("availability must be finite and between zero and one")
    deliveries = tuple(_aware_utc(value, "delivery_utc") for value in deliveries_utc)
    if not deliveries:
        raise ValueError("at least one delivery interval is required")
    if any(
        delivery.minute % 15 or delivery.second or delivery.microsecond
        for delivery in deliveries
    ):
        raise ValueError("delivery starts must be aligned to quarter-hours")
    if any(
        deliveries[index + 1] - deliveries[index] != _QUARTER_HOUR
        for index in range(len(deliveries) - 1)
    ):
        raise ValueError("delivery starts must be unique contiguous UTC intervals")

    price_keys = {_aware_utc(key, "price delivery_utc") for key in price_forecasts}
    if price_keys != set(deliveries):
        raise ValueError("price delivery starts do not match the schedule intervals")
    weather: dict[datetime, float] = {}
    for key, value in weather_hourly_utc.items():
        timestamp = _aware_utc(key, "weather delivery_utc")
        speed = float(value)
        if not isfinite(speed) or speed < 0.0:
            raise ValueError("weather wind speed must be finite and non-negative")
        weather[timestamp] = speed

    schedule: list[ProxySchedulePoint] = []
    for delivery in deliveries:
        weather_hour = delivery.replace(minute=0)
        if weather_hour not in weather:
            raise ValueError(f"missing weather hour for {delivery.isoformat()}")
        forecast = price_forecasts[delivery]
        if _aware_utc(forecast.delivery_utc, "forecast.delivery_utc") != delivery:
            raise ValueError("forecast mapping key does not match its delivery time")
        if forecast.area != "DK2":
            raise ValueError("the Rønne proxy schedule requires DK2 price inputs")
        price = float(forecast.price_eur_mwh)
        if not isfinite(price):
            raise ValueError("price forecast must be finite")
        speed = weather[weather_hour]
        scheduled = (
            capacity_mw * wake_efficiency * availability * _power_curve_fraction(speed)
            if price > 0.0
            else 0.0
        )
        schedule.append(ProxySchedulePoint(delivery, speed, price, round(scheduled, 6)))
    return tuple(schedule)


def _require_quarter_hour(value: datetime, field: str) -> datetime:
    timestamp = _aware_utc(value, field)
    if timestamp.minute % 15 or timestamp.second or timestamp.microsecond:
        raise ValueError(f"{field} must be aligned to a UTC quarter-hour")
    return timestamp


def _price_point_is_prior_local_interval(
    point: PriceForecastPoint,
    *,
    delivery_date: date,
    zone: ZoneInfo,
) -> bool:
    target = _require_quarter_hour(point.delivery_utc, "forecast.delivery_utc")
    source = _require_quarter_hour(
        point.input_delivery_utc, "forecast.input_delivery_utc"
    )
    target_local = target.astimezone(zone)
    source_local = source.astimezone(zone)
    if target_local.date() != delivery_date:
        return False
    target_naive = target_local.replace(tzinfo=None)
    source_naive = source_local.replace(tzinfo=None)
    if _clock_is_ambiguous(target_naive, zone) or _clock_is_ambiguous(
        source_naive, zone
    ):
        raise ValueError("ambiguous local interval cannot use same-clock persistence")
    expected_prior_date = delivery_date - timedelta(days=1)
    if source_local.date() != expected_prior_date:
        raise ValueError("price feature must come from the previous local delivery day")
    if source_local.timetz().replace(tzinfo=None) != target_local.timetz().replace(
        tzinfo=None
    ):
        raise ValueError("price feature must use the same local quarter-hour")
    return True


def score_price_forecasts(
    forecasts: Sequence[PriceForecastPoint],
    outcomes: Sequence[ClearingPricePoint],
    *,
    area: str,
    delivery_date: date,
    timezone_name: str,
) -> dict[str, object]:
    """Score two simple price baselines on one shared UTC outcome mask.

    The scores are a one-day price-only diagnostic. They do not score forecast
    wind, offers, metered generation, or a fitted ZephyrTrade model.
    """
    zone = ZoneInfo(timezone_name)
    forecast_by_delivery: dict[datetime, float] = {}
    for point in forecasts:
        if point.area != area:
            continue
        if not _price_point_is_prior_local_interval(
            point, delivery_date=delivery_date, zone=zone
        ):
            continue
        target = _require_quarter_hour(point.delivery_utc, "forecast.delivery_utc")
        value = float(point.price_eur_mwh)
        if not isfinite(value):
            raise ValueError("price forecast must be finite")
        if target in forecast_by_delivery:
            raise ValueError("duplicate price forecast delivery interval")
        forecast_by_delivery[target] = value

    outcome_by_delivery: dict[datetime, float] = {}
    for point in outcomes:
        if point.area != area:
            continue
        target = _require_quarter_hour(point.delivery_utc, "outcome.delivery_utc")
        if target.astimezone(zone).date() != delivery_date:
            continue
        value = float(point.price_eur_mwh)
        if not isfinite(value):
            raise ValueError("auction outcome must be finite")
        if target in outcome_by_delivery:
            raise ValueError("duplicate auction outcome delivery interval")
        outcome_by_delivery[target] = value

    shared = tuple(sorted(forecast_by_delivery.keys() & outcome_by_delivery.keys()))
    previous_day_mean = (
        fmean(forecast_by_delivery.values()) if forecast_by_delivery else None
    )
    baselines: dict[str, dict[str, float | int] | None] = {}
    predictor_values = {
        "previous_day_same_interval": forecast_by_delivery,
        "previous_day_area_mean": (
            dict.fromkeys(forecast_by_delivery, previous_day_mean)
            if previous_day_mean is not None
            else {}
        ),
    }
    for name, predictions in predictor_values.items():
        if not shared:
            baselines[name] = None
            continue
        errors = [
            float(predictions[delivery]) - outcome_by_delivery[delivery]
            for delivery in shared
        ]
        baselines[name] = {
            "n": len(shared),
            "mae_eur_mwh": fmean(abs(error) for error in errors),
            "rmse_eur_mwh": sqrt(fmean(error * error for error in errors)),
            "mean_error_eur_mwh": fmean(errors),
        }

    expected = expected_delivery_starts_utc(delivery_date, timezone_name)
    return {
        "area": area,
        "delivery_date_local": delivery_date.isoformat(),
        "expected_interval_count": len(expected),
        "forecast_input_count": len(forecast_by_delivery),
        "outcome_count": len(outcome_by_delivery),
        "common_interval_count": len(shared),
        "common_delivery_starts_utc": [
            value.isoformat().replace("+00:00", "Z") for value in shared
        ],
        "baselines": baselines,
    }
