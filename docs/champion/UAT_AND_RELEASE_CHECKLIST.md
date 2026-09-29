# Normal-browser acceptance and controlled-release checklist

**Status: NOT RUN by human participants.** This is a runnable acceptance script,
not evidence that a participant completed it. Use synthetic data and research-only
assumptions. Proposed participant roles: one wind/market researcher and one learner.
Name the actual participant, device, browser/version, candidate SHA and date on each
completed record. An owner must choose which devices are mandatory.

| Task | Starting state and action | Expected outcome | Record / sign-off |
|---|---|---|---|
| Portable launch | Extract ZIP to a normal folder; double-click HTML | Five-screen app appears; 3,888 full-window intervals; synthetic label visible; no terminal required | Pending |
| Offline check | Disconnect network, reopen same file | Backtest filters and scenario calculation work; no live-connection claim | Pending |
| Model / dates | Compare direct regression and persistence; choose 7 days; restore all | Values and charts change with the selection; all returns 3,888 rows | Pending |
| Invalid / empty window | Reverse dates, then use a range without observations | Meaningful validation or empty state, no invented zero-observation record | Pending |
| Numerical scenario | Capacity 30, DA400/up600/down200, scenarios2,8,20, weights.2,.5,.3, duration1 | Offer8 MW; expected revenue3200 DKK. Duration.25 changes revenue to800 DKK, not the offer | Pending |
| Dirty result | Edit DA without calculating; navigate away and back | Draft retained; last result marked stale; save/export prevented until recalculation | Pending |
| Persistence | Save a named scenario; close browser; reopen same file and profile | Scenario loads with the same assumptions and recalculated result | Pending — native storage not covered by harness |
| Backup / restore | Export scenario JSON, copy elsewhere, import into another browser instance | Assumptions match; output recomputed, never trusted from imported output fields | Pending |
| Storage failure | Deny local storage or use a quota-constrained test profile | No false saved state; JSON export offered as recovery | Pending |
| Downloads | Export all/model/date-filtered CSVs and provenance JSON | Files exist in Downloads; row counts and full-precision fields match; synthetic labels remain | Pending |
| Deletion | Try deleting saved scenario; first cancel, then confirm | Cancel preserves it; confirm removes only selected item | Pending |
| Windows launcher | Run START_PYTHON_WINDOWS.bat with Python3.11+ and package access | New isolated environment, local service, no changes to uploaded virtual environment | Pending |
| Real browser + API | Open server at127.0.0.1:8765; calculate scenario; cross-check | Browser says cross-check passed; objective agrees within1e-6 DKK | Pending — complete connection not covered by harness |
| Failed solver | Stop local server or reproduce a safe local service failure | Truthful unavailable/timed-out state; inputs retained; no false result | Pending |
| Keyboard / assistive tech | Navigate all controls and dialogs without mouse, then with chosen screen reader | Visible focus, usable order, accessible names, errors and modal behavior | Pending |
| Devices / zoom | Windows Chrome/Edge; chosen Firefox/Safari; actual phone; 200% text/zoom | Essential content remains readable and reachable; dense tables scroll locally | Pending |
| Light / dark / motion | Toggle theme; use reduced-motion preference | Readable controls and distinguishable charts; no essential motion dependence | Pending |
| Dependency / CI | Install declared dev environment; run original lint/format/tests/build plus JS tests | All required checks complete; no skipped failure accepted as green | Pending |
| Research warnings | Reproduce representative training and review convergence output | Supported choice of regularization/convergence criteria; no suppressed warnings | Pending |
| Recovery rehearsal | Export work, stop candidate service, install prior version in separate folder, reimport safe backup | Old/new artifact identity and stored assumptions verified; no source data removed | Pending |

## Participant feedback

Ask what was unclear about synthetic versus measured data, offer error versus forecast
error, the independence of lab and backtest, the benchmark and missing hours. Ask the
participant to explain how they would recover after a failed save. Record genuine
responses only; no invented quotations or simulated UAT completion.

## Gate record

Candidate ID / SHA: ______  Participant and approver: ______
Mandatory device matrix: ______  Date / evidence links: ______
Observed defects and severity: ______  Remaining blockers: ______
Decision: BLOCKED / approved for the named research-only next environment: ______
Scope of explicit approval: ______

Public hosting, real market access, external telemetry, customer communications and
real transactions are excluded. A technical pass does not authorize them.
