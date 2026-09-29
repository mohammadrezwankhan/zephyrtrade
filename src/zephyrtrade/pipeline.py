"""Run the complete ZephyrTrade research pipeline with one command."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from zephyrtrade import __version__
from zephyrtrade.data_loader import (
    SyntheticDataConfig,
    generate_synthetic_data,
    write_data_bundle,
)
from zephyrtrade.phase2 import Phase2Config, run_phase2
from zephyrtrade.phase3 import Phase3Config, run_phase3
from zephyrtrade.preprocessing import (
    DEFAULT_FARM_ID,
    PreprocessingConfig,
    prepare_dataset,
)

TRACKED_DEPENDENCIES = (
    "joblib",
    "matplotlib",
    "numpy",
    "pandas",
    "scikit-learn",
    "scipy",
)


@dataclass(frozen=True)
class PipelineConfig:
    """Configure the complete deterministic data-to-decision workflow."""

    start: str = "2022-01-01"
    end: str = "2025-01-01"
    seed: int = 42
    negative_price_probability: float = 0.012
    farm_id: str = DEFAULT_FARM_ID
    raw_data_dir: Path = Path("data/raw")
    processed_data_dir: Path = Path("data/processed")
    artifact_dir: Path = Path("artifacts")
    figure_dir: Path = Path("docs/figures")


def file_sha256(path: Path, chunk_size: int = 1 << 20) -> str:
    """Return a file's hexadecimal SHA-256 digest without loading it at once."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Cannot hash missing file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _dependency_versions() -> dict[str, str]:
    """Capture installed versions for the numerical runtime manifest."""
    versions: dict[str, str] = {}
    for package in TRACKED_DEPENDENCIES:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def _json_ready(value: Any) -> Any:
    """Recursively convert paths and tuples to JSON-compatible values."""
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def run_pipeline(config: PipelineConfig) -> dict[str, Path]:
    """Generate data, fit both model families, and write a run manifest."""
    if not 0.0 <= config.negative_price_probability < 1.0:
        raise ValueError("negative_price_probability must lie in [0, 1).")

    synthetic_config = SyntheticDataConfig(
        start=config.start,
        end=config.end,
        seed=config.seed,
        negative_price_probability=config.negative_price_probability,
        output_dir=config.raw_data_dir,
    )
    bundle = generate_synthetic_data(synthetic_config)
    raw_paths = write_data_bundle(bundle, synthetic_config)

    processed_paths = prepare_dataset(
        PreprocessingConfig(
            raw_data_dir=config.raw_data_dir,
            output_dir=config.processed_data_dir,
            farm_id=config.farm_id,
        )
    )
    phase2_paths = run_phase2(
        Phase2Config(
            processed_data_dir=config.processed_data_dir,
            output_dir=config.artifact_dir / "phase2",
            figure_dir=config.figure_dir,
            random_state=config.seed,
        )
    )
    phase3_paths = run_phase3(
        Phase3Config(
            processed_data_dir=config.processed_data_dir,
            phase2_prediction_path=phase2_paths["test_predictions"],
            output_dir=config.artifact_dir / "phase3",
            figure_dir=config.figure_dir,
            random_state=config.seed,
        )
    )

    manifest_path = config.artifact_dir / "run_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    reproducibility_files = {
        "raw_provenance": raw_paths["provenance"],
        "feature_schema": processed_paths["schema"],
        "phase2_summary": phase2_paths["summary"],
        "phase3_summary": phase3_paths["summary"],
    }
    manifest = {
        "project": "ZephyrTrade",
        "pipeline_version": __version__,
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "configuration": asdict(config),
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "dependencies": _dependency_versions(),
        },
        "row_counts": {
            "wind_power": len(bundle.wind_power),
            "climate": len(bundle.climate),
            "retained_market_prices": len(bundle.market_prices),
        },
        "sha256": {
            name: file_sha256(path) for name, path in reproducibility_files.items()
        },
        "outputs": {
            "raw": raw_paths,
            "processed": processed_paths,
            "phase2": phase2_paths,
            "phase3": phase3_paths,
        },
    }
    manifest_path.write_text(
        json.dumps(_json_ready(manifest), indent=2),
        encoding="utf-8",
    )
    print(f"Complete ZephyrTrade pipeline finished. Manifest: {manifest_path}")
    return {"manifest": manifest_path}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the full pipeline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2022-01-01")
    parser.add_argument("--end", default="2025-01-01")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--negative-price-probability",
        type=float,
        default=0.012,
    )
    parser.add_argument("--farm-id", default=DEFAULT_FARM_ID)
    parser.add_argument("--raw-data-dir", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--processed-data-dir",
        type=Path,
        default=Path("data/processed"),
    )
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--figure-dir", type=Path, default=Path("docs/figures"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the complete pipeline from the command line."""
    args = _parse_args(argv)
    run_pipeline(
        PipelineConfig(
            start=args.start,
            end=args.end,
            seed=args.seed,
            negative_price_probability=args.negative_price_probability,
            farm_id=args.farm_id,
            raw_data_dir=args.raw_data_dir,
            processed_data_dir=args.processed_data_dir,
            artifact_dir=args.artifact_dir,
            figure_dir=args.figure_dir,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
