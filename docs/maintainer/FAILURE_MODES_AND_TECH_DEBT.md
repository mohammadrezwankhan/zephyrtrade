# Failure modes and technical debt register

> Source snapshot: [`29abf5d8bd6f05b1f0c027d8753f4837840215dc`](https://github.com/mohammadrezwankhan/zephyrtrade/tree/29abf5d8bd6f05b1f0c027d8753f4837840215dc), inspected 20 November 2026. This is source documentation, not a new release, test run or deployment receipt.

These are **inspection risks and verification needs**, not claims that the named behavior failed on this candidate.

| ID | Risk / limitation | What supports it | Proposed acceptance evidence |
| --- | --- | --- | --- |
| ZT-01 | Synthetic/training data can be mistaken for live tradable data | [README](../../README.md) and [data generator](../../src/zephyrtrade/data_loader.py) | Public copy labels provenance and data vintage in every entry point |
| ZT-02 | Chronological leakage or price-filter mismatch could inflate backtest metrics | [Contribution rules](../../CONTRIBUTING.md) | Explicit split/vintage/filter tests on a pinned source |
| ZT-03 | An optimiser/browser change can split Python and JS objectives | [Parity verifier](../../scripts/verify_engines.py) | Fresh seeded and boundary parity checks on candidate |
| ZT-04 | Local-only server could be incorrectly hosted publicly | [app.py](../../src/zephyrtrade/app.py) | Preserve loopback/Host and same-origin tests, never relax for public use |
| ZT-05 | `None` metrics may be misrepresented as financial zeros | [evaluate.py](../../src/zephyrtrade/evaluate.py) | One-row/nonpositive-oracle UI and API regression cases |
| ZT-06 | Static and hosted exports might drift from validated source | [Deployment guide](../CLOUDFLARE.md) | Complete output hashing and provider publication receipt |
| ZT-07 | Runner shortages can block original required checks | [Workflow definitions](../../.github/workflows/ci.yml) and account-level runner incident | Original required jobs complete at correct revision, no bypass |

Prioritise findings by actual user impact and evidenced failure, not by convenient file-count targets. Any release claim requires a distinct recorded acceptance result.
