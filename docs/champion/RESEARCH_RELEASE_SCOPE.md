# ZephyrTrade — qualified synthetic-research publication scope

**Review date:** 2026-11-22 (Europe/Paris). **Source subject:** [PR #90](https://github.com/mohammadrezwankhan/zephyrtrade/pull/90), initially verified at `8aaafe727ffd1e9d2782cf271d63df9d0d08b71c`. Always check the final merged commit and deployment independently; a source SHA is not a deployment receipt.

## What this release is

A reproducible **synthetic retrospective wind-research and educational software demonstration**. Its scenarios, historical snapshot, settlement optimization and numerical parity are meant for research inspection. It **does not** make or automate real trades; does not verify real forecast issuance, a real wind asset, current electricity-market settlement, prospective profitability, or regulatory compliance. The direct strategy lab is an assumptions tool, not a real trading decision engine.

The retained historical results use realised evaluation-period prices as **ex-post** inputs. The 24-hour production lag and trailing quantiles are chronological with respect to delivery time, but they are **not validated as available by a previous-day bid deadline**. Same-timestamp synthetic weather inputs have no verified forecast-vintage issue time. Do not describe these results as a leak-free prospective day-ahead bidding policy.

## Confirmed source checks (the PR candidate, not yet public deployment)

- [CI](https://github.com/mohammadrezwankhan/zephyrtrade/actions/runs/44959920012): Python 3.11, 3.12 and pinned 3.13.5 quality tests, Node numerical engine, shared Python/browser objective parity and packaging passed for PR #90 at `8aaafe727ffd`.
- [Hardened CI](https://github.com/mohammadrezwankhan/zephyrtrade/actions/runs/44959920055): all 12 language/security jobs passed, including actual OpenGrep/SAST, dependency scanning, secrets and Trivy.
- [Three-browser verification](https://github.com/mohammadrezwankhan/zephyrtrade/actions/runs/44959920040): 186 Playwright tests passed on Chromium, Firefox and WebKit; includes a native offline `file://` document navigation/calculation test. Automated tests do not replace a human screen-reader or production-host acceptance.
- [CodeQL](https://github.com/mohammadrezwankhan/zephyrtrade/actions/runs/44959920165) and required [traceability-links](https://github.com/mohammadrezwankhan/zephyrtrade/actions/runs/44959920086): succeeded at the recorded candidate.
- The previously vulnerable development-only `wcmatch==8.5.2` scanner dependency was updated to the audited, hashed `11.2` package. See [issue #91](https://github.com/mohammadrezwankhan/zephyrtrade/issues/91). This is not a claim about untested future dependency sets.

Every result above is tied to its original source revision and workflow logs. A documentation-only follow-up commit requires **its own** CI evidence before integration.

## Scientific limitations and unresolved work

1. **Prospective causality remains open:** [issue #92](https://github.com/mohammadrezwankhan/zephyrtrade/issues/92). Establish a previous-day information-vintage contract, decision cutoff (including DST), issuance-time fixtures, future-data invariance tests and a separate prospective evaluation before claiming day-ahead deployability. The present study is *retrospective*.
2. **Historical selection:** Negative-price rows were filtered from the retained backtest; supplemental negative-price stress tests do not repair the missing historical population. There are 53 absent retained-snapshot hours. Do not extend selected-population results to an unfiltered calendar.
3. **Comparator limitations:** Phase 3 compares to a fixed locally weighted indirect strategy and a perfect-foresight oracle, not an unbiased prospective production benchmark. The oracle is not implementable.
4. **External and human review:** Multi-agent independent scientific sign-off, live-host/security-header delivery, assistive technology and real participant UAT remain separate from the automatic source CI results.

## Release classification and publication safeguards

**CONDITIONAL — SYNTHETIC RESEARCH USE ONLY.** The software candidate has passed its recorded numerical, security and automatic browser checks, but G2 prospective forecast-information validation and G10 independent scientific review are not complete. It is **not** champion-certified for real trading, prospective forecast/dispatch decisions or investable profitability.

A Git merge, GitHub Pages deployment or Cloudflare deployment is only successful when its **actual post-merge run and published bytes** can be inspected; neither the existence of this document nor a green PR badge proves publication. The hosted lessons and native synthetic engine have distinct computations and units. Do not imply that publishing one automatically deploys the other.

## Maintainer follow-up

- Preserve the signed/immutable checks and repository branch protection; never suppress scanner findings or tests.
- Check the final merge commit, main-associated CI and actual deployment before announcing a version.
- Track prospective scientific acceptance separately in issue #92, without rewriting the historical synthetic experiment or adding broker/live integrations.
