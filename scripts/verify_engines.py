"""Compare the real browser calculation module with SciPy on seeded assumptions."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import numpy as np
from zephyrtrade.app import optimize_payload

root = Path(__file__).resolve().parents[1]
rng = np.random.default_rng(42)
cases = []
for i in range(120):
    n = int(rng.integers(1, 30))
    capacity = float(rng.uniform(5, 100))
    down = float(rng.uniform(-300, 500))
    up = down + float(rng.uniform(1, 900))
    q = 0.0 if i % 10 == 0 else 1.0 if i % 10 == 1 else float(rng.random())
    probabilities = rng.dirichlet(np.ones(n))
    cases.append(dict(capacity=capacity, da=down+q*(up-down), up=up, down=down,
                      hours=float(rng.choice([.25, .5, 1, 2, 24])),
                      scenarios=rng.uniform(0, capacity, n).tolist(),
                      probabilities=probabilities.tolist()))
code = "const E=require('./src/zephyrtrade/web/engine.js');let x='';process.stdin.on('data',d=>x+=d);process.stdin.on('end',()=>console.log(JSON.stringify(JSON.parse(x).map(E.optimize))));"
run = subprocess.run(["node", "-e", code], input=json.dumps(cases), text=True,
                     capture_output=True, check=True, cwd=root, timeout=20)
browser = json.loads(run.stdout)
errors = []
for i, (case, actual) in enumerate(zip(cases, browser, strict=True)):
    expected = optimize_payload(case)
    error = abs(actual['expected'] - expected['expected_revenue_dkk'])
    assert error < 1e-6, (i, error)
    assert 0 <= actual['offer'] <= case['capacity']
    errors.append(error)
print(json.dumps({'status':'PASS','seed':42,'cases':len(cases),
                  'maximum_objective_difference_dkk':max(errors),
                  'comparison':'Browser module in Node vs actual SciPy LP; equal-objective offer ties permitted'},indent=2))
