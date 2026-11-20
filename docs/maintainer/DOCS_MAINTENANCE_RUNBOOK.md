# Documentation maintenance runbook

> Source snapshot: [`29abf5d8bd6f05b1f0c027d8753f4837840215dc`](https://github.com/mohammadrezwankhan/zephyrtrade/tree/29abf5d8bd6f05b1f0c027d8753f4837840215dc), inspected 20 November 2026. This is source documentation, not a new release, test run or deployment receipt.

Canonical source descriptions live alongside their implementation. Read [existing architecture](../architecture/system-overview.md), [engineering case study](../engineering/CASE_STUDY.md), [original research guide](../../README_RESEARCH.md), [quality report](../../QUALITY_REPORT.md) and the new [documentation index](../INDEX.md) before replacing established text.

## Change matrix

| Source change | Update and verify |
| --- | --- |
| Optimiser, prices, probability or capacity rule | [Equations](../math-and-physics/EQUATIONS_AND_DERIVATIONS.md), [units](../math-and-physics/PARAMETERS_AND_SYMBOLS.md), browser parity and LP tests |
| Forecast/data/price filtering | [Architecture](../developer/ARCHITECTURE.md), calibration/test chronology, manifests and historical limitations |
| HTTP/CLI interface | [Interfaces](../developer/API_CLI_AND_INTERFACES.md), request examples, local server security tests |
| Dependency/lockfile | [Toolchain matrix](TOOLCHAIN_AND_DEPENDENCY_MATRIX.md), Python matrix and pinned-environment results |
| Public export or site | [Release playbook](CI_CD_AND_RELEASE_PLAYBOOK.md), [Cloudflare guide](../CLOUDFLARE.md), artifact hash, actual provider receipt |
| New capability | [Changelog](../../CHANGELOG.md) and existing release/citation metadata **only if a real release occurred** |

## Evidence quality requirements

Record full commit SHA, command, environment, timestamp, exit status, test counts and log/artifact hashes. Preserve failed/skipped checks; do not recast a historic source check as candidate verification. Include a diff summary, no source/security policy drift and an independent review before merge. For proposed work, keep roadmap hypotheses distinct from accepted architectural decisions. Do not store secrets, real trades or confidential input in docs.
