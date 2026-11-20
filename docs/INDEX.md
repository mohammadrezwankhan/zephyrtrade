# ZephyrTrade reference handbook

> Source snapshot: [`29abf5d8bd6f05b1f0c027d8753f4837840215dc`](https://github.com/mohammadrezwankhan/zephyrtrade/tree/29abf5d8bd6f05b1f0c027d8753f4837840215dc), inspected 20 November 2026. This is source documentation, not a new release, test run or deployment receipt.

ZephyrTrade is a local research and educational application for **synthetic** wind production, forecast comparisons, day-ahead offers, two-price imbalance settlement and numerical verification. The published browser export is not a trading service. Start with the [project overview](../README.md), [source research guide](../README_RESEARCH.md), [quality and evidence report](../QUALITY_REPORT.md), and [security policy](../SECURITY.md).

## Developer guide
- [Architecture and trust boundaries](developer/ARCHITECTURE.md)
- [Setup and reproducibility](developer/SETUP_AND_REPRODUCIBILITY.md)
- [CLI, APIs and interfaces](developer/API_CLI_AND_INTERFACES.md)
- [Worked experiments](developer/WORKED_EXAMPLES_AND_LABS.md)
- [Troubleshooting](developer/TROUBLESHOOTING.md)

## Equations and assumptions
- [Settlement, quantiles and optimisation](math-and-physics/EQUATIONS_AND_DERIVATIONS.md)
- [Parameters and units](math-and-physics/PARAMETERS_AND_SYMBOLS.md)
- [Model applicability and limits](math-and-physics/ASSUMPTIONS_AND_LIMITS.md)

## Maintainer and owner
- [Verification and evidence ledger](maintainer/VERIFICATION_EVIDENCE_LEDGER.md), [CI and release](maintainer/CI_CD_AND_RELEASE_PLAYBOOK.md), [toolchain](maintainer/TOOLCHAIN_AND_DEPENDENCY_MATRIX.md)
- [Documentation maintenance](maintainer/DOCS_MAINTENANCE_RUNBOOK.md), [failure modes](maintainer/FAILURE_MODES_AND_TECH_DEBT.md)
- [Architecture decisions](owner/ADR/ADR-0000-INDEX.md), [governance](owner/GOVERNANCE_AND_SCOPE.md), [recovery](owner/BUS_FACTOR_RECOVERY_RUNBOOK.md), [portfolio boundary](owner/PORTFOLIO_INTEGRATION.md)

## Scope and evidence types
Existing source and release documents remain authoritative for their own claims. A **declared command** is not an executed check; a **historical successful run** is not evidence that this documentation candidate passed; a **synthetic scenario** is not market data. This package adds navigable maintenance material without changing the Python/JavaScript engines, CI configuration, existing citations or deployable assets. Proposed future work is identified as such.
