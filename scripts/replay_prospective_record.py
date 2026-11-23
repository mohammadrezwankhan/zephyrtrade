"""Replay the archived 23 November 2026 Rønne proxy decision record.

Raw provider files are intentionally supplied by the caller. This script only
reads local files and prints a compact JSON receipt; it makes no network calls.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import UTC, date, datetime, time, timedelta
from email.utils import parsedate_to_datetime
from math import isfinite
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

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

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs" / "champion" / "evidence" / "ronne-20261123-v1.json"


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _parse_utc(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid {field}: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a UTC offset")
    return parsed.astimezone(UTC)


def _verify_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise ValueError(f"{label} input does not exist: {path}")
    observed = _sha256(path)
    if observed != expected:
        raise ValueError(f"{label} SHA-256 mismatch: {observed}")


def _parse_weather(
    path: Path, manifest: dict[str, Any]
) -> tuple[dict[datetime, float], str]:
    expected = manifest["inputs"]["weather"]
    _verify_file(path, expected["snapshot_sha256"], "weather snapshot")
    snapshot = json.loads(path.read_text(encoding="utf-8-sig"))
    response = snapshot["open_meteo_single_run"]
    body = response["raw_body"]
    body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    if body_hash != expected["body_sha256"] or body_hash != response["body_sha256"]:
        raise ValueError("Open-Meteo response body SHA-256 mismatch")
    query = parse_qs(urlparse(response["url"]).query)
    if query.get("models") != ["ecmwf_ifs"]:
        raise ValueError("weather request is not the recorded ECMWF IFS run")
    run_time = query.get("run", [""])[0]
    if run_time != "2026-11-22T00:00":
        raise ValueError("weather request has an unexpected model run time")
    if response["status"] != 200:
        raise ValueError("Open-Meteo source response was not successful")
    observed_lower = _parse_utc(
        expected["observed_lower_bound_utc"], "weather observation lower bound"
    )
    observed_upper = _parse_utc(
        expected["observed_upper_bound_utc"], "weather observation upper bound"
    )
    response_server_date = _parse_utc(response["server_date"], "weather server Date")
    if not observed_lower <= response_server_date < observed_upper:
        raise ValueError(
            "weather server Date is outside the recorded observation minute"
        )

    payload = json.loads(body)
    if payload["timezone"] != manifest["timezone"]:
        raise ValueError("weather response timezone does not match the replay manifest")
    if payload["hourly_units"]["wind_speed_100m"] != "m/s":
        raise ValueError("weather source wind-speed unit is not m/s")
    weather = parse_open_meteo_hourly(
        payload["hourly"]["time"],
        payload["hourly"]["wind_speed_100m"],
        timezone_name=payload["timezone"],
    )

    delivery_date = date.fromisoformat(manifest["delivery_date_local"])
    zone_name = manifest["timezone"]
    zone = ZoneInfo(zone_name)
    target_hours = expected_delivery_starts_utc(
        delivery_date, zone_name, interval_minutes=60
    )
    if len(target_hours) != 24:
        raise ValueError("recorded proxy date should contain 24 hourly weather inputs")
    recorded = response["target_hours_2026_11_23"]
    recorded_by_utc: dict[datetime, float] = {}
    for row in recorded:
        local = datetime.fromisoformat(row["time"])
        aware = local.replace(tzinfo=zone)
        key = aware.astimezone(UTC)
        recorded_by_utc[key] = float(row["wind_speed_100m_ms"])
    if set(recorded_by_utc) != set(target_hours):
        raise ValueError("snapshot target-hour summary does not cover the delivery day")
    if any(weather[key] != value for key, value in recorded_by_utc.items()):
        raise ValueError("snapshot target-hour summary differs from its raw body")
    return weather, body_hash


def _parse_price_input(
    path: Path,
    source_response_path: Path,
    observation_receipt_path: Path,
    manifest: dict[str, Any],
) -> tuple[list[PriceForecastPoint], str, str]:
    meta = manifest["inputs"]["price_input"]
    _verify_file(path, meta["derived_input_csv_sha256"], "price input CSV")
    source_hash = meta["raw_response_sha256"]
    _verify_file(source_response_path, source_hash, "price source response")
    observation_hash = meta["observation_receipt_sha256"]
    _verify_file(
        observation_receipt_path, observation_hash, "price observation receipt"
    )

    zone = ZoneInfo(manifest["timezone"])
    delivery_date = date.fromisoformat(manifest["delivery_date_local"])
    input_date = delivery_date - timedelta(days=1)
    gate = _parse_utc(manifest["gate"]["utc"], "gate")
    receipt = json.loads(observation_receipt_path.read_text(encoding="utf-8-sig"))
    source_payload = json.loads(source_response_path.read_text(encoding="utf-8-sig"))
    if (
        receipt["provider"] != "Nord Pool"
        or receipt["source_version"] != meta["source_version"]
    ):
        raise ValueError(
            "price observation receipt does not identify the expected source"
        )
    if receipt["source_updated_at"] != meta["source_updated_at_utc"]:
        raise ValueError("price observation receipt source version timestamp mismatch")
    if _parse_utc(
        receipt["observed_by_utc"], "price receipt observation"
    ) != _parse_utc(meta["observed_at_utc"], "price observation"):
        raise ValueError("price observation receipt timestamp mismatch")
    if receipt["url"] != meta["source_url"]:
        raise ValueError("price observation receipt URL mismatch")
    if receipt["raw_sha256"] != source_hash or receipt["forecast_sha256"] != _sha256(
        path
    ):
        raise ValueError("price observation receipt hash chain mismatch")
    if receipt["rows"] != 192:
        raise ValueError("price observation receipt does not contain 192 source rows")
    http_date = parsedate_to_datetime(receipt["http_date"]).astimezone(UTC)
    observed_at = _parse_utc(receipt["observed_by_utc"], "price observation")
    deadline = _parse_utc(receipt["next_bid_deadline_utc"], "next bid deadline")
    if not http_date <= observed_at <= gate or deadline != gate:
        raise ValueError("price response receipt is not valid for the recorded gate")

    source_date_text = input_date.isoformat()
    if (
        source_payload["deliveryDateCET"] != source_date_text
        or source_payload["version"] != meta["source_version"]
        or source_payload["updatedAt"] != meta["source_updated_at_utc"]
        or source_payload["market"] != "DayAhead"
        or source_payload["currency"] != "EUR"
    ):
        raise ValueError("price response metadata does not match the receipt")
    areas = source_payload["deliveryAreas"]
    if len(areas) != 2 or set(areas) != {"DK1", "DK2"}:
        raise ValueError("price response areas do not match the receipt")

    expected_source = set(
        expected_delivery_starts_utc(input_date, manifest["timezone"])
    )
    expected_target = set(
        expected_delivery_starts_utc(delivery_date, manifest["timezone"])
    )
    source_starts: set[datetime] = set()
    expected_csv_rows: dict[tuple[str, datetime, datetime], float] = {}
    points: list[PriceForecastPoint] = []
    for row in source_payload["multiAreaEntries"]:
        source = _parse_utc(row["deliveryStart"], "source price delivery start")
        end = _parse_utc(row["deliveryEnd"], "source price delivery end")
        if source.astimezone(zone).date() != input_date:
            continue
        if end - source != timedelta(minutes=15):
            raise ValueError(
                "source price response contains a non-quarter-hour interval"
            )
        if source in source_starts:
            raise ValueError("source price response contains duplicate intervals")
        source_starts.add(source)
        target = same_local_interval_next_day_utc(
            source, delivery_date, timezone_name=manifest["timezone"]
        )
        values = row["entryPerArea"]
        for area in areas:
            price = float(values[area])
            if not isfinite(price):
                raise ValueError("source price response contains a non-finite value")
            expected_csv_rows[(area, source, target)] = price
            if area == manifest["market_area"]:
                points.append(PriceForecastPoint(area, source, target, price))

    if source_starts != expected_source or len(expected_csv_rows) != 192:
        raise ValueError(
            "source price response must cover 96 quarter-hours in both areas"
        )
    if {point.delivery_utc for point in points} != expected_target:
        raise ValueError(
            "derived price forecast does not cover the target UTC intervals"
        )

    seen_csv_rows: set[tuple[str, datetime, datetime]] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {
            "area",
            "input_delivery_start_utc",
            "target_delivery_start_utc",
            "locked_forecast_eur_per_mwh",
        }
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("price input CSV is missing required columns")
        for row in reader:
            area = row["area"]
            source = _parse_utc(row["input_delivery_start_utc"], "price input time")
            target = _parse_utc(row["target_delivery_start_utc"], "price target time")
            key = (area, source, target)
            price = float(row["locked_forecast_eur_per_mwh"])
            if key not in expected_csv_rows or key in seen_csv_rows:
                raise ValueError("derived price CSV rows do not match source intervals")
            if not isfinite(price) or price != expected_csv_rows[key]:
                raise ValueError("derived price CSV value differs from source response")
            seen_csv_rows.add(key)
    if seen_csv_rows != set(expected_csv_rows):
        raise ValueError(
            "derived price CSV does not preserve every source area interval"
        )
    return points, source_hash, observation_hash


def _parse_auction_outcomes(
    path: Path, observation_receipt_path: Path, manifest: dict[str, Any]
) -> tuple[list[ClearingPricePoint], dict[datetime, float], str]:
    meta = manifest["inputs"]["auction_outcome"]
    _verify_file(path, meta["response_sha256"], "auction outcome")
    receipt_hash = meta["observation_receipt_sha256"]
    _verify_file(observation_receipt_path, receipt_hash, "auction observation receipt")
    receipt = json.loads(observation_receipt_path.read_text(encoding="utf-8-sig"))
    if (
        receipt["source_sha256"] != meta["response_sha256"]
        or receipt["source_version"] != meta["source_version"]
        or receipt["source_updated_utc"] != meta["source_updated_at_utc"]
        or _parse_utc(receipt["observed_utc"], "auction receipt observation")
        != _parse_utc(meta["observed_at_utc"], "auction observation")
    ):
        raise ValueError("auction observation receipt does not match the manifest")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if payload["market"] != "DayAhead" or payload["version"] != 2:
        raise ValueError("auction outcome is not the recorded day-ahead v2 response")
    if payload["deliveryDateCET"] != manifest["delivery_date_local"]:
        raise ValueError("auction delivery date does not match the replay record")
    if payload["updatedAt"] != meta["source_updated_at_utc"]:
        raise ValueError("auction source version timestamp does not match the manifest")
    if manifest["market_area"] not in payload["deliveryAreas"]:
        raise ValueError("auction response does not include the requested market area")

    zone = ZoneInfo(manifest["timezone"])
    delivery_date = date.fromisoformat(manifest["delivery_date_local"])
    points: list[ClearingPricePoint] = []
    for row in payload["multiAreaEntries"]:
        start = _parse_utc(row["deliveryStart"], "auction delivery start")
        end = _parse_utc(row["deliveryEnd"], "auction delivery end")
        if start.astimezone(zone).date() != delivery_date:
            continue
        if end - start != timedelta(minutes=15):
            raise ValueError("auction outcome contains a non-quarter-hour interval")
        values = row["entryPerArea"]
        if manifest["market_area"] not in values:
            continue
        points.append(
            ClearingPricePoint(
                area=manifest["market_area"],
                delivery_utc=start,
                price_eur_mwh=float(values[manifest["market_area"]]),
            )
        )

    expected = set(expected_delivery_starts_utc(delivery_date, manifest["timezone"]))
    observed = {point.delivery_utc for point in points}
    if len(points) != len(observed) or observed != expected:
        raise ValueError(
            "auction outcome must cover each expected UTC quarter-hour once"
        )
    prices = {point.delivery_utc: point.price_eur_mwh for point in points}
    return points, prices, _sha256(path)


def _schedule_csv_sha256(schedule: tuple[Any, ...], timezone_name: str) -> str:
    import io

    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "delivery_start_local",
            "issued_wind_100m_ms",
            "observed_previous_day_price_eur_per_mwh",
            "shadow_schedule_mw",
        ]
    )
    zone = ZoneInfo(timezone_name)
    for point in schedule:
        writer.writerow(
            [
                point.delivery_utc.astimezone(zone).isoformat(),
                point.wind_speed_100m_ms,
                point.prior_day_price_eur_mwh,
                point.scheduled_mw,
            ]
        )
    return hashlib.sha256(buffer.getvalue().encode("utf-8")).hexdigest()


def replay(
    *,
    manifest_path: Path,
    weather_snapshot: Path,
    price_input_csv: Path,
    price_source_response_json: Path,
    price_observation_receipt_json: Path,
    auction_outcome_json: Path,
    auction_observation_receipt_json: Path,
) -> dict[str, Any]:
    """Verify the frozen inputs and replay one local record without networking."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    gate = _parse_utc(manifest["gate"]["utc"], "gate")
    if gate.isoformat().replace("+00:00", "Z") != manifest["gate"]["utc"]:
        raise ValueError("gate must be recorded in canonical UTC form")
    if _parse_utc(manifest["gate"]["local"], "local gate") != gate:
        raise ValueError(
            "local and UTC gate timestamps do not identify the same instant"
        )
    timezone_name = manifest["timezone"]
    if timezone_name != "Europe/Copenhagen":
        raise ValueError("the DK2 replay requires the Europe/Copenhagen time zone")
    gate_local = datetime.fromisoformat(manifest["gate"]["local"])
    if (
        gate_local.astimezone(ZoneInfo(timezone_name)).isoformat()
        != manifest["gate"]["local"]
    ):
        raise ValueError("gate local time does not match the declared time zone")
    delivery_date = date.fromisoformat(manifest["delivery_date_local"])
    previous_day = delivery_date - timedelta(days=1)
    if gate_local.date() != previous_day or gate_local.time() != time(12):
        raise ValueError(
            "DK2 gate must be noon Copenhagen time on the previous local day"
        )

    weather_meta = manifest["inputs"]["weather"]
    price_meta = manifest["inputs"]["price_input"]
    schedule_observed = _parse_utc(
        manifest["recorded_output"]["schedule_observed_at_utc"],
        "schedule observation",
    )
    if schedule_observed > gate:
        raise ValueError("recorded proxy schedule was observed after the gate")
    weather_available_upper = _parse_utc(
        weather_meta["observed_upper_bound_utc"], "weather observation upper bound"
    )
    price_observed = _parse_utc(price_meta["observed_at_utc"], "price observation")
    if schedule_observed < weather_available_upper:
        raise ValueError(
            "schedule was recorded before the weather observation window ended"
        )
    if schedule_observed < price_observed:
        raise ValueError("schedule was recorded before the price input was observed")
    require_pre_gate_availability(
        gate,
        weather_issued_at_utc=_parse_utc(
            weather_meta["model_run_utc"], "weather model run"
        ),
        weather_observed_at_utc=weather_available_upper,
        price_source_updated_at_utc=_parse_utc(
            price_meta["source_updated_at_utc"], "price source update"
        ),
        price_observed_at_utc=_parse_utc(
            price_meta["observed_at_utc"], "price observation"
        ),
    )

    # Validate post-gate outcome provenance before reading its values.
    outcome_meta = manifest["inputs"]["auction_outcome"]
    outcome_observed = _parse_utc(
        outcome_meta["observed_at_utc"], "auction observation"
    )
    outcome_updated = _parse_utc(
        outcome_meta["source_updated_at_utc"], "auction source update"
    )
    if outcome_updated <= gate or outcome_observed <= gate:
        raise ValueError("auction outcomes must be timestamped after the decision gate")
    if outcome_observed < outcome_updated:
        raise ValueError("auction was observed before its source version was published")

    # Construct the policy output before loading any post-gate auction outcome.
    weather, weather_hash = _parse_weather(weather_snapshot, manifest)
    (
        price_forecasts,
        price_source_hash,
        price_observation_hash,
    ) = _parse_price_input(
        price_input_csv,
        price_source_response_json,
        price_observation_receipt_json,
        manifest,
    )
    delivery_starts = expected_delivery_starts_utc(delivery_date, timezone_name)
    price_by_target = {point.delivery_utc: point for point in price_forecasts}
    proxy = manifest["proxy"]
    if proxy["power_curve_ms"] != {"cut_in": 3.0, "rated": 12.0, "cut_out": 25.0}:
        raise ValueError("unsupported proxy power-curve configuration")
    schedule = build_proxy_schedule(
        delivery_starts,
        weather,
        price_by_target,
        capacity_mw=float(proxy["capacity_mw"]),
        wake_efficiency=float(proxy["wake_efficiency"]),
        availability=float(proxy["availability"]),
    )
    schedule_hash = _schedule_csv_sha256(schedule, manifest["timezone"])
    if schedule_hash != manifest["recorded_output"]["schedule_csv_sha256"]:
        raise ValueError(f"replayed schedule SHA-256 mismatch: {schedule_hash}")

    # Auction values are intentionally read only after the decision is frozen.
    auction, clearing_by_target, auction_hash = _parse_auction_outcomes(
        auction_outcome_json, auction_observation_receipt_json, manifest
    )
    price_score = score_price_forecasts(
        price_forecasts,
        auction,
        area=manifest["market_area"],
        delivery_date=delivery_date,
        timezone_name=manifest["timezone"],
    )
    mask_value = price_score.pop("common_delivery_starts_utc")
    if not isinstance(mask_value, list) or not all(
        isinstance(item, str) for item in mask_value
    ):
        raise ValueError("scored shared mask must be a list of UTC timestamp strings")
    mask = [item for item in mask_value if isinstance(item, str)]
    mask_hash = hashlib.sha256(("\n".join(mask) + "\n").encode("utf-8")).hexdigest()
    if {point.delivery_utc for point in schedule} != set(clearing_by_target):
        raise ValueError("proxy schedule and auction outcomes do not share a full mask")
    interval_hours = 0.25
    scheduled_mwh = sum(point.scheduled_mw * interval_hours for point in schedule)
    forecast_volume_mark = sum(
        point.scheduled_mw * interval_hours * clearing_by_target[point.delivery_utc]
        for point in schedule
    )

    return {
        "classification": manifest["classification"],
        "delivery_date_local": manifest["delivery_date_local"],
        "gate_utc": manifest["gate"]["utc"],
        "decision_inputs": {
            "weather_body_sha256": weather_hash,
            "price_input_csv_sha256": _sha256(price_input_csv),
            "price_source_response_sha256": price_source_hash,
            "price_observation_receipt_sha256": price_observation_hash,
            "schedule_csv_sha256": schedule_hash,
            "schedule_interval_count": len(schedule),
            "scheduled_forecast_volume_mwh": scheduled_mwh,
        },
        "price_only_backtest": price_score,
        "shared_mask": {
            "interval_count": len(mask),
            "utc_start_sha256": mask_hash,
        },
        "post_gate_counterfactual": {
            "auction_response_sha256": auction_hash,
            "auction_observation_receipt_sha256": _sha256(
                auction_observation_receipt_json
            ),
            "scheduled_forecast_volume_mark_eur": forecast_volume_mark,
            "interpretation": (
                "Forecast-volume mark at clearing prices; not an order, revenue, "
                "metered generation, or imbalance settlement."
            ),
        },
        "scope": [
            "one-day price-persistence score only",
            "educational proxy power schedule only",
            "no historical as-issued forecast reconstruction",
            "no fitted Phase 1-3 strategy score",
            "no actual asset, metered generation, or physical settlement",
            "not an independent scientific review or human UAT",
        ],
    }


def main() -> None:
    """Run the local replay and emit its compact JSON receipt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--weather-snapshot", type=Path, required=True)
    parser.add_argument("--price-input-csv", type=Path, required=True)
    parser.add_argument("--price-source-response-json", type=Path, required=True)
    parser.add_argument("--price-observation-receipt-json", type=Path, required=True)
    parser.add_argument("--auction-outcome-json", type=Path, required=True)
    parser.add_argument("--auction-observation-receipt-json", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = replay(
            manifest_path=args.manifest,
            weather_snapshot=args.weather_snapshot,
            price_input_csv=args.price_input_csv,
            price_source_response_json=args.price_source_response_json,
            price_observation_receipt_json=args.price_observation_receipt_json,
            auction_outcome_json=args.auction_outcome_json,
            auction_observation_receipt_json=args.auction_observation_receipt_json,
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
