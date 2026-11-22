"""Decision-time replay controls for timestamped prospective inputs."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

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


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_local_delivery_day_has_dst_aware_utc_quarter_hour_count() -> None:
    spring = expected_delivery_starts_utc(date(2024, 3, 31), "Europe/Copenhagen")
    autumn = expected_delivery_starts_utc(date(2024, 10, 27), "Europe/Copenhagen")
    ordinary = expected_delivery_starts_utc(date(2024, 11, 23), "Europe/Copenhagen")
    assert len(spring) == 92
    assert len(autumn) == 100
    assert len(ordinary) == 96


def test_open_meteo_local_hours_convert_to_contiguous_utc_across_spring_dst() -> None:
    local_times = [
        "2024-03-31T00:00",
        "2024-03-31T01:00",
        "2024-03-31T03:00",
        "2024-03-31T04:00",
    ]
    weather = parse_open_meteo_hourly(
        local_times, [1.0, 2.0, 3.0, 4.0], timezone_name="Europe/Copenhagen"
    )
    assert list(weather) == [
        dt("2024-03-30T23:00:00Z"),
        dt("2024-03-31T00:00:00Z"),
        dt("2024-03-31T01:00:00Z"),
        dt("2024-03-31T02:00:00Z"),
    ]


def test_ambiguous_fall_back_local_weather_requires_explicit_offsets() -> None:
    with pytest.raises(ValueError, match="ambiguous local timestamp"):
        parse_open_meteo_hourly(
            [
                "2024-10-27T01:00",
                "2024-10-27T02:00",
                "2024-10-27T02:00",
                "2024-10-27T03:00",
            ],
            [1.0, 2.0, 3.0, 4.0],
            timezone_name="Europe/Copenhagen",
        )


def test_same_local_interval_mapping_rejects_dst_gaps_and_folds() -> None:
    assert same_local_interval_next_day_utc(
        dt("2026-11-22T22:45:00Z"),
        date(2026, 11, 23),
        timezone_name="Europe/Copenhagen",
    ) == dt("2026-11-23T22:45:00Z")
    with pytest.raises(ValueError, match="ambiguous local target"):
        same_local_interval_next_day_utc(
            dt("2024-10-26T00:00:00Z"),
            date(2024, 10, 27),
            timezone_name="Europe/Copenhagen",
        )
    with pytest.raises(ValueError, match="nonexistent local target"):
        same_local_interval_next_day_utc(
            dt("2024-03-30T01:00:00Z"),
            date(2024, 3, 31),
            timezone_name="Europe/Copenhagen",
        )


def test_nonexistent_local_weather_hour_is_rejected() -> None:
    with pytest.raises(ValueError, match="nonexistent local timestamp"):
        parse_open_meteo_hourly(
            ["2024-03-31T01:00", "2024-03-31T02:00", "2024-03-31T03:00"],
            [1.0, 2.0, 3.0],
            timezone_name="Europe/Copenhagen",
        )


def test_late_input_observation_fails_closed_at_the_cutoff() -> None:
    cutoff = dt("2026-11-22T11:00:00Z")
    require_pre_gate_availability(
        cutoff,
        weather_issued_at_utc=dt("2026-11-22T00:00:00Z"),
        weather_observed_at_utc=dt("2026-11-22T07:59:00Z"),
        price_source_updated_at_utc=dt("2026-11-21T12:06:21.249922Z"),
        price_observed_at_utc=dt("2026-11-22T07:59:25.819862Z"),
    )
    with pytest.raises(ValueError, match="price input was observed after the gate"):
        require_pre_gate_availability(
            cutoff,
            weather_issued_at_utc=dt("2026-11-22T00:00:00Z"),
            weather_observed_at_utc=dt("2026-11-22T07:59:00Z"),
            price_source_updated_at_utc=dt("2026-11-21T12:06:21.249922Z"),
            price_observed_at_utc=cutoff + timedelta(seconds=1),
        )


def test_proxy_schedule_rejects_missing_delivery_or_weather_hours() -> None:
    start = dt("2026-11-22T23:00:00Z")
    deliveries = tuple(start + timedelta(minutes=15 * i) for i in range(8))
    prices = {
        point: PriceForecastPoint("DK2", point - timedelta(hours=24), point, 50.0)
        for point in deliveries
    }
    with pytest.raises(ValueError, match="price delivery starts do not match"):
        build_proxy_schedule(
            deliveries[:-1],
            {start: 10.0, start + timedelta(hours=1): 11.0},
            prices,
            capacity_mw=30.0,
            wake_efficiency=0.94,
            availability=1.0,
        )
    with pytest.raises(ValueError, match="missing weather hour"):
        build_proxy_schedule(
            deliveries,
            {start: 10.0},
            prices,
            capacity_mw=30.0,
            wake_efficiency=0.94,
            availability=1.0,
        )


def test_proxy_schedule_applies_the_declared_availability_factor() -> None:
    delivery = dt("2026-11-22T23:00:00Z")
    forecast = PriceForecastPoint("DK2", delivery - timedelta(hours=24), delivery, 50.0)
    schedule = build_proxy_schedule(
        [delivery],
        {delivery: 12.0},
        {delivery: forecast},
        capacity_mw=30.0,
        wake_efficiency=0.94,
        availability=0.5,
    )
    assert schedule[0].scheduled_mw == 14.1


def test_schedule_is_decision_time_only_and_outcomes_only_change_scores() -> None:
    deliveries = tuple(
        dt("2026-11-22T23:00:00Z") + timedelta(minutes=15 * i) for i in range(4)
    )
    prices = {
        point: PriceForecastPoint("DK2", point - timedelta(hours=24), point, 10.0)
        for point in deliveries
    }
    weather = {deliveries[0]: 10.0}
    schedule = build_proxy_schedule(
        deliveries,
        weather,
        prices,
        capacity_mw=30.0,
        wake_efficiency=0.94,
        availability=1.0,
    )
    actual = [ClearingPricePoint("DK2", point, 20.0) for point in deliveries]
    score = score_price_forecasts(
        list(prices.values()),
        actual,
        area="DK2",
        delivery_date=date(2026, 11, 23),
        timezone_name="Europe/Copenhagen",
    )
    mutated_actual = [
        ClearingPricePoint("DK2", point, -900.0 if i % 2 else 900.0)
        for i, point in enumerate(deliveries)
    ]
    changed_score = score_price_forecasts(
        list(prices.values()),
        mutated_actual,
        area="DK2",
        delivery_date=date(2026, 11, 23),
        timezone_name="Europe/Copenhagen",
    )
    assert schedule == build_proxy_schedule(
        deliveries,
        weather,
        prices,
        capacity_mw=30.0,
        wake_efficiency=0.94,
        availability=1.0,
    )
    assert score["common_interval_count"] == changed_score["common_interval_count"] == 4
    baseline_scores = score["baselines"]
    changed_baselines = changed_score["baselines"]
    assert isinstance(baseline_scores, dict)
    assert isinstance(changed_baselines, dict)
    baseline = baseline_scores["previous_day_same_interval"]
    changed_baseline = changed_baselines["previous_day_same_interval"]
    assert isinstance(baseline, dict)
    assert isinstance(changed_baseline, dict)
    assert baseline["mae_eur_mwh"] == 10.0
    assert changed_baseline["mae_eur_mwh"] == 900.0


def test_two_price_baselines_use_the_same_utc_intersection() -> None:
    deliveries = tuple(
        dt("2026-11-22T23:00:00Z") + timedelta(minutes=15 * i) for i in range(4)
    )
    inputs = [
        PriceForecastPoint("DK2", point - timedelta(hours=24), point, value)
        for point, value in zip(deliveries[:3], [10.0, 20.0, 30.0], strict=True)
    ]
    outcomes = [
        ClearingPricePoint("DK2", point, value)
        for point, value in zip(deliveries[1:], [18.0, 25.0, 30.0], strict=True)
    ]
    result = score_price_forecasts(
        inputs,
        outcomes,
        area="DK2",
        delivery_date=date(2026, 11, 23),
        timezone_name="Europe/Copenhagen",
    )
    assert result["expected_interval_count"] == 96
    assert result["forecast_input_count"] == 3
    assert result["outcome_count"] == 3
    assert result["common_interval_count"] == 2
    assert result["common_delivery_starts_utc"] == [
        point.isoformat().replace("+00:00", "Z") for point in deliveries[1:3]
    ]
    baselines = result["baselines"]
    assert isinstance(baselines, dict)
    assert set(baselines) == {
        "previous_day_same_interval",
        "previous_day_area_mean",
    }
    assert all(
        isinstance(entry, dict) and entry["n"] == result["common_interval_count"]
        for entry in baselines.values()
    )
