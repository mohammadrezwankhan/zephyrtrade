# Portfolio integration boundary

This document describes ZephyrTrade's own public integration metadata. It contains no inventory or findings from other repositories. The [public source](https://github.com/mohammadrezwankhan/zephyrtrade) remains the authority for its software; the existing portal and dedicated pages are navigation/publication surfaces, not independent scientific validation.

## Implemented public mapping

`traceability.json` maps this repository's app identifier `37` to main/public source and the following declared endpoints. The identifier is an opaque mapping key, not a count of repositories. [traceability.json](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/traceability.json)

| Purpose | Configured route | Evidence boundary |
| --- | --- | --- |
| Portal | `https://mklab.co.technology/` | Existing public navigation; no portfolio-wide coverage claim |
| Overview | `https://mktrade.co.business/` | Dedicated explanatory page |
| Runtime | `https://mktrade.co.business/run/` | Static browser research app; no order execution |
| Runtime metadata | `https://mktrade.co.business/app.json` | Deployment/source association must be checked against observed bytes |
| Collection build | `https://mklab.co.technology/apps/zephyrtrade/` | Separately configured collection export; not automatically identical to the dedicated build |

The local traceability checker validates visible source links and configuration. Its live mode has additional endpoint/metadata checks. The workflow's optional source-observation bridge is conditional and records a source revision after its checks. A source observation does not identify the commit actually deployed to a public runtime. [scripts/check-traceability.py](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/check-traceability.py) [.github/workflows/mklab-traceability-sync.yml](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/.github/workflows/mklab-traceability-sync.yml) [cloudflare.json](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/cloudflare.json) [cloudflare-domain.json](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/cloudflare-domain.json)

The current documentation task observed source checks and local builds, not a fresh canonical-site deployment. Effective merge policy and Pages metadata were partly inaccessible. Consequently this package must not be promoted as newly merged, newly published or fully audited in a portfolio dashboard before those separate receipts exist.

## Reusable contracts and non-integration

The source offers reusable ideas—MW/MWh duration discipline, explicit synthetic provenance, chronological data partitioning, source-pinned numerical parity and browser import/recalculation rules. These are potential shared documentation conventions. No cross-repository scientific service, common trained model, unified authentication, shared database or automatic deployment dependency is established by this review. Reuse needs its own unit/schema/version/rights agreement.

The existing teaching companion, native lessons and six-path reading guide have historical source pins. They remain reading/teaching surfaces with distinct numerical scopes. This handbook links them while explicitly separating USD/basis-point teaching from DKK/MWh native settlement. [docs/lesson-config.json](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/docs/lesson-config.json) [docs/native-lessons.json](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/docs/native-lessons.json) [docs/portfolio/README.md](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/docs/portfolio/README.md)

## Public status suitable for a later hub

A public status entry can link the canonical [index](../INDEX.md), [evidence ledger](../maintainer/VERIFICATION_EVIDENCE_LEDGER.md), [limitations](../math-and-physics/ASSUMPTIONS_AND_LIMITS.md) and [roadmap](../../ROADMAP.md), and report actual dated content/QA/CI/merge/publication outcomes. Keep the source SHA and scope beside any test count. Do not publish operational logs, credentials, private input data, or identities/findings from private repositories. Proposed work stays proposed until an independently reviewed implementation and its evidence are available.
