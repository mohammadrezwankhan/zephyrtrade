"""Check that a committed scenario can be replayed by both engines."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests/fixtures/fictional-scenario-v1.json"


def replay(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 -- fixed interpreter and test script
        [
            sys.executable,
            str(ROOT / "scripts/verify_engines.py"),
            "--manifest",
            str(path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_replay_reports_both_engines() -> None:
    result = replay(MANIFEST)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["status"] == "PASS"
    assert output["browser"]["offer_mw"] == 7
    assert output["python"]["expected_revenue_dkk"] == 2540
    assert output["objective_difference_dkk"] < 1e-6


def test_replay_rejects_changed_recorded_revenue(tmp_path: Path) -> None:
    document = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    document["calculated"]["expected_revenue_dkk"] = 1
    altered = tmp_path / "altered.json"
    altered.write_text(json.dumps(document), encoding="utf-8")
    assert replay(altered).returncode != 0


def test_replay_rejects_nonoptimal_recorded_offer(tmp_path: Path) -> None:
    document = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    document["calculated"]["offer_mw"] = 0
    altered = tmp_path / "altered.json"
    altered.write_text(json.dumps(document), encoding="utf-8")
    assert replay(altered).returncode != 0


def test_replay_rejects_changed_recorded_quantile(tmp_path: Path) -> None:
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    document["calculated"]["critical_quantile"] = 0.5
    altered = tmp_path / "altered.json"
    altered.write_text(json.dumps(document), encoding="utf-8")
    assert replay(altered).returncode != 0


def test_replay_accepts_equal_objective_offer(tmp_path: Path) -> None:
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    document["input"]["da"] = 310
    document["calculated"] = {
        "offer_mw": 0,
        "expected_revenue_dkk": 2170,
        "critical_quantile": 0,
    }
    tied = tmp_path / "tied.json"
    tied.write_text(json.dumps(document), encoding="utf-8")
    result = replay(tied)
    assert result.returncode == 0, result.stderr
