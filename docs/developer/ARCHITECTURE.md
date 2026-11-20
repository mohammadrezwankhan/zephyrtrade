# Architecture and execution boundaries

> Source snapshot: [`29abf5d8bd6f05b1f0c027d8753f4837840215dc`](https://github.com/mohammadrezwankhan/zephyrtrade/tree/29abf5d8bd6f05b1f0c027d8753f4837840215dc), inspected 20 November 2026. This is source documentation, not a new release, test run or deployment receipt.

## Paths through the project

| Boundary | Implementation | Contract |
| --- | --- | --- |
| Data generation | [data_loader.py](../../src/zephyrtrade/data_loader.py), [preprocessing.py](../../src/zephyrtrade/preprocessing.py) | Synthetic Bornholm-like wind, weather and market-price rows; deterministic configuration and price filtering |
| Forecast and strategy analysis | [phase2.py](../../src/zephyrtrade/phase2.py), [phase3.py](../../src/zephyrtrade/phase3.py) | Chronological evaluation; compare forecasts, offers and financial outcomes without future-data leakage |
| Optimisation | [optimize.py](../../src/zephyrtrade/optimize.py) | Finite scenario vectors, nonnegative probabilities, price-order validation, capacity bounds and HiGHS LP |
| Financial evaluation | [evaluate.py](../../src/zephyrtrade/evaluate.py) | MW/MWh, DKK and DKK/MWh kept explicit; undefined capture is not represented as zero |
| Python HTTP application | [app.py](../../src/zephyrtrade/app.py) | IPv4 loopback on 127.0.0.1, fixed static-asset allowlist and bounded JSON solver requests |
| Browser numerical engine | [engine.js](../../src/zephyrtrade/web/engine.js), [app.js](../../src/zephyrtrade/web/app.js) | Local/browser calculation and device-local saved scenarios |
| Reproducibility | [pipeline.py](../../src/zephyrtrade/pipeline.py), [verify_engines.py](../../scripts/verify_engines.py) | File SHA-256 manifests and cross-language numerical comparisons |

## What the separate surfaces do not share

A static browser export, local Python server and offline portable application do **not** imply a shared production backend, remote account system or order-placement API. The domain/export mechanism is separately described in [Cloudflare deployment notes](../CLOUDFLARE.md). The browser can use a local SciPy cross-check only when the local Python service is started; it does not load persisted estimator pickles or submit market orders.

## Change-impact review

For a change to an offer or settlement equation, inspect both [optimize.py](../../src/zephyrtrade/optimize.py) and [evaluate.py](../../src/zephyrtrade/evaluate.py), the [browser engine](../../src/zephyrtrade/web/engine.js), the [cross-engine verifier](../../scripts/verify_engines.py), source fixtures and affected tests. Update [equations](../math-and-physics/EQUATIONS_AND_DERIVATIONS.md) and the dated [evidence ledger](../maintainer/VERIFICATION_EVIDENCE_LEDGER.md) only with actual fresh results.
