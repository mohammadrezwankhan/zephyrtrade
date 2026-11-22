"""Adversarial examples for a hypothetical synthetic issued-power contract."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from zephyrtrade.issuance_contract import (
    IssuedPowerForecast,
    illustrative_gate_utc,
    illustrative_issued_offers,
)


def moment(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def vintage(delivery: datetime, issued: datetime, power: float) -> IssuedPowerForecast:
    return IssuedPowerForecast(delivery, issued, issued + timedelta(minutes=5), power)


def test_gate_is_previous_local_day_not_utc_day_at_dst_transitions() -> None:
    spring = illustrative_gate_utc(moment("2024-03-31T01:00:00Z"))
    autumn = illustrative_gate_utc(moment("2024-10-27T01:00:00Z"))
    assert spring == moment("2024-03-30T11:00:00Z")
    assert autumn == moment("2024-10-26T10:00:00Z")


def test_issued_offer_ignores_future_revisions_but_uses_eligible_vintage() -> None:
    delivery = moment("2024-04-01T00:00:00Z")
    gate = illustrative_gate_utc(delivery)
    first = vintage(delivery, gate - timedelta(hours=2), 6.0)
    late = vintage(delivery, gate + timedelta(minutes=1), 15.0)
    offers = illustrative_issued_offers([delivery], [first, late], capacity_mw=12.0)
    mutated = illustrative_issued_offers(
        [delivery], [first, replace(late, power_mw=999.0)], capacity_mw=12.0
    )
    eligible_mutated = illustrative_issued_offers(
        [delivery], [replace(first, power_mw=7.0), late], capacity_mw=12.0
    )
    assert offers == mutated == (6.0,)
    assert eligible_mutated == (7.0,)


def test_rejects_only_post_deadline_vintage_and_missing_issuance() -> None:
    delivery = moment("2024-04-01T00:00:00Z")
    issued = illustrative_gate_utc(delivery) + timedelta(minutes=1)
    late = vintage(delivery, issued, 3.0)
    with pytest.raises(ValueError, match="No timely issued forecast"):
        illustrative_issued_offers([delivery], [late], capacity_mw=10.0)
    with pytest.raises(ValueError, match="No timely issued forecast"):
        illustrative_issued_offers([delivery], [], capacity_mw=10.0)


def test_missing_hour_and_duplicates_rejected_even_across_dst() -> None:
    delivery = moment("2024-10-27T00:00:00Z")
    missing = [delivery, delivery + timedelta(hours=2)]
    with pytest.raises(ValueError, match="contiguous"):
        illustrative_issued_offers(missing, [], capacity_mw=10.0)
    with pytest.raises(ValueError, match="contiguous"):
        illustrative_issued_offers([delivery, delivery], [], capacity_mw=10.0)
    delivery_hours = [delivery + timedelta(hours=i) for i in range(3)]
    forecasts = [
        vintage(hour, moment("2024-10-26T09:00:00Z"), 3.0) for hour in delivery_hours
    ]
    assert illustrative_issued_offers(delivery_hours, forecasts, capacity_mw=10.0) == (
        3.0,
        3.0,
        3.0,
    )


def test_naive_datetime_and_conflicting_same_issue_are_rejected() -> None:
    delivery = moment("2024-04-01T00:00:00Z")
    issued = illustrative_gate_utc(delivery) - timedelta(hours=2)
    forecast = vintage(delivery, issued, 4.0)
    with pytest.raises(ValueError, match="timezone-aware"):
        illustrative_issued_offers(
            [delivery.replace(tzinfo=None)], [forecast], capacity_mw=10.0
        )
    with pytest.raises(ValueError, match="duplicate"):
        illustrative_issued_offers(
            [delivery], [forecast, replace(forecast, power_mw=5.0)], capacity_mw=10.0
        )
    with pytest.raises(ValueError, match="before it was issued"):
        illustrative_issued_offers(
            [delivery],
            [replace(forecast, available_at_utc=issued - timedelta(seconds=1))],
            capacity_mw=10.0,
        )


def test_duplicate_issue_time_with_different_availability_is_rejected() -> None:
    delivery = moment("2024-04-01T00:00:00Z")
    issued = illustrative_gate_utc(delivery) - timedelta(hours=2)
    first = vintage(delivery, issued, 4.0)
    contradictory = replace(
        first, available_at_utc=issued + timedelta(minutes=6), power_mw=5.0
    )
    with pytest.raises(ValueError, match="duplicate"):
        illustrative_issued_offers(
            [delivery], [first, contradictory], capacity_mw=10.0
        )

def test_realized_future_outcomes_are_not_control_inputs() -> None:
    delivery = moment("2024-04-01T00:00:00Z")
    issued = illustrative_gate_utc(delivery) - timedelta(hours=2)
    forecast = vintage(delivery, issued, 4.0)
    future_observations = {
        "realized_power_mw": 8.0,
        "weather_ms": 12.0,
        "realized_price": -50.0,
    }
    original = illustrative_issued_offers([delivery], [forecast], capacity_mw=10.0)
    future_observations.update(
        realized_power_mw=0.0, weather_ms=100.0, realized_price=900.0
    )
    assert (
        illustrative_issued_offers([delivery], [forecast], capacity_mw=10.0) == original
    )
    assert future_observations["realized_price"] == 900.0


def test_rejects_invalid_capacity_and_nonfinite_forecasts() -> None:
    delivery = moment("2024-04-01T00:00:00Z")
    issued = illustrative_gate_utc(delivery) - timedelta(hours=2)
    with pytest.raises(ValueError, match="capacity_mw"):
        illustrative_issued_offers(
            [delivery], [vintage(delivery, issued, 2.0)], capacity_mw=0.0
        )
    with pytest.raises(ValueError, match="finite"):
        illustrative_issued_offers(
            [delivery], [vintage(delivery, issued, float("nan"))], capacity_mw=10.0
        )


def test_offer_is_clipped_without_realized_prices() -> None:
    delivery = moment("2024-04-01T00:00:00Z")
    issued = illustrative_gate_utc(delivery) - timedelta(hours=2)
    high = illustrative_issued_offers(
        [delivery], [vintage(delivery, issued, 20.0)], capacity_mw=10.0
    )
    low = illustrative_issued_offers(
        [delivery], [vintage(delivery, issued, -20.0)], capacity_mw=10.0
    )
    assert high == (10.0,)
    assert low == (0.0,)


def test_versioned_synthetic_issued_forecast_fixture() -> None:
    fixture = Path(__file__).parent / "fixtures" / "issued_power_v1.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert data["classification"] == "invented_illustrative_only"
    hours = [moment(value) for value in data["delivery_hours_utc"]]
    forecasts = [
        IssuedPowerForecast(
            delivery_utc=moment(entry["delivery_utc"]),
            issued_at_utc=moment(entry["issued_at_utc"]),
            available_at_utc=moment(entry["available_at_utc"]),
            power_mw=entry["power_mw"],
        )
        for entry in data["forecast_vintages"]
    ]
    assert illustrative_issued_offers(
        hours, forecasts, capacity_mw=data["capacity_mw"]
    ) == tuple(data["expected_offers_mw"])
