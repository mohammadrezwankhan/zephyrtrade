"""Compare the real browser calculation module with SciPy on seeded assumptions."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

from zephyrtrade.app import optimize_payload
from zephyrtrade.optimize import expected_scenario_revenue

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--manifest", type=Path, help="Replay a version-1 scenario JSON")
args = parser.parse_args()
rng = np.random.default_rng(42)
cases = []
for i in range(120):
    n = int(rng.integers(1, 30))
    capacity = float(rng.uniform(5, 100))
    down = float(rng.uniform(-300, 500))
    up = down + float(rng.uniform(1, 900))
    q = 0.0 if i % 10 == 0 else 1.0 if i % 10 == 1 else float(rng.random())
    probabilities = rng.dirichlet(np.ones(n))
    cases.append(
        {
            "capacity": capacity,
            "da": down + q * (up - down),
            "up": up,
            "down": down,
            "hours": float(rng.choice([0.25, 0.5, 1, 2, 24])),
            "scenarios": rng.uniform(0, capacity, n).tolist(),
            "probabilities": probabilities.tolist(),
        }
    )
recorded = None
recorded_offer = None
recorded_quantile = None
if args.manifest is not None:
    document = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ValueError("Expected a version-1 scenario document")
    if not isinstance(document.get("input"), dict):
        raise ValueError("Scenario document requires an input object")
    calculated = document.get("calculated")
    if not isinstance(calculated, dict):
        raise ValueError("Scenario document requires recorded calculation")
    recorded = calculated.get("expected_revenue_dkk")
    if (
        isinstance(recorded, bool)
        or not isinstance(recorded, (int, float))
        or not math.isfinite(recorded)
    ):
        raise ValueError("Recorded revenue must be a finite number")
    recorded_offer = calculated.get("offer_mw")
    if (
        isinstance(recorded_offer, bool)
        or not isinstance(recorded_offer, (int, float))
        or not math.isfinite(recorded_offer)
    ):
        raise ValueError("Recorded offer must be a finite number")
    recorded_quantile = calculated.get("critical_quantile")
    if (
        isinstance(recorded_quantile, bool)
        or not isinstance(recorded_quantile, (int, float))
        or not math.isfinite(recorded_quantile)
    ):
        raise ValueError("Recorded quantile must be a finite number")
    cases = [document["input"]]

code = (
    "const E=require('./src/zephyrtrade/web/engine.js');let"
    " x='';process.stdin.on('data',d=>x+=d);process.stdin.on('end"
    "',()=>console.log(JSON.stringify(JSON.parse(x).map(E.optimiz"
    "e))));"
)
node = shutil.which("node")
if node is None:
    raise RuntimeError("Node.js is required for the browser engine comparison.")
node = str(Path(node).resolve(strict=True))
run = subprocess.run(  # noqa: S603 -- resolved Node, fixed code, generated JSON stdin
    [node, "-e", code],
    input=json.dumps(cases),
    text=True,
    capture_output=True,
    check=True,
    cwd=root,
    timeout=20,
)
browser = json.loads(run.stdout)
errors = []
for i, (case, actual) in enumerate(zip(cases, browser, strict=True)):
    expected = optimize_payload(case)
    error = abs(actual["expected"] - expected["expected_revenue_dkk"])
    if not (error < 1e-6):
        raise AssertionError((i, error))
    if not (0 <= actual["offer"] <= case["capacity"]):
        raise AssertionError
    errors.append(error)
if recorded is not None:
    actual = browser[0]
    if recorded_quantile is None or abs(recorded_quantile - actual["quantile"]) >= 1e-9:
        raise AssertionError("Recorded quantile differs from recalculated quantile")
    expected = optimize_payload(cases[0])
    case = cases[0]
    if recorded_offer is None or not 0 <= recorded_offer <= case["capacity"]:
        raise ValueError("Recorded offer is outside capacity")
    case_probabilities = case.get("probabilities") or [
        1 / len(case["scenarios"])
    ] * len(case["scenarios"])
    case_probabilities = np.asarray(case_probabilities, dtype=float)
    case_probabilities = case_probabilities / case_probabilities.sum()
    recorded_offer_revenue = expected_scenario_revenue(
        recorded_offer,
        case["scenarios"],
        case_probabilities,
        case["da"],
        case["up"],
        case["down"],
    ) * case.get("hours", 1)
    if abs(recorded_offer_revenue - expected["expected_revenue_dkk"]) >= 1e-6:
        raise AssertionError("Recorded offer does not achieve the optimum")
    if abs(recorded - expected["expected_revenue_dkk"]) >= 1e-6:
        raise AssertionError("Recorded revenue differs from recalculated revenue")
    sys.stdout.write(
        json.dumps(
            {
                "status": "PASS",
                "browser": {
                    "offer_mw": actual["offer"],
                    "expected_revenue_dkk": actual["expected"],
                },
                "python": {
                    "offer_mw": expected["offer_mw"],
                    "expected_revenue_dkk": expected["expected_revenue_dkk"],
                },
                "objective_difference_dkk": errors[0],
                "tolerance_dkk": 1e-6,
            },
            indent=2,
        )
        + "\n"
    )
    sys.exit(0)

sys.stdout.write(
    str(
        json.dumps(
            {
                "status": "PASS",
                "seed": 42,
                "cases": len(cases),
                "maximum_objective_difference_dkk": max(errors),
                "comparison": (
                    "Browser module in Node vs actual SciPy LP; equal-objective"
                    " offer ties permitted"
                ),
            },
            indent=2,
        )
    )
    + "\n"
)
