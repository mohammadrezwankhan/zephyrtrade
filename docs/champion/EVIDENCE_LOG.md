# Evidence log — ZephyrTrade Champion 1.1.0

All execution took place in the isolated Linux environment described in
AUDIT_AND_RELEASE.md. Evidence IDs below are stable artifact names. These are
sequential implementation and self-review records, not independent agent findings.
Absolute command paths identify this run; use your extracted project directory when
reproducing checks. The recorded time is the command-completion record time.

## Final decisive evidence

| Evidence ID | Content and limit |
|---|---|
| E01 / baseline-tests.log | Original 20-test pass, before changes. |
| E02 / regression-baseline-refined.log | 17 failing and 3 passing new tests against original source. |
| E03 / python-final-tests.log | Final 86 Python tests, warnings as errors; includes real loopback API tests. |
| E04 / javascript-final-tests.log | 13 final JavaScript calculation cases. |
| E05 / parity-final.log | 120 seeded browser-engine versus SciPy objectives; maximum absolute difference about 1.16e-10 DKK. |
| E06 / snapshot-verification.json | 3,888 retained observations; 34,992 revenue comparisons; maximum difference about 3.64e-12 DKK. |
| E07 / browser-checks.json and browser-final.log | 23 real DOM/UI harness checks; 25 page/viewport combinations; Storage double, no native browser navigation. |
| E08 / screenshots/ | Six final actual implemented-screen captures, not conceptual artwork. |
| E09 / source-preservation.json | 65 protected source files preserved byte for byte; original README separately preserved. |
| E10 / wheel-final-build.log | Final wheel built with existing setuptools backend. |
| E11 / wheel-final-install-smoke.log | Exact 16-file wheel/source parity and isolated target install, health, assets and actual SciPy HTTP solve. Shared scientific dependencies, not clean resolution. |
| E12 / reduced-training-smoke.log | Completed bounded new training with a smaller Phase 3 grid; four Lasso warnings retained. |

## Failed, blocked and intermediate evidence

All available attempts are retained, including initial flawed test fixtures,
pre-repair failures, the reproduced mobile-theme defect, native-navigation policy
failures, package-network failures and both interrupted research-pipeline attempts.
The full-grid pipeline has no success claim. See BASELINE_RESULTS.csv and
commands.jsonl for exact commands, outcomes and log filenames. Missing durations or
exit codes on interrupted attempts are left unknown, not inferred.

Ruff, the declared hosted CI matrix, native file/localhost browser navigation,
native durable persistence, a complete browser-to-Python session, physical devices,
assistive-technology review and human UAT remain blocked or pending. The complete
scope is in AUDIT_AND_RELEASE.md and UAT_AND_RELEASE_CHECKLIST.md.

## Reproduction tools

The original project tests and scripts are included. `evidence/tools/` preserves the
execution wrapper and wheel-install check used here; these include this run's local
paths and need adaptation outside the recorded workspace. Build the web snapshot
with scripts/build_app.py. Do not overwrite archived research artifacts during a
new training run. Examples in the repository examples/ directory are illustrative user assumptions,
not acquired market data. Imported scenarios are recalculated by the real engine.

No production logs, customer records, private credentials, live order activity,
public rollout statistics, human interviews or external telemetry were available.
