# Repository recovery and handover runbook

> Source snapshot: [`29abf5d8bd6f05b1f0c027d8753f4837840215dc`](https://github.com/mohammadrezwankhan/zephyrtrade/tree/29abf5d8bd6f05b1f0c027d8753f4837840215dc), inspected 20 November 2026. This is source documentation, not a new release, test run or deployment receipt.

This runbook is a **proposed procedure**, not evidence that a backup was restored or another maintainer was appointed.

1. **Re-establish authorization.** Obtain owner-approved GitHub and artifact access through trusted channels. Keep secrets out of logs/docs.
2. **Recover immutable source.** Fetch the exact commit, verify Git tree and licensing, and compare [README](../../README.md), [CFF](../../CITATION.cff), [LICENSE](../../LICENSE), [SECURITY](../../SECURITY.md), lockfiles and original workflows.
3. **Recreate toolchain.** Follow [setup](../developer/SETUP_AND_REPRODUCIBILITY.md), Python 3.11+ and the pinned-original CI environment. Do not silently substitute an unpinned latest solver.
4. **Recover data provenance.** Use synthetic input generators or specifically authorised source files; inspect the pipeline manifest and SHA-256 digests. Never treat hidden local browser state as the source of record.
5. **Prove numerical boundaries.** Run pytest and browser/SciPy parity, inspect sample chronology, LP price order, capacity enforcement and undefined-metric semantics.
6. **Inspect publication separately.** Rebuild the *complete* intended Cloudflare artifact with source-defined scripts; preserve collection vs dedicated-domain separation. Do not deploy without owner approval and required checks.
7. **Document handoff.** Record exact refs, toolchain, access gaps, tests actually executed, output digests, pending risks and next approvers.

A green README badge, historical screenshot or old workflow run is not a recovery rehearsal. Report missing artifacts plainly rather than inventing restoration success.
