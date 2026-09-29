"""The compiled observation snapshot must reject misleading source artifacts."""
import runpy
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
make_snapshot = runpy.run_path(str(ROOT / "scripts/build_app.py"))["make_snapshot"]


@pytest.fixture
def source(tmp_path):
    for relative in ["artifacts/phase2/test_predictions.csv.gz",
                     "artifacts/phase3/test_direct_predictions.csv.gz",
                     "data/raw/provenance.json", "data/raw/farm_metadata.csv"]:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    return tmp_path


def test_snapshot_reconciles_all_models():
    snap = make_snapshot(ROOT)
    assert snap["quality"]["revenue_values_checked"] == 34992
    assert len(snap["models"]) == 9
    assert snap["quality"]["maximum_revenue_error_dkk"] < 1e-7


@pytest.mark.parametrize("defect", ["nan_saved_direct_revenue", "varying_capacity",
                                   "bad_price_order", "duplicate_time", "wrong_metadata"])
def test_snapshot_refuses_invalid_or_mislabelled_sources(source, defect):
    paths = [source / "artifacts/phase2/test_predictions.csv.gz",
             source / "artifacts/phase3/test_direct_predictions.csv.gz"]
    frames = [pd.read_csv(p) for p in paths]
    if defect == "nan_saved_direct_revenue":
        frames[1].loc[0, "direct_regression_revenue_dkk"] = np.nan
    elif defect == "wrong_metadata":
        metadata = pd.read_csv(source / "data/raw/farm_metadata.csv")
        metadata.loc[0, "capacity_mw"] = 31
        metadata.to_csv(source / "data/raw/farm_metadata.csv", index=False)
    else:
        for frame in frames:
            if defect == "varying_capacity":
                frame.loc[0, "capacity_mw"] = 31
            elif defect == "bad_price_order":
                frame.loc[0, "up_reg_price_dkk_mwh"] = -100
            elif defect == "duplicate_time":
                frame.loc[0, "timestamp_utc"] = frame.loc[1, "timestamp_utc"]
    for path, frame in zip(paths, frames, strict=True):
        frame.to_csv(path, index=False)
    with pytest.raises(ValueError):
        make_snapshot(source)
