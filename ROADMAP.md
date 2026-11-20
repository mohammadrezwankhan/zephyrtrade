# ZephyrTrade roadmap

1. Reproduce the documented source checks and close remaining issues in QUALITY_REPORT.md.
2. Verify native-origin reload, export/restore and keyboard behavior around the primary ZephyrTrade workflow, with fictional inputs.
3. Obtain domain and Bangla/English review before expanding the supplied catalogue or instructional content.
4. Keep live-data adapters, accounts, delivery, clinical/safety decisions and paid integrations out of scope until a separate design has source, rights, privacy and accountable operational owners.

No dates or service commitments are implied. Propose changes with acceptance criteria and evidence.

## Evidence-linked twelve-month plan · 2026-11-19 to 2027-11-18

This is a proposed development plan anchored to the documentation task date, not a claim that future work is already implemented or staffed. The original roadmap above remains unchanged. The window covers twelve calendar months, including partial 2026 Q4 and partial 2027 Q4. Roles and effort ranges are suggestions in engineering days; access/review lead time is separate. Source is `29abf5d8bd6f05b1f0c027d8753f4837840215dc` unless a current documentation page is identified.

The near-term priorities are the demonstrated low-level probability contract, missing native-browser evidence, clean environment replay and inaccessible delivery policy. Research expansions depend on information timing and retained-data provenance. No new accounts, live broker, hosting, measured-data ingestion, tag or application change is authorized by this plan itself.

### Now · 2026-11-19 through 2026-12-31 (Partial 2026 Q4)

#### ZT-N01 — Make probability mass a deliberate library contract

**defect · P1 · Proposed owner: Numerical maintainer · Effort: 2–4 engineering days · Confidence: High: exact source counterexample.**

Evidence: Direct LP accepts weight 1.000005 without normalization; LP 500 DKK differs from full expected revenue 500.0025 DKK. The API rejects the example. [src/zephyrtrade/optimize.py:97–168](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L97-L168)

Outcome: Choose reject-versus-normalize semantics for the low-level solver and evaluator, document migration, and implement it only in a separate numerical PR.

Dependencies: None beyond ordinary maintainer review. Risk/assumption: Changing permissive behavior can break library callers; no evidence currently shows the normalized UI pipeline failing.

Acceptance:

- Boundary fixtures cover mass below/above 1, individual limits, zero weights and negative/nonfinite inputs.
- Accepted normalized cases agree between LP and full expected revenue to the declared tolerance.
- API/browser behavior and tie policy are explicitly preserved or deliberately versioned.

Verification: Independent review of contract and tests; run existing optimize/evaluate/native parity suites plus new focused mass-boundary cases. Milestone: proposed Now review by 2026-12-31.

#### ZT-N06 — Close native-origin browser evidence gaps

**verification · P1 · Proposed owner: Browser QA maintainer · Effort: 2–4 days · Confidence: High: known capability gap.**

Evidence: The local Chromium process failed before page load; source workflows declare three-browser testing. [tests/browser/audit/playwright.config.ts:1–53](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/tests/browser/audit/playwright.config.ts#L1-L53)

Outcome: Use a capable runner to exercise the existing audit with exact final runtime hash and native file/HTTP origin cases.

Dependencies: None beyond ordinary maintainer review. Risk/assumption: Browser storage, permissions and platform differences may reveal issues invisible to Node tests; no screenshots should be synthesized as evidence.

Acceptance:

- Chromium/Firefox/WebKit results retain exact versions, commands, source/build hash and failures.
- Save/reload/export/restore, storage denial, stale results, keyboard dialogs and mobile chart/table controls are exercised.
- Manual visual/assistive review limits remain separate from automated passes.

Verification: Run existing browser audit and focused native-origin acceptance; retain real screenshots and trace/run identities. Milestone: proposed Now review by 2026-12-31.

#### ZT-N07 — Publish a clean environment replay recipe

**maintenance · P1 · Proposed owner: Toolchain maintainer · Effort: 1–3 days · Confidence: High: observed setup failures.**

Evidence: Reference pins target Linux/Python 3.13.5; local test interpreter was 3.12.14. Host plugin autoload and missing nested audit dependencies caused retained first failures. [requirements-tested.txt:1–9](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/requirements-tested.txt#L1-L9)

Outcome: Document or automate an isolated clean-room replay that reports actual versions and installs each declared Node project.

Dependencies: None beyond ordinary maintainer review. Risk/assumption: Dependency availability and supported wheel platforms may vary; preserve broad support separately from a tested matrix.

Acceptance:

- Actual Python 3.13.5 and all seven scientific pins are verified in the reference job.
- A clean environment executes warnings-as-errors tests without unrelated plugin contamination.
- Nested audit lock install and root quality commands are reproducible without changing manifests merely to silence failures.

Verification: Independent clean-environment run with pip check/freeze and lockfile hashes; compare with source workflow commands. Milestone: proposed Now review by 2026-12-31.

#### ZT-N10 — Resolve delivery-policy and publication evidence

**delivery · P1 · Proposed owner: Repository and hosting maintainer · Effort: 1–3 days plus external access lead time · Confidence: Medium: permissions external.**

Evidence: Classic branch policy returned 403; Pages metadata route was unavailable. Visible rulesets and historical source checks are only partial delivery evidence. [.github/workflows/deploy-dashboard.yml:61–93](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/.github/workflows/deploy-dashboard.yml#L61-L93)

Outcome: Obtain supported read access or authenticated owner evidence, then verify reviewed candidate checks, expected-head merge and existing-route deployment identity.

Dependencies: None beyond ordinary maintainer review. Risk/assumption: Required human review, queue or protected environment may prevent autonomous completion; never bypass them.

Acceptance:

- Full effective branch/review/check policy is recorded for the intended head/base.
- Any merge uses an expected-head guard and records actual merged SHA.
- Published handbook content and deployment/build identity match the merged revision; otherwise status stays explicitly unverified.

Verification: Provider metadata plus complete PR diff/check reconciliation and canonical-site distinctive-content inspection. Milestone: proposed Now review by 2026-12-31.

### Next · 2027-01-01 through 2027-03-31 (2027 Q1)

#### ZT-N02 — Specify information available at bid time

**research contract · P1 · Proposed owner: Forecasting researcher and domain reviewer · Effort: 5–10 days · Confidence: Medium: requires domain assumptions.**

Evidence: Climate columns are synthetic forecast-time proxies; current ex-post optimization uses realized test prices. [src/zephyrtrade/preprocessing.py:20–60](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/preprocessing.py#L20-L60)

Outcome: Define forecast issue/valid timestamps, price-information assumptions and an explicit prospective-versus-ex-post experiment contract.

Dependencies: ZT-N07. Risk/assumption: Realistic forecast-vintage data may be unavailable or separately licensed; do not imply that a schema alone removes leakage.

Acceptance:

- Every prospective input has an issuance/availability rule relative to bid time.
- Synthetic fixtures deliberately include late-arriving/revised inputs and reject forbidden information.
- Reports label oracle/ex-post and prospective experiments separately.

Verification: Domain-reviewed data contract, timestamp assertions and chronological leakage counterexamples in a separate research branch. Milestone: proposed Next review by 2027-03-31.

#### ZT-N03 — Quantify negative-price filtering sensitivity

**research · P1 · Proposed owner: Energy-market researcher · Effort: 5–8 days · Confidence: Medium: experiment outcome unknown.**

Evidence: All negative-price market rows are removed upstream, while ordered negative prices are valid in the offering engine. [src/zephyrtrade/data_loader.py:361–380](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/data_loader.py#L361-L380)

Outcome: Run paired synthetic all-hours and filtered scenarios with consistent calendar alignment, published assumptions and distinct retained baselines.

Dependencies: ZT-N02, ZT-N07. Risk/assumption: Changing the sample population can change rankings; market price-order violations require a separately designed model rather than forced validation.

Acceptance:

- Both experiment populations and missing/filtered intervals are enumerated.
- Metrics disclose calendar coverage, price regime, duration and strategy information set.
- Original archived results remain immutable and new outputs have source/config/environment identities.

Verification: Calendar-join audit, native settlement/parity fixtures and paired report with input hashes; no real-profitability inference. Milestone: proposed Next review by 2027-03-31.

#### ZT-N04 — Make the indirect comparison identity explicit

**engineering · P2 · Proposed owner: Research pipeline maintainer · Effort: 2–4 days · Confidence: High: fixed source column.**

Evidence: Phase 3 always loads locally_weighted_offer_mw; the fresh bounded run selected Lasso in Phase 2. [src/zephyrtrade/phase3.py:283–333](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase3.py#L283-L333)

Outcome: Add a separately reviewed explicit comparator configuration/result field if flexibility is desired, preserving the fixed-LW historical experiment.

Dependencies: ZT-N01. Risk/assumption: Dynamic selection on held-out test revenue would introduce selection bias; comparator choice must precede test comparison.

Acceptance:

- Reports state comparator model ID, selection data and prediction source hash.
- Missing, mismatched or misaligned comparator columns fail clearly.
- Default historical LW behavior remains reproducible and optional alternatives are separately labeled.

Verification: Focused configuration/alignment tests and a bounded experiment demonstrating default and declared alternative without test-set selection. Milestone: proposed Next review by 2027-03-31.

#### ZT-N05 — Align documented boundary tests across surfaces

**contract tests · P2 · Proposed owner: API and browser maintainer · Effort: 3–6 days · Confidence: High: observable surface differences.**

Evidence: Python API rejects unknown/duplicate keys and numeric strings; browser import projects fields and JSON.parse accepts duplicates; low-level revenue helpers accept broader domains. [src/zephyrtrade/app.py:38–100](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L38-L100)

Outcome: Build a deliberate surface-contract matrix and fixtures; decide explicitly which differences remain supported.

Dependencies: ZT-N01, ZT-N06. Risk/assumption: A universal strictness change could silently invalidate existing imports; library and transport layers have different purposes.

Acceptance:

- Each HTTP/browser/library input boundary has an expected outcome and source-linked fixture.
- Duration, price order, capacity, probability tolerance and unknown/duplicate fields are represented.
- Import recalculation, stale results and objective tie handling remain verifiable.

Verification: Targeted API/native-engine/import tests plus capable-browser evidence, keeping numerical and transport assertions separate. Milestone: proposed Next review by 2027-03-31.

### Later · 2027-04-01 through 2027-06-30 (2027 Q2)

#### ZT-N11 — Evaluate forecast and economic uncertainty

**research · P2 · Proposed owner: Statistical researcher · Effort: 8–15 days · Confidence: Medium-low: outcomes exploratory.**

Evidence: Validation residual quantiles and point metrics do not by themselves establish calibrated forecast intervals or stable economic rankings. [src/zephyrtrade/phase2.py:500–579](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase2.py#L500-L579)

Outcome: Design chronological residual-calibration, sensitivity and ranking-uncertainty experiments with predeclared metrics and computational budget.

Dependencies: ZT-N02, ZT-N03. Risk/assumption: Autocorrelation and filtered uneven timestamps can invalidate naive independent bootstrap assumptions.

Acceptance:

- Resampling/holdout methodology states time dependence and equal-calendar comparability assumptions.
- Forecast calibration and economic sensitivity are reported separately.
- All intervals, seeds, populations and failed hypotheses are retained without claiming production performance.

Verification: Reviewed statistical protocol, bounded synthetic controls with known behavior and independently inspected result tables. Milestone: proposed Later review by 2027-06-30.

#### ZT-N08 — Improve recoverable experiment manifests

**maintenance · P2 · Proposed owner: Reproducibility maintainer · Effort: 3–6 days · Confidence: High: current manifest scope explicit.**

Evidence: The run manifest hashes four summaries/provenance files; original full raw/processed tables are not all retained. [src/zephyrtrade/pipeline.py:91–172](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/pipeline.py#L91-L172)

Outcome: Define full retained-versus-regenerable artifact accounting and a safe recovery procedure with exact environment/config identities.

Dependencies: ZT-N07. Risk/assumption: Large artifacts and serialization compatibility raise storage and security costs; a plain digest does not authenticate origin.

Acceptance:

- Every retained output has a path/type/size/hash and provenance relationship.
- A clean recovery drill verifies selected numerical outputs with declared tolerances.
- No untrusted joblib/pickle loading is required; historical artifacts remain intact.

Verification: Manifest completeness checks and a bounded clean-room regeneration/restore drill with actual records. Milestone: proposed Later review by 2027-06-30.

#### ZT-N12 — Review teaching transfer and terminology

**documentation · P2 · Proposed owner: Teaching maintainer and domain/language reviewers · Effort: 3–7 days · Confidence: Medium: reviewers not assigned.**

Evidence: Companion USD/bps and native DKK/MWh engines are intentionally distinct; original roadmap requests domain and Bangla/English review. [docs/lesson-config.json:1–317](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/docs/lesson-config.json#L1-L317)

Outcome: Review lesson language, numerical checkpoints, source-pin boundaries and learner transfer into the native model.

Dependencies: ZT-N06, ZT-N05. Risk/assumption: Translated terms can blur offered power, energy, cost and oracle metrics; review availability is not assured.

Acceptance:

- Every exercise identifies its model, units, time and calibration status.
- All eight current numeric checkpoints retain explicit tolerance and source evidence.
- Language/domain feedback is documented without representing teaching completion as certification.

Verification: Independent terminology review, source-model checkpoint checks and recorded learner walkthrough on capable browsers. Milestone: proposed Later review by 2027-06-30.

#### ZT-N13 — Keep documentation drift detectable

**documentation tooling · P2 · Proposed owner: Documentation maintainer · Effort: 2–4 days · Confidence: High: isolated renderer exists.**

Evidence: Multiple historical reading surfaces and generated handbook can diverge from current source without explicit identity checks. [current documentation runbook](docs/maintainer/DOCS_MAINTENANCE_RUNBOOK.md)

Outcome: Maintain narrow source-locator, required-output, handbook-freshness and interface-accounting checks without broadening application CI unnecessarily.

Dependencies: ZT-N04, ZT-N08. Risk/assumption: Mechanical link checks cannot validate equations or scientific interpretation; avoid treating coverage counts as semantic proof.

Acceptance:

- Current-source paths/line ranges and canonical links resolve.
- Handbook generation is deterministic and preserves safe image/CSP behavior.
- Generated/vendor/media and unresolved dynamic interfaces remain visibly classified.

Verification: Focused docs validator negative controls, independent semantic review and full authorized-diff inspection. Milestone: proposed Later review by 2027-06-30.

### Horizon · 2027-07-01 through 2027-11-18 (2027 Q3 and partial Q4)

#### ZT-N14 — Assess a measured-data adapter without premature integration

**exploratory design · P3 · Proposed owner: Data steward and energy-domain owner · Effort: 5–10 days for assessment only · Confidence: Low: rights/access/forecast-vintage unresolved.**

Evidence: Current public provider URLs are references; no measured-data adapter or redistribution right is established. [src/zephyrtrade/data_loader.py:413–504](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/data_loader.py#L413-L504)

Outcome: Evaluate one candidate provider contract and document access rights, schema versions, revision history and a synthetic adapter test design before proposing implementation.

Dependencies: ZT-N02, ZT-N03, ZT-N08. Risk/assumption: A provider may not supply historical forecast vintages or redistribution rights; outcome may be a justified no-go.

Acceptance:

- Access/redistribution terms and exact dataset/schema/resolution are recorded from authoritative current evidence.
- Issue/valid time, DST, missing-data and revision policies have testable definitions.
- Decision explicitly approves a separately scoped implementation or records why no integration should proceed.

Verification: Primary-source rights/schema review and synthetic contract fixtures; no credentials or measured records committed by this assessment. Milestone: proposed Horizon review by 2027-11-18.

#### ZT-N15 — Test transfer across synthetic farms and regimes

**research · P3 · Proposed owner: Forecasting researcher · Effort: 8–15 days · Confidence: Medium-low: hypotheses exploratory.**

Evidence: Generator has four site proxies while the current default evaluated farm is Ronne Coastal. [src/zephyrtrade/data_loader.py:37–87](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/data_loader.py#L37-L87)

Outcome: Design farm-separated and regime-shift comparisons using declared capacity/weather differences and fixed evaluation contracts.

Dependencies: ZT-N11, ZT-N03. Risk/assumption: Synthetic diversity is not geographic or operational external validation; shared generator assumptions can dominate results.

Acceptance:

- Train/selection/test farms, dates and regimes are explicit and disjoint where intended.
- Per-farm capacity, time and price rules remain consistent.
- Report failures and uncertainty, without claiming measured-site generalization.

Verification: Independent experiment protocol, leakage tests, reproducible run manifests and reviewed per-regime tables. Milestone: proposed Horizon review by 2027-11-18.

#### ZT-N09 — Prepare an evidence-based release decision

**release planning · P2 · Proposed owner: Repository maintainer · Effort: 2–5 days plus required reviews · Confidence: Medium: downstream gates external.**

Evidence: Package version 1.1.0 and CFF preview-2026.09.30 refer to different records; local build is not published release evidence. [CITATION.cff:1–10](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/CITATION.cff#L1-L10)

Outcome: Reconcile actual version/tag/assets/citation records and propose a release only when required policy, browser/recovery and provenance gates are met.

Dependencies: ZT-N06, ZT-N08, ZT-N10, ZT-N13. Risk/assumption: Required reviewers or hosting gates may remain unavailable; no schedule or new tag is preauthorized by this roadmap.

Acceptance:

- A proposed release packet maps actual package, commit, tag, CFF, artifacts and test evidence.
- Required policy and human/independent approvals are satisfied or explicit blockers remain.
- No production/market validation language exceeds evidence; a no-release decision is valid.

Verification: Read-only release packet review first; any later release action requires its own authorized workflow and receipts. Milestone: proposed Horizon review by 2027-11-18.

#### ZT-N16 — Review outcomes and roll the next annual plan

**governance · P2 · Proposed owner: Repository owner with maintainers · Effort: 1–3 days · Confidence: High: review process feasible.**

Evidence: The original roadmap is intentionally undated; this package adds proposed evidence-linked sequencing with no staffing guarantee. [ROADMAP.md:1–8](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/ROADMAP.md#L1-L8)

Outcome: Review delivered, deferred, rejected and blocked items; update the next twelve-month plan from actual results.

Dependencies: ZT-N09, ZT-N12, ZT-N15. Risk/assumption: Unfinished dependency work must not be relabeled complete to meet calendar targets.

Acceptance:

- Each item has a dated outcome and supporting PR/run/review or explicit deferral.
- Public portfolio status separates content, CI, merge and publication and excludes private information.
- Next roadmap preserves unresolved scientific and access assumptions and assigns proposed roles.

Verification: Owner review of evidence ledger and actual repository delivery outcomes; no automatically scheduled notification is created. Milestone: proposed Horizon review by 2027-11-18.

### Monthly evidence checkpoints

These are planning checkpoints, not automated reminders or promised releases. Record actual progress against dependencies; carry unresolved items forward transparently.

| Month window | Evidence to review |
| --- | --- |
| 2026-11-19–2026-12-18 | Probability contract, clean replay and capable-browser plan |
| 2026-12-19–2027-01-18 | Delivery-policy evidence and forecast-time contract draft |
| 2027-01-19–2027-02-18 | Input availability fixtures and all-hours/filtered experiment design |
| 2027-02-19–2027-03-18 | Comparator identity and cross-surface contract outcomes |
| 2027-03-19–2027-04-18 | Research protocol and experiment-manifest scope |
| 2027-04-19–2027-05-18 | Recovery drill and chronological uncertainty controls |
| 2027-05-19–2027-06-18 | Teaching/language review and documentation drift checks |
| 2027-06-19–2027-07-18 | Measured-data feasibility/rights decision prerequisites |
| 2027-07-19–2027-08-18 | Farm/regime transfer experiment evidence |
| 2027-08-19–2027-09-18 | Scientific uncertainty and unclosed browser/provenance gaps |
| 2027-09-19–2027-10-18 | Proposed release packet or explicit no-release decision |
| 2027-10-19–2027-11-18 | Actual outcomes, remaining blockers and next annual plan |

Cross-repository runtime dependencies are not assumed. The established public portal/traceability mapping is documented in [portfolio integration](docs/owner/PORTFOLIO_INTEGRATION.md); any future shared schema or data adapter needs its own reviewed contract. The [debt ledger](docs/maintainer/FAILURE_MODES_AND_TECH_DEBT.md) and [verification ledger](docs/maintainer/VERIFICATION_EVIDENCE_LEDGER.md) supply the current evidence, including failed or unavailable checks.
