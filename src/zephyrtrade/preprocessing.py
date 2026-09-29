"""Engineer leakage-safe wind features and chronological model splits."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

DEFAULT_FARM_ID = "bornholm_ronne_coastal"
TARGET_COLUMN = "actual_power_mw"
PRICE_COLUMNS = [
    "day_ahead_price_dkk_mwh",
    "up_reg_price_dkk_mwh",
    "down_reg_price_dkk_mwh",
]
FEATURE_COLUMNS = [
    "actual_power_lag_24h_mw",
    "weekly_power_q05_mw",
    "weekly_power_q50_mw",
    "weekly_power_q95_mw",
    "wind_speed_100m_ms",
    "wind_gust_100m_ms",
    "temperature_2m_c",
    "surface_pressure_hpa",
    "relative_humidity_pct",
    "wind_direction_sin",
    "wind_direction_cos",
    "hour_sin",
    "hour_cos",
    "day_of_year_sin",
    "day_of_year_cos",
]

FEATURE_DEFINITIONS = {
    "actual_power_lag_24h_mw": "Actual production at exactly t minus 24 hours.",
    "weekly_power_q05_mw": "5th percentile of production from t-168h through t-1h.",
    "weekly_power_q50_mw": "Median production from t-168h through t-1h.",
    "weekly_power_q95_mw": "95th percentile of production from t-168h through t-1h.",
    "wind_speed_100m_ms": "Forecast-time 100 m wind-speed proxy.",
    "wind_gust_100m_ms": "Forecast-time 100 m gust proxy.",
    "temperature_2m_c": "Forecast-time air-temperature proxy at 2 m.",
    "surface_pressure_hpa": "Forecast-time surface-pressure proxy.",
    "relative_humidity_pct": "Forecast-time relative-humidity proxy.",
    "wind_direction_sin": "Sine encoding of 100 m wind direction.",
    "wind_direction_cos": "Cosine encoding of 100 m wind direction.",
    "hour_sin": "Sine encoding of local hour in Europe/Copenhagen.",
    "hour_cos": "Cosine encoding of local hour in Europe/Copenhagen.",
    "day_of_year_sin": "Sine encoding of local day of year.",
    "day_of_year_cos": "Cosine encoding of local day of year.",
}


@dataclass(frozen=True)
class PreprocessingConfig:
    """Configure feature construction, chronological splitting, and persistence."""

    raw_data_dir: Path = Path("data/raw")
    output_dir: Path = Path("data/processed")
    farm_id: str = DEFAULT_FARM_ID
    train_fraction: float = 0.70
    validation_fraction: float = 0.15
    timezone_name: str = "Europe/Copenhagen"
    weekly_window_hours: int = 168
    weekly_min_periods: int = 72


def _read_csv_utc(path: Path) -> pd.DataFrame:
    """Read a source table and parse its UTC timestamp column."""
    if not path.exists():
        raise FileNotFoundError(f"Required source table not found: {path}")
    frame = pd.read_csv(path)
    if "timestamp_utc" not in frame.columns:
        raise ValueError(f"timestamp_utc is missing from {path}")
    frame["timestamp_utc"] = pd.to_datetime(
        frame["timestamp_utc"],
        utc=True,
        errors="raise",
    )
    return frame


def load_raw_tables(
    raw_data_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the wind, climate, and nonnegative-price source tables."""
    raw_data_dir = Path(raw_data_dir)
    wind_power = _read_csv_utc(raw_data_dir / "wind_power.csv.gz")
    climate = _read_csv_utc(raw_data_dir / "climate.csv.gz")
    market_prices = _read_csv_utc(raw_data_dir / "market_prices.csv.gz")
    if (market_prices.loc[:, PRICE_COLUMNS] < 0.0).any().any():
        raise ValueError("The market source table still contains negative prices.")
    return wind_power, climate, market_prices


def _validate_selected_farm(
    wind_power: pd.DataFrame,
    climate: pd.DataFrame,
    farm_id: str,
) -> None:
    """Ensure the requested farm has unique, aligned source observations."""
    if farm_id not in set(wind_power["farm_id"]):
        available = sorted(wind_power["farm_id"].unique())
        raise ValueError(f"Unknown farm_id {farm_id!r}; choose from {available}.")
    if farm_id not in set(climate["farm_id"]):
        raise ValueError(f"Climate data are missing for farm {farm_id!r}.")
    for name, frame in (("wind_power", wind_power), ("climate", climate)):
        selected = frame.loc[frame["farm_id"] == farm_id]
        if selected["timestamp_utc"].duplicated().any():
            raise ValueError(f"Duplicate timestamps found in {name} for {farm_id}.")


def engineer_features(
    wind_power: pd.DataFrame,
    climate: pd.DataFrame,
    market_prices: pd.DataFrame,
    config: PreprocessingConfig,
) -> pd.DataFrame:
    """Build a point-in-time-correct feature matrix for one selected wind farm."""
    _validate_selected_farm(wind_power, climate, config.farm_id)
    farm_power = (
        wind_power.loc[wind_power["farm_id"] == config.farm_id]
        .sort_values("timestamp_utc")
        .copy()
    )
    farm_climate = (
        climate.loc[climate["farm_id"] == config.farm_id]
        .sort_values("timestamp_utc")
        .copy()
    )

    power_indexed = farm_power.set_index("timestamp_utc")
    complete_index = pd.date_range(
        power_indexed.index.min(),
        power_indexed.index.max(),
        freq="h",
        tz="UTC",
    )
    if not power_indexed.index.equals(complete_index):
        raise ValueError(
            "Wind-power history must be a complete hourly UTC series before "
            "market-price filtering."
        )

    power = power_indexed[TARGET_COLUMN]
    trailing_history = power.shift(1).rolling(
        window=config.weekly_window_hours,
        min_periods=config.weekly_min_periods,
    )
    history_features = pd.DataFrame(
        {
            "timestamp_utc": power.index,
            "actual_power_lag_24h_mw": power.shift(24).to_numpy(),
            "weekly_power_q05_mw": trailing_history.quantile(0.05).to_numpy(),
            "weekly_power_q50_mw": trailing_history.quantile(0.50).to_numpy(),
            "weekly_power_q95_mw": trailing_history.quantile(0.95).to_numpy(),
        }
    )

    model_frame = (
        farm_power.merge(history_features, on="timestamp_utc", validate="one_to_one")
        .merge(
            farm_climate,
            on=["timestamp_utc", "farm_id"],
            validate="one_to_one",
        )
        .merge(market_prices, on="timestamp_utc", validate="many_to_one")
        .sort_values("timestamp_utc")
        .reset_index(drop=True)
    )

    direction_radians = np.deg2rad(model_frame["wind_direction_100m_deg"])
    model_frame["wind_direction_sin"] = np.sin(direction_radians)
    model_frame["wind_direction_cos"] = np.cos(direction_radians)

    local_time = model_frame["timestamp_utc"].dt.tz_convert(config.timezone_name)
    local_hour = local_time.dt.hour + local_time.dt.minute / 60.0
    day_of_year = local_time.dt.dayofyear
    model_frame["hour_sin"] = np.sin(2.0 * np.pi * local_hour / 24.0)
    model_frame["hour_cos"] = np.cos(2.0 * np.pi * local_hour / 24.0)
    model_frame["day_of_year_sin"] = np.sin(2.0 * np.pi * (day_of_year - 1.0) / 365.25)
    model_frame["day_of_year_cos"] = np.cos(2.0 * np.pi * (day_of_year - 1.0) / 365.25)

    required = ["timestamp_utc", "farm_id", TARGET_COLUMN, *FEATURE_COLUMNS]
    missing = set(required).difference(model_frame.columns)
    if missing:
        raise ValueError(f"Engineered columns are missing: {sorted(missing)}")
    model_frame = model_frame.dropna(subset=[TARGET_COLUMN, *FEATURE_COLUMNS])
    if model_frame.empty:
        raise ValueError("No complete feature rows remain after history construction.")
    return model_frame.reset_index(drop=True)


def chronological_split(
    model_frame: pd.DataFrame,
    train_fraction: float,
    validation_fraction: float,
) -> dict[str, pd.DataFrame]:
    """Split observations in timestamp order without random shuffling."""
    test_fraction = 1.0 - train_fraction - validation_fraction
    if min(train_fraction, validation_fraction, test_fraction) <= 0.0:
        raise ValueError("Train, validation, and test fractions must all be positive.")
    if not np.isclose(train_fraction + validation_fraction + test_fraction, 1.0):
        raise ValueError("Split fractions must sum to one.")

    ordered = model_frame.sort_values("timestamp_utc").reset_index(drop=True)
    row_count = len(ordered)
    train_end = int(np.floor(row_count * train_fraction))
    validation_end = train_end + int(np.floor(row_count * validation_fraction))
    if train_end < 1 or validation_end <= train_end or validation_end >= row_count:
        raise ValueError("The dataset is too small for the requested split fractions.")

    splits = {
        "train": ordered.iloc[:train_end].copy(),
        "validation": ordered.iloc[train_end:validation_end].copy(),
        "test": ordered.iloc[validation_end:].copy(),
    }
    if not (
        splits["train"]["timestamp_utc"].max()
        < splits["validation"]["timestamp_utc"].min()
        < splits["test"]["timestamp_utc"].min()
    ):
        raise ValueError("Chronological split boundaries overlap.")
    return splits


def scale_feature_splits(
    splits: dict[str, pd.DataFrame],
) -> tuple[dict[str, pd.DataFrame], StandardScaler]:
    """Fit z-score scaling on training features and transform all three splits."""
    scaler = StandardScaler()
    scaler.fit(splits["train"].loc[:, FEATURE_COLUMNS])
    scaled: dict[str, pd.DataFrame] = {}
    for split_name, split_frame in splits.items():
        transformed = split_frame.copy()
        transformed.loc[:, FEATURE_COLUMNS] = scaler.transform(
            split_frame.loc[:, FEATURE_COLUMNS]
        )
        scaled[split_name] = transformed
    return scaled, scaler


def _split_metadata(
    splits: dict[str, pd.DataFrame],
) -> dict[str, dict[str, Any]]:
    """Summarize split sizes and boundaries for the feature manifest."""
    return {
        name: {
            "rows": len(frame),
            "start_utc": frame["timestamp_utc"].min().isoformat(),
            "end_utc": frame["timestamp_utc"].max().isoformat(),
        }
        for name, frame in splits.items()
    }


def prepare_dataset(config: PreprocessingConfig) -> dict[str, Path]:
    """Run the complete Phase 1 preprocessing pipeline and persist its artifacts."""
    wind_power, climate, market_prices = load_raw_tables(config.raw_data_dir)
    features = engineer_features(wind_power, climate, market_prices, config)
    splits = chronological_split(
        features,
        train_fraction=config.train_fraction,
        validation_fraction=config.validation_fraction,
    )
    scaled_splits, scaler = scale_feature_splits(splits)

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "features": output_dir / "features_unscaled.csv.gz",
        "train": output_dir / "train_scaled.csv.gz",
        "validation": output_dir / "validation_scaled.csv.gz",
        "test": output_dir / "test_scaled.csv.gz",
        "scaler": output_dir / "standard_scaler.joblib",
        "schema": output_dir / "feature_schema.json",
    }
    features.to_csv(
        paths["features"],
        index=False,
        compression="gzip",
        date_format="%Y-%m-%dT%H:%M:%SZ",
    )
    for split_name, split_frame in scaled_splits.items():
        split_frame.to_csv(
            paths[split_name],
            index=False,
            compression="gzip",
            date_format="%Y-%m-%dT%H:%M:%SZ",
        )
    joblib.dump(scaler, paths["scaler"])

    schema = {
        "farm_id": config.farm_id,
        "target_column": TARGET_COLUMN,
        "feature_columns": FEATURE_COLUMNS,
        "feature_definitions": FEATURE_DEFINITIONS,
        "retained_evaluation_columns": PRICE_COLUMNS,
        "scaling": {
            "method": "training-only standard score",
            "with_mean": scaler.with_mean,
            "with_std": scaler.with_std,
            "training_feature_means": dict(
                zip(FEATURE_COLUMNS, scaler.mean_, strict=True)
            ),
            "training_feature_scales": dict(
                zip(FEATURE_COLUMNS, scaler.scale_, strict=True)
            ),
        },
        "split_policy": {
            "method": "strict chronological allocation without shuffling",
            "train_fraction": config.train_fraction,
            "validation_fraction": config.validation_fraction,
            "test_fraction": 1.0 - config.train_fraction - config.validation_fraction,
            "splits": _split_metadata(splits),
        },
        "history_policy": {
            "lag_hours": 24,
            "weekly_window_hours": config.weekly_window_hours,
            "weekly_min_periods": config.weekly_min_periods,
            "current_target_excluded_from_rolling_statistics": True,
        },
    }
    paths["schema"].write_text(json.dumps(schema, indent=2), encoding="utf-8")
    return paths


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the preprocessing pipeline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-data-dir",
        type=Path,
        default=Path("data/raw"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed"),
    )
    parser.add_argument("--farm-id", default=DEFAULT_FARM_ID)
    parser.add_argument("--train-fraction", type=float, default=0.70)
    parser.add_argument("--validation-fraction", type=float, default=0.15)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run feature engineering from the command line."""
    args = _parse_args(argv)
    config = PreprocessingConfig(
        raw_data_dir=args.raw_data_dir,
        output_dir=args.output_dir,
        farm_id=args.farm_id,
        train_fraction=args.train_fraction,
        validation_fraction=args.validation_fraction,
    )
    paths = prepare_dataset(config)
    print(f"Prepared chronological features for {config.farm_id}.")
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
