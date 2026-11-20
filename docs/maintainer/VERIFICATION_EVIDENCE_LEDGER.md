# Verification evidence ledger

## Identity and interpretation

The application source tested locally is `29abf5d8bd6f05b1f0c027d8753f4837840215dc`, tree `83a0b69f4e8eabe81c103d0923910f17cb48b98d`. All 372 tracked source files were reconciled by content hash and executable mode before and after each recorded runtime command. The documentation candidate is a separate working-tree artifact; its eventual commit, independent review, PR checks, merge and deployment identities belong in external integration receipts. This page cannot claim the hash of its own future commit.

The local runtime used Python 3.12.14, Node 24.22.3 and npm 11.9.0. Scientific packages matched the seven pins in `requirements-tested.txt`; the interpreter did not match that file's Linux/Python 3.13.5 reference target. Package installation and build success are not end-to-end browser or market validation. [requirements-tested.txt](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/requirements-tested.txt) [pyproject.toml](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/pyproject.toml)

## Observed local commands, 2026-11-19 UTC

| Observation | Actual result | Time and scope |
| --- | --- | --- |
| Initial `python -m pytest -W error` | **FAIL before collection** | 23:29:18–23:29:19; unrelated host AnyIO plugin raised a `CallSpec2` deprecation under pytest 9.2 |
| Same source with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` | **PASS: 255 tests, 54 subtests** | 23:29:25–23:30:30; 63.95 seconds reported by pytest; no skipped tests reported |
| First native Node subset | **PASS: 47 tests** | 23:29:47–23:29:48; engine, CSP, HTML-document and UUID tests actually discovered. Some requested filenames did not exist; the count is not the whole browser glob |
| Remaining publication/helper subset | **PASS: 11 tests** | 23:30:28–23:30:29; deployment CSP, preview health, production CSP, runtime security and engineering hero. Combined with the preceding nonoverlapping subset: 58 tests |
| `python scripts/verify_engines.py` | **PASS: 120 seeded cases** | 23:29:53; maximum objective difference 2.3283064365386963e−10 DKK, required `< 1e−6`; positive durations and negative-price cases included |
| First `npm run quality:lint` | **FAIL** | 23:30:36–23:30:41; 1,955 diagnostics from incomplete nested audit dependency installation |
| Nested audit `npm ci`, then lint | **PASS** | Dependency install 23:31:03–23:31:09; lint 23:31:33–23:31:38. Original failure retained |
| `npm run quality:typecheck` | **PASS** | 23:30:36–23:30:42; declared TypeScript project scope, not every generated/vendor declaration |
| `npm run quality:format` | **PASS** | 23:31:03–23:31:04; five explicitly named configuration/CSP files, not a repository-wide formatting claim |
| Ruff lint / format | **PASS / PASS** | 23:31:44; `src tests`, 34 Python files already formatted |
| Existing bounded research smoke | **PASS** | 23:31:33–23:32:23; new January–February 2023 data, default Phase 2 and reduced Phase 3, about 50.3 seconds |
| `python -m build --no-isolation` | **PASS** | 23:31:52–23:31:54; source archive and Python wheel 1.1.0 produced in isolated output directory; not a published release or a clean wheel installation test |
| Existing Chromium harness | **BLOCKED: launch failed** | 23:31:44; socket/ptrace permission error before page initialization. Host Playwright 1.62.0 also differs from declared 1.65.0. No new screenshots or browser acceptance result |
| Dedicated static build and check | **PASS / PASS** | Build 23:33:31, check 23:33:58; three pages / 58 output files checked locally; no deployment |
| Four documented native labs | **PASS** | 23:33:59–23:34:00; fixed-offer settlement, LP fixture, residual/bracket examples and snapshot recomputation |
| Four literal Python cells from the new lab page | **PASS** | 23:52:24–23:52:26; executed the authored snippets with numeric assertions; separate from the earlier native lab observation |
| New renderer against repository-wide Ruff | **Initial FAIL, repaired PASS** | 23:56:10 first run found 28 style/docstring diagnostics in the new docs helper; 23:57:05 rerun passed after scoped helper corrections. Existing source files were unchanged |
| Focused handbook contracts | **12 checks PASS** | 23:57:49; original ten image/link/HTML/table cases plus real published-index and rejected missing-index cases. Both new controls first failed and were retained; the current directory link already had an index |

These observations were recorded in separate command receipts with exact argument vectors, start/end times, exit codes, raw logs and tracked-input reconciliations. Failed records were not replaced by later passes. The normalized structured verification handoff preserves those receipts outside the repository. A new independent documentation reviewer must bind its decision to the frozen candidate.

## Claims and criteria

| Claim | Source/check | Meaning of the observation |
| --- | --- | --- |
| Two-price settlement and duration scaling | [src/zephyrtrade/evaluate.py:43–69](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/evaluate.py#L43-L69); native lab 1 and existing tests | 550/1100 DKK scenario outcomes, 880 DKK expected fixed-offer revenue; no strategy-optimality claim |
| LP versus breakpoint agreement | [scripts/verify_engines.py:1–169](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/verify_engines.py#L1-L169) | Objective agreement under declared price ordering; exact offer ties need not agree |
| Probability mass edge discrepancy | [src/zephyrtrade/optimize.py:97–168](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L97-L168) [src/zephyrtrade/optimize.py:214–255](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L214-L255) | Selected source-only reviewer reproduction at 23:28:53 returned 500 versus 500.0025 DKK for p=1.000005; API rejects it. Reviewer used different scientific package versions and retained an initial assertion-harness failure |
| Snapshot consistency | [scripts/build_app.py:87–211](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/build_app.py#L87-L211) | 3,888 rows, 34,992 revenue comparisons, fresh maximum difference 0.0 DKK. Verifies retained predictions/settlement, not retraining or original raw-data generation |
| Native local HTTP guards | [src/zephyrtrade/app.py:139–315](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L139-L315) and existing `tests/test_app.py` within 255-test run | Real loopback test server coverage; not remote service hardening or authentication |
| Static export identity/CSP | [scripts/build-domain.mjs](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/build-domain.mjs) [scripts/check-domain.mjs](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/check-domain.mjs) | Local generated output and declared canonical URLs; not canonical-site content observation |

The bounded research smoke's Phase 2 winner was Lasso. Its Phase 3 comparator remained locally weighted regression by implementation. Historic model rankings and screenshots remain their original evidence. The full archived three-year training experiment was not rerun. [src/zephyrtrade/phase3.py:283–333](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase3.py#L283-L333)

## Dated remote source baseline

At 2026-11-19 23:26:36 UTC, the GitHub default/latest check-run response for the pinned source returned 27 records: **26 success and one skipped**. The eight returned workflow runs were successful; their executions were on November 17–18, before this documentation candidate. They are a source baseline, not current candidate CI or all historical attempts. Sources: [check-run endpoint](https://api.github.com/repos/mohammadrezwankhan/zephyrtrade/commits/29abf5d8bd6f05b1f0c027d8753f4837840215dc/check-runs?per_page=100&page=1), [source CI run](https://github.com/mohammadrezwankhan/zephyrtrade/actions/runs/44131413050), [Cloudflare export run](https://github.com/mohammadrezwankhan/zephyrtrade/actions/runs/44131412666).

The skipped `Publish source observation` job is conditional on `MKLAB_TRACEABILITY_ACTIVE`, event type and main-branch conditions. Its skip is not a passed execution. The condition is visible in source; the specific absent condition must not be guessed from the skip alone. [.github/workflows/mklab-traceability-sync.yml:38–46](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/.github/workflows/mklab-traceability-sync.yml#L38-L46)

Ruleset details observed at 23:33:07 UTC included active deletion/non-fast-forward protection and an active strict `traceability-links` required check. Classic branch-protection access returned 403, so complete merge-policy discovery remains incomplete. Pages metadata returned an unsupported-route error through the available connector; this does not prove a site is absent. See the [release playbook](CI_CD_AND_RELEASE_PLAYBOOK.md).

## Remaining verification boundaries

Fresh candidate CI, full current policy, an expected-head guarded merge, browser acceptance and merged-site content are separate later gates. No CircleCI or Buildkite configuration was found in the complete pinned tree; no claim is made about inaccessible external services. No live trading, measured wind validation, penetration test, profitability, financial advice or operational readiness is established by these checks.
