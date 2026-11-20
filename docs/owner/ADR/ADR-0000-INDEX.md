# Architecture decision register

> Source snapshot: [`29abf5d8bd6f05b1f0c027d8753f4837840215dc`](https://github.com/mohammadrezwankhan/zephyrtrade/tree/29abf5d8bd6f05b1f0c027d8753f4837840215dc), inspected 20 November 2026. This is source documentation, not a new release, test run or deployment receipt.

This index reconstructs observed source choices; it does **not** claim that unrecorded owner approvals or historic ADRs exist.

| ID | Observed decision | Evidence | Status |
| --- | --- | --- | --- |
| ZT-ADR-OBS-01 | Use generated/synthetic wind-market data and preserve chronological evaluation | [Data generator](../../../src/zephyrtrade/data_loader.py), [contributing](../../../CONTRIBUTING.md) | Implemented source constraint |
| ZT-ADR-OBS-02 | Keep the optional SciPy HTTP application loopback-only | [Local app](../../../src/zephyrtrade/app.py), [security](../../../SECURITY.md) | Implemented source boundary |
| ZT-ADR-OBS-03 | Cross-check browser objectives against SciPy HiGHS without assuming equal optimum offers under ties | [Verifier](../../../scripts/verify_engines.py) | Implemented test contract |
| ZT-ADR-OBS-04 | Separate static domain export from multi-app collection publishing | [Cloudflare guide](../../CLOUDFLARE.md) | Source-defined publication distinction |

**Proposed ADR topics**, pending human decision: live-provider rights and data-vintage policy; external security review; a production trading/market integration boundary; a consistent historical release/citation versioning convention. Do not mark these accepted by generating documentation alone.
