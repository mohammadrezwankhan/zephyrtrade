"""Check source validation, causal-history prerequisites, and CLI receipts."""

from __future__ import annotations

import importlib
import json
import runpy
import sys
from dataclasses import replace
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from zephyrtrade import data_loader, phase2, phase3, pipeline, preprocessing
from zephyrtrade.data_loader import DataBundle, SyntheticDataConfig


@pytest.fixture
def source_bundle() -> DataBundle:
    return data_loader.generate_synthetic_data(
        SyntheticDataConfig(start="2024-01-01", end="2024-02-01", seed=63)
    )


@pytest.mark.parametrize(
    "start,end", [("2024-01-02", "2024-01-01"), ("2024-01-01", "2024-01-08")]
)
def test_synthetic_sources_require_forward_time_and_enough_history(
    start: str, end: str
) -> None:
    with pytest.raises(ValueError):
        data_loader.generate_synthetic_data(SyntheticDataConfig(start=start, end=end))


@pytest.mark.parametrize(
    "defect",
    [
        "wind_farm",
        "climate_farm",
        "duplicate",
        "missing",
        "negative_power",
        "excess_power",
        "negative_price",
        "humidity",
    ],
)
def test_source_bundle_rejects_physical_and_key_contract_violations(
    source_bundle: DataBundle,
    defect: str,
) -> None:
    wind = source_bundle.wind_power.copy()
    climate = source_bundle.climate.copy()
    prices = source_bundle.market_prices.copy()
    if defect == "wind_farm":
        wind = wind.loc[wind.farm_id != wind.farm_id.iloc[0]]
    elif defect == "climate_farm":
        climate = climate.loc[climate.farm_id != climate.farm_id.iloc[0]]
    elif defect == "duplicate":
        wind = pd.concat([wind, wind.iloc[[0]]], ignore_index=True)
    elif defect == "missing":
        climate.loc[0, "relative_humidity_pct"] = np.nan
    elif defect == "negative_power":
        wind.loc[0, "actual_power_mw"] = -0.01
    elif defect == "excess_power":
        wind.loc[0, "actual_power_mw"] = 1e6
    elif defect == "negative_price":
        prices.loc[0, data_loader.PRICE_COLUMNS[0]] = -1.0
    else:
        climate.loc[0, "relative_humidity_pct"] = 100.01
    with pytest.raises(ValueError):
        data_loader.validate_data_bundle(
            replace(
                source_bundle, wind_power=wind, climate=climate, market_prices=prices
            )
        )


def test_price_filter_requires_all_settlement_prices_and_counts_removed_rows() -> None:
    with pytest.raises(ValueError, match="missing"):
        data_loader.filter_negative_price_intervals(pd.DataFrame({"other": [1.0]}))
    prices = pd.DataFrame(
        {name: [10.0, 20.0, 30.0] for name in data_loader.PRICE_COLUMNS}
    )
    prices.loc[1, data_loader.PRICE_COLUMNS[2]] = -0.1
    retained, summary = data_loader.filter_negative_price_intervals(prices)
    assert len(retained) == 2
    assert summary == {
        "rows_before_filter": 3,
        "rows_after_filter": 2,
        "negative_price_rows_removed": 1,
        "negative_price_share_removed": 1 / 3,
    }


@pytest.mark.parametrize(
    "defect",
    ["unknown_farm", "missing_climate", "duplicate", "gap", "column", "too_short"],
)
def test_feature_history_rejects_ambiguous_or_incomplete_sources(
    source_bundle: DataBundle,
    defect: str,
) -> None:
    wind, climate = source_bundle.wind_power.copy(), source_bundle.climate.copy()
    config = preprocessing.PreprocessingConfig()
    if defect == "unknown_farm":
        config = replace(config, farm_id="missing-farm")
    elif defect == "missing_climate":
        climate = climate.loc[climate.farm_id != config.farm_id]
    elif defect == "duplicate":
        duplicate = wind.loc[wind.farm_id == config.farm_id].iloc[[0]]
        wind = pd.concat([wind, duplicate], ignore_index=True)
    elif defect == "gap":
        row = wind.index[wind.farm_id == config.farm_id][10]
        wind = wind.drop(index=row)
    elif defect == "column":
        climate = climate.drop(columns=["temperature_2m_c"])
    else:
        config = replace(config, weekly_window_hours=1000, weekly_min_periods=1000)
    with pytest.raises(ValueError):
        preprocessing.engineer_features(
            wind, climate, source_bundle.market_prices, config
        )


@pytest.mark.parametrize(
    "train,validation", [(0.0, 0.2), (0.9, 0.2), (np.nan, 0.2), (0.7, 0.15)]
)
def test_chronological_splits_reject_invalid_fractions_and_empty_periods(
    train: float, validation: float
) -> None:
    frame = pd.DataFrame({"timestamp_utc": pd.to_datetime(["2024-01-01"], utc=True)})
    with pytest.raises(ValueError):
        preprocessing.chronological_split(frame, train, validation)


def test_data_and_preprocessing_commands_write_usable_receipts(tmp_path: Path) -> None:
    raw, processed = tmp_path / "raw", tmp_path / "processed"
    assert (
        data_loader.main(
            ["--start", "2024-01-01", "--end", "2024-02-01", "--output-dir", str(raw)]
        )
        == 0
    )
    assert (
        preprocessing.main(["--raw-data-dir", str(raw), "--output-dir", str(processed)])
        == 0
    )
    schema = json.loads((processed / "feature_schema.json").read_text())
    assert schema["feature_columns"] == preprocessing.FEATURE_COLUMNS
    with pytest.raises(ValueError, match="probability"):
        data_loader.main(["--negative-price-probability", "1"])
    with pytest.raises(FileNotFoundError):
        preprocessing.load_raw_tables(tmp_path / "missing")
    (raw / "wind_power.csv.gz").unlink()
    pd.DataFrame({"wrong": [1]}).to_csv(raw / "wind_power.csv.gz", index=False)
    with pytest.raises(ValueError, match="timestamp"):
        preprocessing.load_raw_tables(raw)


def test_stage_commands_preserve_explicit_directories_and_model_options(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    phase2_configs: list[phase2.Phase2Config] = []
    phase3_configs: list[phase3.Phase3Config] = []

    def capture_phase2(config: phase2.Phase2Config) -> dict[str, Path]:
        phase2_configs.append(config)
        return {"receipt": tmp_path / "phase2.json"}

    def capture_phase3(config: phase3.Phase3Config) -> dict[str, Path]:
        phase3_configs.append(config)
        return {}

    monkeypatch.setattr(phase2, "run_phase2", capture_phase2)
    monkeypatch.setattr(phase3, "run_phase3", capture_phase3)
    assert (
        phase2.main(["--processed-data-dir", str(tmp_path), "--local-neighbors", "24"])
        == 0
    )
    assert phase2_configs[0].processed_data_dir == tmp_path
    assert phase2_configs[0].local_neighbors == 24
    assert (
        phase3.main(["--phase2-prediction-path", str(tmp_path / "predictions.csv")])
        == 0
    )
    assert phase3_configs[0].phase2_prediction_path == tmp_path / "predictions.csv"


@pytest.mark.parametrize(
    "name", ["app", "data_loader", "preprocessing", "phase2", "phase3", "pipeline"]
)
def test_public_module_entrypoint_help_is_available_without_running_models(
    name: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = importlib.import_module("zephyrtrade." + name)
    assert module.__file__ is not None
    monkeypatch.setattr(sys, "argv", ["zephyr-" + name, "--help"])
    with pytest.raises(SystemExit) as stopped:
        runpy.run_path(module.__file__, run_name="__main__")
    assert stopped.value.code == 0
    assert "usage:" in capsys.readouterr().out


def test_manifest_conversion_and_unavailable_dependency_are_truthful(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    def missing_one(package: str) -> str:
        if package == "numpy":
            raise PackageNotFoundError(package)
        return version(package)

    monkeypatch.setattr(pipeline, "version", missing_one)
    assert pipeline._dependency_versions()["numpy"] == "not-installed"
    assert pipeline._json_ready((Path("artifact.csv"),)) == ["artifact.csv"]
    with pytest.raises(ValueError, match="negative_price_probability"):
        pipeline.run_pipeline(pipeline.PipelineConfig(negative_price_probability=1.0))
    value = phase3._json_ready({"count": np.int64(3), "revenue": np.float64(7.5)})
    assert json.dumps(value, allow_nan=False) == '{"count": 3, "revenue": 7.5}'
