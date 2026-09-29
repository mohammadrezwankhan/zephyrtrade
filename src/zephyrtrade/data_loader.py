"""Create and validate source-aligned synthetic Bornholm wind-market data."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PRICE_COLUMNS = (
    "day_ahead_price_dkk_mwh",
    "up_reg_price_dkk_mwh",
    "down_reg_price_dkk_mwh",
)

PUBLIC_SOURCE_REFERENCES = {
    "energinet_api": "https://api.energidataservice.dk/index.html",
    "energinet_historical_spot": (
        "https://www.energidataservice.dk/tso-electricity/Elspotprices"
    ),
    "energinet_imbalance_price": (
        "https://www.energidataservice.dk/tso-electricity/ImbalancePrice"
    ),
    "entso_e_transparency": "https://transparency.entsoe.eu/",
    "open_meteo_archive": ("https://open-meteo.com/en/docs/historical-weather-api"),
}


@dataclass(frozen=True)
class FarmSpec:
    """Describe one synthetic wind-farm site proxy."""

    farm_id: str
    display_name: str
    latitude: float
    longitude: float
    capacity_mw: float
    wind_multiplier: float
    wake_efficiency: float


FARM_SPECS = (
    FarmSpec(
        "bornholm_ronne_coastal",
        "Ronne Coastal Proxy",
        55.100,
        14.706,
        30.0,
        1.05,
        0.94,
    ),
    FarmSpec(
        "bornholm_hasle_ridge",
        "Hasle Ridge Proxy",
        55.184,
        14.706,
        24.0,
        1.02,
        0.92,
    ),
    FarmSpec(
        "bornholm_nexo_east",
        "Nexo East Proxy",
        55.060,
        15.130,
        36.0,
        1.08,
        0.95,
    ),
    FarmSpec(
        "bornholm_aakirkeby_inland",
        "Aakirkeby Inland Proxy",
        55.070,
        14.920,
        18.0,
        0.95,
        0.90,
    ),
)


@dataclass(frozen=True)
class SyntheticDataConfig:
    """Configure a deterministic source-data generation run."""

    start: str = "2022-01-01"
    end: str = "2025-01-01"
    timezone_name: str = "Europe/Copenhagen"
    seed: int = 42
    negative_price_probability: float = 0.012
    output_dir: Path = Path("data/raw")


@dataclass(frozen=True)
class DataBundle:
    """Hold validated Phase 1 source tables and price-filter statistics."""

    farm_metadata: pd.DataFrame
    wind_power: pd.DataFrame
    climate: pd.DataFrame
    market_prices: pd.DataFrame
    price_filter_summary: dict[str, float | int]


def _ar1_noise(
    rng: np.random.Generator,
    length: int,
    persistence: float,
    innovation_scale: float,
) -> np.ndarray:
    """Generate a stationary-looking autoregressive noise sequence."""
    values = np.zeros(length, dtype=float)
    innovations = rng.normal(0.0, innovation_scale, length)
    for index in range(1, length):
        values[index] = persistence * values[index - 1] + innovations[index]
    return values


def _build_timestamps(config: SyntheticDataConfig) -> pd.DatetimeIndex:
    """Return an exclusive-end hourly UTC index generated in Danish local time."""
    start = pd.Timestamp(config.start)
    end = pd.Timestamp(config.end)
    if end <= start:
        raise ValueError("The end timestamp must be later than the start timestamp.")

    timestamps = pd.date_range(
        start=start,
        end=end,
        freq="h",
        inclusive="left",
        tz=config.timezone_name,
    )
    if len(timestamps) < 24 * 8:
        raise ValueError("Generate at least eight days of hourly observations.")
    return timestamps.tz_convert("UTC")


def _generate_weather_drivers(
    timestamps: pd.DatetimeIndex,
    rng: np.random.Generator,
    timezone_name: str,
) -> dict[str, np.ndarray]:
    """Generate correlated regional weather drivers for Bornholm."""
    local_time = timestamps.tz_convert(timezone_name)
    day_of_year = np.asarray(local_time.dayofyear, dtype=float)
    hour = np.asarray(local_time.hour, dtype=float)
    length = len(timestamps)

    seasonal_wind = 8.4 + 2.1 * np.cos(2.0 * np.pi * (day_of_year - 12.0) / 365.25)
    synoptic_wind = _ar1_noise(rng, length, 0.965, 0.52)
    common_wind = np.clip(seasonal_wind + synoptic_wind, 0.5, 29.0)

    seasonal_temperature = 8.5 + 8.2 * np.sin(
        2.0 * np.pi * (day_of_year - 172.0) / 365.25
    )
    diurnal_temperature = 1.7 * np.sin(2.0 * np.pi * (hour - 14.0) / 24.0)
    temperature = (
        seasonal_temperature + diurnal_temperature + _ar1_noise(rng, length, 0.91, 0.48)
    )

    pressure = (
        1013.0
        + _ar1_noise(rng, length, 0.985, 0.95)
        - 0.7 * (common_wind - np.mean(common_wind))
    )
    humidity = np.clip(
        77.0 - 0.9 * (temperature - 8.5) + _ar1_noise(rng, length, 0.88, 1.8),
        35.0,
        100.0,
    )
    direction = np.mod(
        245.0 + np.cumsum(rng.normal(0.0, 7.5, length)),
        360.0,
    )
    return {
        "common_wind": common_wind,
        "temperature": temperature,
        "pressure": pressure,
        "humidity": humidity,
        "direction": direction,
    }


def _power_curve_fraction(wind_speed_ms: np.ndarray) -> np.ndarray:
    """Map hub-height wind speed to a generic normalized turbine power curve."""
    cut_in = 3.0
    rated = 12.0
    cut_out = 25.0
    fraction = np.zeros_like(wind_speed_ms, dtype=float)

    ramp_mask = (wind_speed_ms >= cut_in) & (wind_speed_ms < rated)
    fraction[ramp_mask] = (wind_speed_ms[ramp_mask] ** 3 - cut_in**3) / (
        rated**3 - cut_in**3
    )
    fraction[(wind_speed_ms >= rated) & (wind_speed_ms <= cut_out)] = 1.0
    return fraction


def _generate_farm_tables(
    timestamps: pd.DatetimeIndex,
    drivers: dict[str, np.ndarray],
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Create farm metadata, weather observations, and wind-power observations."""
    metadata_rows: list[dict[str, Any]] = []
    climate_frames: list[pd.DataFrame] = []
    wind_frames: list[pd.DataFrame] = []
    length = len(timestamps)

    for farm_index, farm in enumerate(FARM_SPECS):
        site_rng = np.random.default_rng(rng.integers(0, np.iinfo(np.int32).max))
        wind_speed = np.clip(
            drivers["common_wind"] * farm.wind_multiplier
            + _ar1_noise(site_rng, length, 0.72, 0.33),
            0.0,
            32.0,
        )
        wind_gust = np.clip(
            wind_speed * (1.16 + site_rng.normal(0.0, 0.025, length))
            + site_rng.gamma(1.5, 0.25, length),
            wind_speed,
            40.0,
        )
        wind_direction = np.mod(
            drivers["direction"] + farm_index * 4.0 + site_rng.normal(0.0, 5.0, length),
            360.0,
        )
        temperature = drivers["temperature"] + site_rng.normal(0.0, 0.35, length)
        pressure = drivers["pressure"] + site_rng.normal(0.0, 0.45, length)
        humidity = np.clip(
            drivers["humidity"] + site_rng.normal(0.0, 1.6, length),
            30.0,
            100.0,
        )

        availability = np.ones(length, dtype=float)
        derated = site_rng.random(length) < 0.009
        availability[derated] = site_rng.uniform(0.35, 0.88, derated.sum())
        power_fraction = _power_curve_fraction(wind_speed)
        measurement_noise = site_rng.normal(0.0, 0.012, length)
        actual_power = farm.capacity_mw * np.clip(
            power_fraction * farm.wake_efficiency * availability + measurement_noise,
            0.0,
            1.0,
        )

        metadata_rows.append(
            {
                "farm_id": farm.farm_id,
                "display_name": farm.display_name,
                "latitude": farm.latitude,
                "longitude": farm.longitude,
                "capacity_mw": farm.capacity_mw,
                "site_type": "synthetic_proxy",
            }
        )
        climate_frames.append(
            pd.DataFrame(
                {
                    "timestamp_utc": timestamps,
                    "farm_id": farm.farm_id,
                    "wind_speed_100m_ms": wind_speed,
                    "wind_gust_100m_ms": wind_gust,
                    "wind_direction_100m_deg": wind_direction,
                    "temperature_2m_c": temperature,
                    "surface_pressure_hpa": pressure,
                    "relative_humidity_pct": humidity,
                }
            )
        )
        wind_frames.append(
            pd.DataFrame(
                {
                    "timestamp_utc": timestamps,
                    "farm_id": farm.farm_id,
                    "actual_power_mw": actual_power,
                    "capacity_mw": farm.capacity_mw,
                    "availability_fraction": availability,
                }
            )
        )

    return (
        pd.DataFrame(metadata_rows),
        pd.concat(climate_frames, ignore_index=True),
        pd.concat(wind_frames, ignore_index=True),
    )


def _generate_market_prices(
    timestamps: pd.DatetimeIndex,
    drivers: dict[str, np.ndarray],
    mean_site_wind: np.ndarray,
    rng: np.random.Generator,
    config: SyntheticDataConfig,
) -> pd.DataFrame:
    """Generate source-aligned hourly DK2 day-ahead and balancing prices."""
    local_time = timestamps.tz_convert(config.timezone_name)
    hour = np.asarray(local_time.hour, dtype=float)
    day_of_year = np.asarray(local_time.dayofyear, dtype=float)
    length = len(timestamps)

    morning_peak = np.exp(-0.5 * ((hour - 8.0) / 2.2) ** 2)
    evening_peak = np.exp(-0.5 * ((hour - 18.5) / 2.8) ** 2)
    winter_premium = 0.5 + 0.5 * np.cos(2.0 * np.pi * (day_of_year - 8.0) / 365.25)
    cold_load = np.maximum(7.0 - drivers["temperature"], 0.0)
    price_noise = _ar1_noise(rng, length, 0.82, 22.0)

    day_ahead = (
        430.0
        + 95.0 * morning_peak
        + 145.0 * evening_peak
        + 80.0 * winter_premium
        + 9.0 * cold_load
        - 20.0 * mean_site_wind
        + price_noise
    )
    spike_mask = rng.random(length) < 0.004
    day_ahead[spike_mask] += rng.gamma(2.2, 330.0, spike_mask.sum())

    wind_change = np.diff(mean_site_wind, prepend=mean_site_wind[0])
    up_regulation = (
        day_ahead
        + 72.0
        + 25.0 * np.maximum(-wind_change, 0.0)
        + np.abs(rng.normal(0.0, 34.0, length))
    )
    down_regulation = (
        day_ahead
        - 48.0
        - 19.0 * np.maximum(wind_change, 0.0)
        - np.abs(rng.normal(0.0, 28.0, length))
    )

    negative_event = rng.random(length) < config.negative_price_probability
    day_ahead[negative_event] = -rng.uniform(5.0, 260.0, negative_event.sum())
    down_regulation[negative_event] = day_ahead[negative_event] - rng.uniform(
        5.0,
        80.0,
        negative_event.sum(),
    )

    return pd.DataFrame(
        {
            "timestamp_utc": timestamps,
            "market_area": "DK2",
            "day_ahead_price_dkk_mwh": day_ahead,
            "up_reg_price_dkk_mwh": up_regulation,
            "down_reg_price_dkk_mwh": down_regulation,
        }
    )


def filter_negative_price_intervals(
    market_prices: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    """Remove intervals with any negative market price and summarize the filter."""
    missing = set(PRICE_COLUMNS).difference(market_prices.columns)
    if missing:
        raise ValueError(f"Market-price columns are missing: {sorted(missing)}")

    keep_mask = market_prices.loc[:, PRICE_COLUMNS].ge(0.0).all(axis=1)
    filtered = market_prices.loc[keep_mask].reset_index(drop=True)
    total_rows = int(len(market_prices))
    removed_rows = int((~keep_mask).sum())
    summary: dict[str, float | int] = {
        "rows_before_filter": total_rows,
        "rows_after_filter": int(len(filtered)),
        "negative_price_rows_removed": removed_rows,
        "negative_price_share_removed": removed_rows / total_rows,
    }
    return filtered, summary


def validate_data_bundle(bundle: DataBundle) -> None:
    """Raise a descriptive error if a generated source table violates its contract."""
    expected_farms = {farm.farm_id for farm in FARM_SPECS}
    observed_farms = set(bundle.wind_power["farm_id"].unique())
    if observed_farms != expected_farms:
        raise ValueError("Wind data must contain every configured farm exactly once.")
    if set(bundle.climate["farm_id"].unique()) != expected_farms:
        raise ValueError("Climate data must contain every configured farm.")

    for frame_name, frame, key in (
        ("wind_power", bundle.wind_power, ["timestamp_utc", "farm_id"]),
        ("climate", bundle.climate, ["timestamp_utc", "farm_id"]),
        ("market_prices", bundle.market_prices, ["timestamp_utc"]),
    ):
        if frame.duplicated(key).any():
            raise ValueError(f"Duplicate keys found in {frame_name}.")
        if frame.isna().any().any():
            raise ValueError(f"Missing values found in {frame_name}.")

    if (bundle.wind_power["actual_power_mw"] < 0.0).any():
        raise ValueError("Wind production cannot be negative.")
    if (
        bundle.wind_power["actual_power_mw"] > bundle.wind_power["capacity_mw"] + 1e-9
    ).any():
        raise ValueError("Wind production cannot exceed nameplate capacity.")
    if (bundle.market_prices.loc[:, PRICE_COLUMNS] < 0.0).any().any():
        raise ValueError("Negative prices remain after filtering.")
    if not bundle.climate["relative_humidity_pct"].between(0.0, 100.0).all():
        raise ValueError("Relative humidity must remain between 0 and 100 percent.")


def generate_synthetic_data(config: SyntheticDataConfig) -> DataBundle:
    """Generate, filter, validate, and return a deterministic Phase 1 data bundle."""
    timestamps = _build_timestamps(config)
    rng = np.random.default_rng(config.seed)
    drivers = _generate_weather_drivers(timestamps, rng, config.timezone_name)
    farm_metadata, climate, wind_power = _generate_farm_tables(
        timestamps,
        drivers,
        rng,
    )
    mean_site_wind = (
        climate.groupby("timestamp_utc", sort=True)["wind_speed_100m_ms"]
        .mean()
        .to_numpy()
    )
    market_prices = _generate_market_prices(
        timestamps,
        drivers,
        mean_site_wind,
        rng,
        config,
    )
    market_prices, filter_summary = filter_negative_price_intervals(market_prices)
    bundle = DataBundle(
        farm_metadata=farm_metadata,
        wind_power=wind_power,
        climate=climate,
        market_prices=market_prices,
        price_filter_summary=filter_summary,
    )
    validate_data_bundle(bundle)
    return bundle


def _config_for_json(config: SyntheticDataConfig) -> dict[str, Any]:
    """Return a JSON-serializable configuration dictionary."""
    values = asdict(config)
    values["output_dir"] = str(config.output_dir)
    return values


def write_data_bundle(
    bundle: DataBundle,
    config: SyntheticDataConfig,
) -> dict[str, Path]:
    """Write source tables and a provenance manifest to the configured directory."""
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "farm_metadata": output_dir / "farm_metadata.csv",
        "wind_power": output_dir / "wind_power.csv.gz",
        "climate": output_dir / "climate.csv.gz",
        "market_prices": output_dir / "market_prices.csv.gz",
        "provenance": output_dir / "provenance.json",
    }
    bundle.farm_metadata.to_csv(paths["farm_metadata"], index=False)
    for name, frame in (
        ("wind_power", bundle.wind_power),
        ("climate", bundle.climate),
        ("market_prices", bundle.market_prices),
    ):
        frame.to_csv(
            paths[name],
            index=False,
            compression="gzip",
            date_format="%Y-%m-%dT%H:%M:%SZ",
        )

    manifest = {
        "project": "ZephyrTrade",
        "data_kind": "synthetic_source_aligned",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "configuration": _config_for_json(config),
        "public_source_references": PUBLIC_SOURCE_REFERENCES,
        "price_filter": bundle.price_filter_summary,
        "row_counts": {
            "farm_metadata": len(bundle.farm_metadata),
            "wind_power": len(bundle.wind_power),
            "climate": len(bundle.climate),
            "market_prices": len(bundle.market_prices),
        },
        "disclaimer": (
            "Farm names, capacities, observations, and prices are synthetic and "
            "must not be interpreted as measurements from commercial assets."
        ),
    }
    paths["provenance"].write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    return paths


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for source-data generation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2022-01-01")
    parser.add_argument("--end", default="2025-01-01")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--negative-price-probability",
        type=float,
        default=0.012,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/raw"),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Generate Phase 1 source data and print a concise completion summary."""
    args = _parse_args(argv)
    if not 0.0 <= args.negative_price_probability < 1.0:
        raise ValueError("Negative-price probability must be in [0, 1).")
    config = SyntheticDataConfig(
        start=args.start,
        end=args.end,
        seed=args.seed,
        negative_price_probability=args.negative_price_probability,
        output_dir=args.output_dir,
    )
    bundle = generate_synthetic_data(config)
    paths = write_data_bundle(bundle, config)
    print(
        "Generated four-farm source data; removed "
        f"{bundle.price_filter_summary['negative_price_rows_removed']} "
        "negative-price intervals."
    )
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
