"""Negative-path coverage for the safety-critical prospective replay controls."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from scripts.replay_prospective_record import DEFAULT_MANIFEST, replay
from zephyrtrade.prospective_replay import (
    ClearingPricePoint,
    PriceForecastPoint,
    build_proxy_schedule,
    expected_delivery_starts_utc,
    parse_open_meteo_hourly,
    require_pre_gate_availability,
    same_local_interval_next_day_utc,
    score_price_forecasts,
)

ZONE = "Europe/Copenhagen"
DAY = date(2026, 11, 23)
START = datetime(2026, 11, 22, 23, 0, tzinfo=UTC)


def _forecast(
    delivery: datetime = START,
    *,
    source: datetime | None = None,
    area: str = "DK2",
    value: float = 50.0,
) -> PriceForecastPoint:
    return PriceForecastPoint(
        area,
        source if source is not None else delivery - timedelta(days=1),
        delivery,
        value,
    )


def _score(
    forecasts: list[PriceForecastPoint],
    outcomes: list[ClearingPricePoint] | None = None,
    *,
    delivery_date: date = DAY,
) -> dict[str, object]:
    return score_price_forecasts(
        forecasts,
        outcomes if outcomes is not None else [],
        area="DK2",
        delivery_date=delivery_date,
        timezone_name=ZONE,
    )


@pytest.mark.parametrize(
    "record,field,timestamp,error",
    [
        (
            "recorded_output",
            "schedule_observed_at_utc",
            "2026-11-22T07:59:30Z",
            "schedule was recorded before the weather observation window ended",
        ),
        (
            "price_input",
            "observed_at_utc",
            "2026-11-22T08:02:00Z",
            "schedule was recorded before the price input was observed",
        ),
        (
            "auction_outcome",
            "observed_at_utc",
            "2026-11-22T11:15:00Z",
            "auction was observed before its source version was published",
        ),
    ],
)
def test_replay_rejects_impossible_record_chronology(
    tmp_path: Path, record: str, field: str, timestamp: str, error: str
) -> None:
    manifest = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    target = manifest if record == "recorded_output" else manifest["inputs"]
    target[record][field] = timestamp
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    unused = tmp_path / "unused"

    with pytest.raises(ValueError, match=error):
        replay(
            manifest_path=manifest_path,
            weather_snapshot=unused,
            price_input_csv=unused,
            price_source_response_json=unused,
            price_observation_receipt_json=unused,
            auction_outcome_json=unused,
            auction_observation_receipt_json=unused,
        )


@pytest.mark.parametrize(
    "delivery,local_gate,utc_gate,error",
    [
        (
            "2026-11-23",
            "2026-11-22T12:30:00+01:00",
            "2026-11-22T11:30:00Z",
            "DK2 gate must be noon Copenhagen time on the previous local day",
        ),
        (
            "2026-11-23",
            "2026-11-23T12:00:00+01:00",
            "2026-11-23T11:00:00Z",
            "DK2 gate must be noon Copenhagen time on the previous local day",
        ),
        (
            "2026-03-30",
            "2026-03-29T13:00:00+02:00",
            "2026-03-29T11:00:00Z",
            "DK2 gate must be noon Copenhagen time on the previous local day",
        ),
        (
            "2026-03-30",
            "2026-03-29T12:00:00+02:00",
            "2026-03-29T10:00:00Z",
            "recorded proxy schedule was observed after the gate",
        ),
    ],
)
def test_replay_validates_the_standard_dk2_gate(
    tmp_path: Path, delivery: str, local_gate: str, utc_gate: str, error: str
) -> None:
    manifest = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    manifest["delivery_date_local"] = delivery
    manifest["gate"].update(local=local_gate, utc=utc_gate)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    unused = tmp_path / "unused"
    with pytest.raises(ValueError, match=error):
        replay(
            manifest_path=manifest_path,
            weather_snapshot=unused,
            price_input_csv=unused,
            price_source_response_json=unused,
            price_observation_receipt_json=unused,
            auction_outcome_json=unused,
            auction_observation_receipt_json=unused,
        )


def test_naive_source_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        same_local_interval_next_day_utc(
            START.replace(tzinfo=None), DAY, timezone_name=ZONE
        )


@pytest.mark.parametrize("minutes", [0, -15, 7, 61])
def test_delivery_interval_must_divide_one_hour(minutes: int) -> None:
    with pytest.raises(ValueError, match="positive divisor"):
        expected_delivery_starts_utc(DAY, ZONE, interval_minutes=minutes)


def test_weather_supports_explicit_utc_offset() -> None:
    observed = parse_open_meteo_hourly(
        ["2026-11-22T23:00:00+00:00"], [9.0], timezone_name=ZONE
    )
    assert observed == {START: 9.0}


@pytest.mark.parametrize(
    "labels,speeds,pattern",
    [
        ([], [], "non-empty and aligned"),
        (["2026-11-23T00:00"], [], "non-empty and aligned"),
        (["2026-11-23T00:00"], [-1.0], "finite and non-negative"),
        (["2026-11-23T00:00"], [float("nan")], "finite and non-negative"),
        (
            ["2026-11-22T23:00:00+00:00", "2026-11-23T00:00:00+01:00"],
            [8.0, 9.0],
            "duplicate UTC hours",
        ),
        (
            ["2026-11-23T00:00", "2026-11-23T02:00"],
            [8.0, 9.0],
            "contiguous without gaps",
        ),
    ],
)
def test_weather_rejects_unsafe_hourly_inputs(
    labels: list[str], speeds: list[float], pattern: str
) -> None:
    with pytest.raises(ValueError, match=pattern):
        parse_open_meteo_hourly(labels, speeds, timezone_name=ZONE)


@pytest.mark.parametrize(
    "source,target_date,pattern",
    [
        (START + timedelta(minutes=1), DAY, "aligned"),
        (START, date(2026, 11, 25), "previous local calendar day"),
    ],
)
def test_local_price_persistence_rejects_incompatible_inputs(
    source: datetime, target_date: date, pattern: str
) -> None:
    with pytest.raises(ValueError, match=pattern):
        same_local_interval_next_day_utc(source, target_date, timezone_name=ZONE)


@pytest.mark.parametrize(
    "change,pattern",
    [
        ("weather_seen_before_issue", "observed before the model run"),
        ("price_seen_before_update", "observed before its source version"),
        ("weather_issued_after_gate", "run was issued after the gate"),
        ("weather_seen_after_gate", "weather input was observed after the gate"),
        ("price_updated_after_gate", "source version was updated after the gate"),
    ],
)
def test_vintage_checks_fail_closed_for_each_temporal_invariant(
    change: str, pattern: str
) -> None:
    gate = datetime(2026, 11, 22, 11, 0, tzinfo=UTC)
    defaults: dict[str, datetime] = {
        "weather_issued_at_utc": gate - timedelta(hours=11),
        "weather_observed_at_utc": gate - timedelta(hours=3),
        "price_source_updated_at_utc": gate - timedelta(days=1),
        "price_observed_at_utc": gate - timedelta(hours=2),
    }
    changes: dict[str, dict[str, datetime]] = {
        "weather_seen_before_issue": {
            "weather_issued_at_utc": gate - timedelta(hours=1),
            "weather_observed_at_utc": gate - timedelta(hours=2),
        },
        "price_seen_before_update": {
            "price_source_updated_at_utc": gate - timedelta(hours=1),
            "price_observed_at_utc": gate - timedelta(hours=2),
        },
        "weather_issued_after_gate": {
            "weather_issued_at_utc": gate + timedelta(minutes=1),
            "weather_observed_at_utc": gate + timedelta(minutes=2),
        },
        "weather_seen_after_gate": {
            "weather_observed_at_utc": gate + timedelta(minutes=1),
        },
        "price_updated_after_gate": {
            "price_source_updated_at_utc": gate + timedelta(minutes=1),
            "price_observed_at_utc": gate + timedelta(minutes=2),
        },
    }
    defaults.update(changes[change])
    with pytest.raises(ValueError, match=pattern):
        require_pre_gate_availability(
            gate,
            weather_issued_at_utc=defaults["weather_issued_at_utc"],
            weather_observed_at_utc=defaults["weather_observed_at_utc"],
            price_source_updated_at_utc=defaults["price_source_updated_at_utc"],
            price_observed_at_utc=defaults["price_observed_at_utc"],
        )


@pytest.mark.parametrize(
    "capacity,wake,available,pattern",
    [
        (0.0, 0.94, 1.0, "capacity_mw"),
        (30.0, float("nan"), 1.0, "wake_efficiency"),
        (30.0, 0.94, -0.1, "availability"),
    ],
)
def test_proxy_model_parameters_are_bounded(
    capacity: float, wake: float, available: float, pattern: str
) -> None:
    with pytest.raises(ValueError, match=pattern):
        build_proxy_schedule(
            [START],
            {START: 10.0},
            {START: _forecast()},
            capacity_mw=capacity,
            wake_efficiency=wake,
            availability=available,
        )


@pytest.mark.parametrize(
    "deliveries,pattern",
    [
        ([], "at least one delivery"),
        ([START + timedelta(minutes=1)], "aligned to quarter-hours"),
        ([START, START + timedelta(minutes=30)], "unique contiguous"),
    ],
)
def test_schedule_rejects_empty_unaligned_or_gapped_intervals(
    deliveries: list[datetime], pattern: str
) -> None:
    prices = {delivery: _forecast(delivery) for delivery in deliveries}
    with pytest.raises(ValueError, match=pattern):
        build_proxy_schedule(
            deliveries,
            {START: 10.0},
            prices,
            capacity_mw=30.0,
            wake_efficiency=0.94,
        )


@pytest.mark.parametrize(
    "kind,pattern",
    [
        ("bad_weather", "finite and non-negative"),
        ("forecast_target", "key does not match"),
        ("wrong_area", "requires DK2"),
        ("bad_price", "price forecast must be finite"),
    ],
)
def test_schedule_rejects_corrupted_weather_and_price_inputs(
    kind: str, pattern: str
) -> None:
    weather = {START: float("nan") if kind == "bad_weather" else 10.0}
    forecast = _forecast(
        delivery=START + timedelta(minutes=15) if kind == "forecast_target" else START,
        area="DK1" if kind == "wrong_area" else "DK2",
        value=float("nan") if kind == "bad_price" else 10.0,
    )
    with pytest.raises(ValueError, match=pattern):
        build_proxy_schedule(
            [START],
            weather,
            {START: forecast},
            capacity_mw=30.0,
            wake_efficiency=0.94,
        )


@pytest.mark.parametrize(
    "source,pattern",
    [
        (START, "previous local delivery day"),
        (START - timedelta(days=1, minutes=15), "previous local delivery day"),
        (START - timedelta(days=1) + timedelta(minutes=15), "same local quarter-hour"),
        (START.replace(tzinfo=None), "timezone-aware"),
    ],
)
def test_schedule_rejects_price_from_wrong_source_interval(
    source: datetime, pattern: str
) -> None:
    with pytest.raises(ValueError, match=pattern):
        build_proxy_schedule(
            [START],
            {START: 10.0},
            {START: _forecast(source=source)},
            capacity_mw=30.0,
            wake_efficiency=0.94,
        )


@pytest.mark.parametrize("wind,price", [(2.0, 10.0), (26.0, 10.0), (10.0, -5.0)])
def test_proxy_schedule_zeroes_unsafe_or_negative_price_operating_regions(
    wind: float, price: float
) -> None:
    schedule = build_proxy_schedule(
        [START],
        {START: wind},
        {START: _forecast(value=price)},
        capacity_mw=30.0,
        wake_efficiency=0.94,
    )
    assert schedule[0].scheduled_mw == 0.0


@pytest.mark.parametrize(
    "kind,pattern",
    [
        ("unaligned_source", "aligned to a UTC quarter-hour"),
        ("wrong_previous_day", "previous local delivery day"),
        ("wrong_clock", "same local quarter-hour"),
        ("nan_forecast", "price forecast must be finite"),
        ("duplicate_forecast", "duplicate price forecast"),
        ("nan_outcome", "auction outcome must be finite"),
        ("duplicate_outcome", "duplicate auction outcome"),
        ("ambiguous_dst_target", "ambiguous local interval"),
    ],
)
def test_scoring_rejects_corrupt_inputs_and_ambiguous_dst(
    kind: str, pattern: str
) -> None:
    if kind == "ambiguous_dst_target":
        target = datetime(2024, 10, 27, 0, 0, tzinfo=UTC)
        source = datetime(2024, 10, 26, 0, 0, tzinfo=UTC)
        with pytest.raises(ValueError, match=pattern):
            _score([_forecast(target, source=source)], delivery_date=date(2024, 10, 27))
        return
    source = START - timedelta(days=1)
    if kind == "unaligned_source":
        source += timedelta(minutes=1)
    elif kind == "wrong_previous_day":
        source -= timedelta(days=1)
    elif kind == "wrong_clock":
        source += timedelta(minutes=15)
    forecast = _forecast(
        source=source, value=float("nan") if kind == "nan_forecast" else 10.0
    )
    forecasts = [forecast, forecast] if kind == "duplicate_forecast" else [forecast]
    outcome = ClearingPricePoint(
        "DK2", START, float("nan") if kind == "nan_outcome" else 20.0
    )
    outcomes = [outcome, outcome] if kind == "duplicate_outcome" else [outcome]
    with pytest.raises(ValueError, match=pattern):
        _score(forecasts, outcomes)


@pytest.mark.parametrize(
    "case",
    ["forecast_area", "forecast_day", "outcome_area", "outcome_day", "no_shared"],
)
def test_scoring_excludes_unmatched_inputs_without_inventing_scores(case: str) -> None:
    forecast = _forecast(area="DK1" if case == "forecast_area" else "DK2")
    delivery_day = date(2026, 11, 24) if case == "forecast_day" else DAY
    outcome = ClearingPricePoint(
        "DK1" if case == "outcome_area" else "DK2",
        START + timedelta(days=1) if case == "outcome_day" else START,
        20.0,
    )
    outcomes = [] if case == "no_shared" else [outcome]
    result = _score([forecast], outcomes, delivery_date=delivery_day)
    assert result["common_interval_count"] == 0
    baselines = result["baselines"]
    assert isinstance(baselines, dict)
    assert baselines == {
        "previous_day_same_interval": None,
        "previous_day_area_mean": None,
    }
