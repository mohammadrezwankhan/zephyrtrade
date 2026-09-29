# ZephyrTrade Champion — audit, verification and release handoff

**Candidate:** 1.1.0, local research only. **Prepared:** 28 September 2026.
**Overall unrestricted-release gate: BLOCKED.** A usable local research candidate
has been implemented and packaged. It is not a production deployment, a live-market
integration or a claim of completed human acceptance testing.

## 1. Executive diagnosis and scope

The upload is a Python research repository, not an existing graphical application.
It generates synthetic wind/weather/price tables, constructs chronological features,
trains indirect and direct offer-learning models, evaluates offers and writes reports.
No existing interactive UI, broker adapter, accounts, shared database, authenticated
service, production URL, feedback dataset or operational telemetry was supplied.
Their absence is a scope/evidence limitation, not proof of a production outage.

The original 20 tests passed in the available environment. Additional regression
checks exposed numerical boundary errors not covered by those tests: zero-benchmark
capture could divide by zero; a single-row R² raised a warning; invalid durations,
probabilities and capacities could pass important boundaries; near-unity class
probability rows could select the lowest class at decision quantile 1. These were
repaired before the new interface was built. Core revenue equations, ordinary valid
inputs, chronological splitting and the supplied prediction artifacts were preserved.

The new interface uses the existing research domain rather than replacing it with a
stock/crypto trading dashboard. It presents one evaluated synthetic wind site,
backtest filters, a separate assumption sandbox, model comparison and a data ledger.
It never executes orders. A small optional loopback-only Python service cross-checks
the same scenario objective with the actual SciPy linear program.

Work was performed sequentially across audit, engineering, design and verification
roles. There were no independently executed agents or independent human reviewers.
The review is self-review. No remote push, production deployment, paid service,
customer communication or public release was performed.

## 2. Reproducible baseline and source identity

Input archive: `ZephyrTrade.zip`.
SHA-256: `59ea37ed94e6c2ba7bb298cfc19605e46844910d39b94f5f04c71c59d4592a0c`.
The Windows-style archive paths were normalized in a separate local workspace.
The original archive was not changed. Uploaded virtual environments, IDE caches,
Python caches and incomplete Git metadata were excluded from the deliverable.
There was no trustworthy source commit history to identify. The candidate uses a
content manifest rather than inventing a commit ID or clean-branch history.

The working source is an isolated copy, not a reset or overwrite of the upload.
`CANDIDATE_MANIFEST.json` identifies the final implementation. `CHANGED_FILES.csv`
records compared files; `source-changes.patch` contains textual source differences.
The original README is preserved byte-for-byte as `README_RESEARCH.md`.
All 65 protected data/artifact/research-figure files matched their starting hashes; see `evidence/source-preservation.json`. Original data, artifacts and research figures are retained; read the current report
rather than interpreting historical README/test claims as this candidate's results.

### Verification environment

Linux; Python 3.13.5; NumPy 2.3.5; pandas 2.2.3; SciPy 1.17.0;
scikit-learn 1.8.0; Matplotlib 3.10.8; Node 22.16.0;
Chromium 144.0.7559.96. Exact observed versions are also recorded in the evidence.
Tests used preinstalled pytest 9.0.2. The original development requirement is pytest
8.x; installation of the declared development environment was blocked by package
network access. This was not an exact reproduction of the declared CI matrix.
The original runtime dependency ranges were not broadly upgraded.

Checks used `PYTHONPATH=<candidate>/src`, `MPLBACKEND=Agg`,
`OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1`. `BASELINE_RESULTS.csv` and
`evidence/commands.jsonl` preserve exact commands, working directories, timestamps,
exit codes and durations where captured. Timestamps in the wrapper are completion
record times. Interrupted commands have no fabricated exit status or duration.

### Attempt history that matters

The original suite passed 20 tests. The first added regression suite failed 20 cases;
three failures were over-specific error-message expectations for inputs already
rejected by the baseline. Those expectations were corrected, without relaxing the
required rejection. The refined baseline produced **17 failed / 3 passed**. The
same refined tests then passed after the repairs.

An initial HTTP integration test used the wrong handwritten expected shortfall cost
(6 MW × 600 DKK/MWh is 3600, not 1200). The implementation and independent JavaScript
calculation were correct; the test expectation was corrected. Both attempts remain
in the evidence. An early browser fixture embedded a literal closing script tag in
test storage and reused a JavaScript global context. The harness, not the app's
escaped saved-name rendering, was corrected. A real new-UI defect—mobile CSS hiding
the new theme button—was then reproduced and fixed. None of these failed attempts
was removed from the log.

## 3. Actual architecture and preservation inventory

| Layer / journey | Implementation and state | Preservation / limitation |
|---|---|---|
| Synthetic data | `data_loader.py`, `data/raw/` | Existing generation and supplied tables retained; no live feeds |
| Features / splits | `preprocessing.py`, `data/processed/` | Existing chronological split and scaling contracts retained |
| Indirect research | `models.py`, `phase2.py`, `optimize.py` | Seven existing model/baseline strategies retained |
| Direct research | `direct.py`, `phase3.py` | Continuous and bracket-based offers retained; boundary validation repaired |
| Market evaluation | `evaluate.py` | Revenue formula retained; undefined metric contract made explicit |
| Portable app | `web/index.html`, `styles.css`, `engine.js`, `app.js` | New real UI, no frontend dependency or external CDN |
| Snapshot compiler | `scripts/build_app.py` | Reads CSV/JSON only; validates alignment, numeric values, capacity, prices and source revenues |
| Scenario solver | Browser engine, optional `app.py` | Browser quantile; real SciPy LP at loopback `/api/optimize`; no order execution |
| Scenario storage | Browser localStorage plus JSON import/export | Save failures visible; explicit backup workflow; native persistence still needs normal-browser acceptance |
| CLI / build | Original CLI commands plus `zephyr-app` | Existing commands retained; wheel includes all five web assets |

The browser snapshot contains 3,888 retained hourly rows for a 30 MW Ronne Coastal
Proxy, nine strategies and exact source hashes. The inclusive interval from its
first to last timestamp contains 3,941 hours, so 53 observations are absent. The
source generation log removed 319 negative-price rows across the entire original
period; that is a different population from the 53 missing test-window hours.

The browser recomputes selected-period revenue and offer error from unrounded
observations. Daily production/price charts show means of included hours;
cumulative-revenue charts use sums of included records. Missing intervals are not
filled with zero. The scenario lab is independent of dashboard date/model filters.
It uses editable assumptions and is not a new forecast from a trained estimator.

### Scientific limits that remain visible

The data and weather inputs are synthetic. Forecast-time availability, day-ahead gate
closure for lag features, current market rules, operational settlement, transaction
costs and out-of-sample live profitability were not independently validated. No claim
of proven operational information availability is made. This is not a finding that
all models leak information; it is an unresolved operational-validity question.

Perfect foresight knows actual production. Under the source's price ordering it is
a useful analytical benchmark, not a deployable prediction. The app's capture values
are synthetic benchmark ratios, not investment returns. It labels offer RMSE/MAE
separately from wind-forecast accuracy.

## 4. Focused repairs and traceability

The canonical details, severity rationale, origin, evidence and remaining actions
are in `ISSUE_REGISTER.csv`. Priorities below are for this local research scope;
production incidence and affected-user counts are unknown.

| Issue | Supported mechanism and repair | Verification |
|---|---|---|
| ZT-01 | Zero/nonpositive oracle denominator: return undefined capture, not division by zero or a fabricated percent | Python regression, browser engine null-metric test |
| ZT-02 | Nonfinite/invalid duration and offer inputs: reject at numerical boundaries | Parameterized regression tests |
| ZT-03 | R² for one interval: return `None`; retain valid MAE/RMSE | Warning-as-error regression |
| ZT-04 | Negative scenario weights / invalid price ordering: validate instead of producing a misleading objective | Expected-revenue tests, API tests |
| ZT-05 | Accepted near-one probability rows could have a cumulative endpoint below 1; `argmax(False...)` returned index 0 | Normalize accepted rows, force final CDF endpoint to 1; regression at quantile 1 |
| ZT-06 | Invalid class IDs and encoder capacity could enter bracket transformations | Unique/nonnegative IDs and finite capacity/bracket validation; regression tests |
| ZT-07 | No graphical workflow in the source | Product addition, not a pre-existing defect: five connected screens and portable build |
| ZT-08 | Edited lab fields could leave apparently current results / lose draft values on navigation | Dirty-result notice, save/export guard, in-memory draft retention; browser checks |
| ZT-09 | Mobile rule hid theme/help controls | Responsive toolbar repair; 320–1440 px browser checks |
| ZT-10 | New compiler needed strict validation of both source tables and consistent site metadata | Nonfinite direct-revenue, capacity, price, time and metadata rejection tests |
| ZT-11 | Malformed optional solver payload could otherwise pass a NaN comparison in UI | Pure finite/bounds/objective-response validator and JavaScript regression |

Explicit contract changes: `revenue_capture_pct` may be `None` for a nonpositive
benchmark; single-observation `r2` is `None`. Consumers must not coerce undefined
values to a meaningful zero. No database schema or data migration was introduced.
Source artifact rows were not rewritten to hide a discrepancy or improve a score.

## 5. Integrated evidence and test status

| Check | Result | Evidence / coverage |
|---|---|---|
| Original baseline | PASS — 20 tests | `baseline-tests.log` |
| Refined new tests on original source | Expected failures — 17 fail / 3 pass | `regression-baseline-refined.log` |
| Final Python suite | PASS — 86 tests, warnings as errors | `python-final-tests.log`; real local HTTP plus original and new regressions |
| JavaScript numerical suite | PASS — 13 cases | `javascript-final-tests.log` |
| Browser engine versus SciPy | PASS — 120 seeded assumption cases | `parity-final.log`; max objective difference 1.1641532182693481e-10 DKK |
| Supplied snapshot integrity | PASS — 34,992 saved revenues checked | `snapshot-final-build.log`; max discrepancy 3.637978807091713e-12 DKK |
| Browser UI harness | PASS — 23 grouped checks | `browser-final.log`, `browser-checks.json`; 25 page/viewport combinations |
| Python and JS syntax; shell syntax | PASS in available runtime | `python-compile.log`, `javascript-syntax.log`, `shell-launcher-syntax.log` |
| Wheel backend build and installed-package check | PASS — all 16 Python/web files match final source; health, five assets and actual SciPy HTTP solve | `wheel-final-build.log`, `wheel-final-install-smoke.log`; existing scientific dependencies reused; missing `python -m build` frontend did not run |
| Fresh bounded training smoke | Completed, with four Lasso convergence warnings | `reduced-training-smoke.log`; normal Phase 2, smaller 10-iteration Phase 3 grid |
| Default full-grid research pipeline | INCONCLUSIVE / interrupted at tool limit | Two retained attempts; latest 120-second limit; no completion manifest |
| Direct file / localhost browser navigation | BLOCKED by administrator browser policy | `browser-first-pass.log`, `hosted-smoke.log` |
| Ruff lint and format; original hosted CI matrix | BLOCKED / not completed | Package unavailable; `ruff-unavailable.log`; original checks remain enabled |
| Native storage, real devices, assistive technology, human UAT | NOT RUN / pending | Normal-browser acceptance script below |

### What the browser evidence actually establishes

The shipped HTML was rendered in Chromium using `set_content`. The real interface,
DOM, calculations, event handlers, validation, downloads' Blob payloads, responsive
layouts, dialog behavior and reduced-motion CSS were exercised. Five actual browser
download events were observed. The harness uses an **explicit in-memory Storage
double** to exercise save, hydrate, load, delete and quota-failure logic.

It does not prove durable browser storage across native restarts, direct local-file
opening or the complete browser-to-server connection. Those paths were blocked by
this environment's browser navigation policy. The real HTTP service was separately
exercised by Python clients; Node exercised the same shipped calculation module
against SciPy. Separate passing layers are not misrepresented as a complete E2E pass.

The screenshots are of the implemented app at recorded synthetic states, not mockups.
There is no fabricated “before UI” screenshot because the original source had no UI.
Screenshots were inspected on desktop and mobile. Physical device support, Firefox,
Safari and Windows execution were not independently tested.

### Performance and accessibility

The browser harness records one `set_content` load duration per run; that is not a
cold network-load benchmark or a speedup claim. No comparable original UI exists.
Memory retention, production latency and crash-free-session metrics are unavailable.
Performance thresholds remain proposed/TBD pending a representative environment.
The app avoids external frontend bundles, aggregates dense charts and paginates data;
those are design choices, not proof of universal performance improvement.

Proposed accessibility target: WCAG 2.2 AA. Implemented features include semantic
navigation, labelled controls, keyboard-visible focus, a skip link, native dialog
focus/Escape handling, live error/status feedback, dash patterns in multi-series
charts and reduced-motion handling. Selected DOM/control and dialog checks passed.
No comprehensive automated accessibility scanner, screen reader, contrast audit or
full conformance assessment was completed. Human review remains necessary.

### Failure-mode coverage

Invalid input, empty filters, negative/zero probability handling, source mismatch,
quarter-hour units, malformed JSON, oversize API requests, stale edited outputs,
scenario import recovery and explicit storage failure were exercised. HTTP tests
check host/origin restrictions, arbitrary-path rejection and a busy solver response.
The optional Python request has a bounded client timeout and does not silently retry.
No transaction, queue, session-refresh or tenant workflow exists in this product;
those tests are not applicable to the local research scope, not waived live-system checks.

## 6. Security, privacy and data integrity

The optional server binds only to 127.0.0.1, uses a fixed static-asset allowlist,
validates Host and Origin, grants no CORS, limits JSON bodies to 32 KB and scenario
counts to 100, rejects nonfinite/duplicate-key JSON, bounds HTTP workers and permits
one solver at a time. It sends defensive headers and avoids logging scenario bodies.
Input strings shown in the UI are escaped; CSV text cells are formula-neutralized.
These finite checks are not a security certification or production hardening claim.

No accounts, credentials, live customer records, cookies or broker API keys were
required. No external telemetry was added. The portable app contacts no remote fonts,
CDNs or analytics. The local service is not an internet-hosting architecture; the
Python HTTP documentation explicitly cautions against production use.

The original `standard_scaler.joblib` files are retained as source artifacts but were
**not deserialized**. Snapshot building reads CSV/JSON. New training smoke runs fitted
fresh estimators from synthetic tables, rather than loading uploaded pickle objects.
No database migration, external side effect or real financial transaction took place.

Runtime dependency vulnerability scanning was not completed because registry access
was unavailable. No claim of vulnerability-free dependencies is made. The current
source has no supplied telemetry/support-review dataset; all incident rates, crash
rates and user-impact frequencies remain unknown. No review quotations were invented.

## 7. Design package

**Audience assumption:** research analysts and learners evaluating this repository's
wind-offering experiments, not licensed live operators. Stakeholder validation of
that audience remains pending. The selected direction is a dense but legible energy
research terminal: navy surfaces, restrained mint/cyan/gold semantic emphasis,
system typography, original wind diagrams, shared spacing/border tokens and light
and dark themes. No expensive 3D engine or decorative frontend dependency was added.

Before: run commands, open several CSV/report files and manually reconcile strategy
outputs. After: select a strategy/window, inspect a common chart and numerical ledger,
compare all models, then separately challenge assumptions in the scenario lab.
The workflow removes manual lookup steps, but no measured human task-time improvement
is claimed. The sandbox does not silently inherit backtest filters. Provenance and
synthetic labels remain visible rather than hidden behind cosmetic panels.

All five screens are connected to real local data or calculation behavior. Loading
and unavailable-service states apply to the optional Python request; empty results
apply to ledger/date filters and saved scenarios; validation and failure states retain
inputs. Destructive scenario deletion asks for confirmation. User assumptions are
never presented as measured market observations.

New icons, diagrams, CSS and UI code are original under the retained project MIT
licence. Existing research figures remain supplied artifacts. No font binaries,
proprietary brand assets or third-party JavaScript libraries were distributed.

## 8. Release and recovery preparation

**Current disposition:** local research candidate for owner evaluation. All broad
release gates remain blocked where they require normal-browser E2E, declared CI,
human UAT or operational evidence. No production platform or rollout owner was supplied.
No rollout has begun.

| Phase | Gate assessment |
|---|---|
| Audit / first repair readiness | PASS for the identified bounded numerical repairs; baseline and hypotheses recorded |
| Stabilisation | Targeted Python repairs PASS in the stated runtime; whole-product sign-off BLOCKED by integration/tooling gaps |
| Modernisation | Implemented and UI-harness checks PASS; formal gate BLOCKED pending full accessibility/performance/normal-browser evidence |
| Validation | Component/API tests PASS; unrestricted next-environment gate BLOCKED |
| Release preparation | Package prepared; release-entry, promotion and full-release gates BLOCKED / no authorization |

### Proposed staged exposure, not execution

Retain the supplied strategy **1% → 10% → 50% → 100%** only after pre-release acceptance.
For a local-file product, the closest proposed mechanism is controlled invitations
and versioned download cohorts, not HTTP traffic splitting. Exact platform support,
eligible population, stable cohort definition and installation/update delivery remain
unresolved. No exact percentages or cohort tracking are claimed to be configured.

Before any first cohort, an owner must approve the candidate hash, mandatory checks,
support channel, withdrawal instructions and intended audience. Before each promotion,
record both an agreed observation interval and a sufficient sample of genuine task
outcomes; both are TBD based on expected usage and risk. Zero reports from a small or
unobserved cohort is not evidence of reliability. Halt promotion for incorrect
settlement calculations, data provenance mismatch, loss of saved work, undisclosed
live connectivity or any new material security defect. These are proposed stop
conditions, not an accepted service-level agreement.

### Monitoring specification and ownership

No production monitoring was enabled. Proposed signals are successful essential-task
completion, failed solver requests, source-validation failures, save/import errors
and user-reported defects. A future owner must define denominators, time windows,
candidate/cohort labels, privacy rules and escalation. Named people, accepted duty
rotas, alert delivery and telemetry baselines are not supplied. Missing mandatory
telemetry blocks promotion. No future monitoring by this chat is promised.

### Recovery and rollback

There is no database migration to reverse. Retain the original uploaded archive and
this candidate's hash manifest. Roll back app code by restoring a separate previous
folder or wheel; do not overwrite a user's source working tree. Scenario storage is
origin/file-location dependent: export JSON before changing the application location,
port or version. Keep exported files outside a folder scheduled for removal.

The local server stops with Ctrl+C. Deactivate and remove only its dedicated virtual
environment when no longer needed; do not remove the original source data. Withdraw
an incorrectly distributed HTML by notifying its recipients through an authorized
owner; a downloaded/offline copy cannot be remotely recalled. No automated kill switch,
remote update channel, backup service or database restore was invented.

Browser-harness scenario export/import was exercised, but native persistent-storage
restore and installed-client rollback require normal-device rehearsal. The original
source archive is retained; that alone is not a tested production recovery procedure.

### Required next human decision

Run `UAT_AND_RELEASE_CHECKLIST.md` on a normal Windows browser, confirm portable-file
operation and native save/reopen behavior, and separately verify the Python launcher
and its cross-check. Complete the declared CI/tooling checks, assess the retained
training warnings and approve the intended **research-only** distribution scope.
Any public hosting, market-data integration or actual trading requires a separate
architecture, validation and authorization decision.

## 9. Evidence index and authoritative references

`EVIDENCE_LOG.md`, `BASELINE_RESULTS.csv`, `ISSUE_REGISTER.csv`,
`CHANGED_FILES.csv`, `CANDIDATE_MANIFEST.json`, `source-changes.patch` and the
`evidence/` directory provide the handoff. Relative artifact paths are authoritative;
absolute command paths document the original verification environment and should be
adapted to the extracted project when reproducing a check.

Official references consulted for implementation constraints (not a claim that an
external integration was tested):

- Python HTTP server documentation: https://docs.python.org/3/library/http.server.html
- NumPy quantile definition and methods: https://numpy.org/doc/stable/reference/generated/numpy.quantile.html
- scikit-learn R² behavior: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.r2_score.html
- W3C WCAG 2.2: https://www.w3.org/TR/WCAG22/
- Ruff 0.12.12 official release, consulted during an unsuccessful tool-download attempt: https://github.com/astral-sh/ruff/releases/tag/0.12.12

The operational sequence and evidence/gate terminology derive from the supplied
`broken app repairFull.docx` brief. Unknowns have not been filled with customer,
telemetry, human-test or production-deployment claims.
