# ZephyrTrade: project analysis

## Purpose and boundary

Research application that generates synthetic wind/weather/price tables, compares wind-forecast and direct-offer strategies, backtests revenue and explores hypothetical offers without placing trades.

Source evidence: `ZephyrTrade_Champion.zip`. Canonical repository: `zephyrtrade`. All supplied originals remain in the local Champion archive; exact duplicate exports were not made into separate repositories.

## Source map

- `src/zephyrtrade/app.py`
- `src/zephyrtrade/optimize.py`
- `src/zephyrtrade/web/engine.js`
- `scripts/verify_engines.py`
- `tests/test_app.py`
- `artifacts/reproduction/results/run_manifest.json`

## Distribution and verification

Demo entry: `ZephyrTrade-Champion.html`. Source verification commands appear in README. The latest executed outcomes are in QUALITY_REPORT.md. No Git history was present in the supplied ZIP; the initial main commit preserves the imported application, and improvements use `astra/championization`.

## Ownership and release interpretation

First-party source is available under [MIT](LICENSE). Bundled dependencies retain their upstream notices; trademarks and third-party content are not relicensed.

The user's requested MIT default is applied only to the supplied editable first-party project where inspection found no conflicting ownership/license. Existing third-party notices and original MIT licenses are retained. The three source-incomplete exports are held private. Publishing a fictional demonstration does not authorize live records or operation of the proposed service.
