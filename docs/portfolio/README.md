# ZephyrTrade · Wind Market Research — learning map

Synthetic wind-market research with forecasting comparisons, chronological backtests and explicit application limits.

This companion organises 6 selected source-backed paths. It complements the repository's full documentation and native lessons. It does not execute its scientific or operational models.

Open `index.html` locally for search, topic filters, source/configuration inspection, personal notes and study-plan export. The guide has no network or build dependency.

Open the [offline interactive lesson lab](../index.html) and inspect its [lesson configuration](../lesson-config.json).

| Path | Learning objective | Level | First source |
| --- | --- | --- | --- |
| path-01 | Trace synthetic observations | Foundation | [src/zephyrtrade/data_loader.py](../../src/zephyrtrade/data_loader.py) |
| path-02 | Compare forecast and direct-offer models | Foundation | [src/zephyrtrade/models.py](../../src/zephyrtrade/models.py) |
| path-03 | Calculate a weighted-quantile offer | Applied | [src/zephyrtrade/web/engine.js](../../src/zephyrtrade/web/engine.js) |
| path-04 | Compare strategies on the same window | Applied | [src/zephyrtrade/evaluate.py](../../src/zephyrtrade/evaluate.py) |
| path-05 | Save and recover scenario inputs | Advanced | [src/zephyrtrade/web/app.js](../../src/zephyrtrade/web/app.js) |
| path-06 | Reproduce numerical and snapshot evidence | Advanced | [scripts/verify_engines.py](../../scripts/verify_engines.py) |

## Provenance

Repository: <https://github.com/mohammadrezwankhan/zephyrtrade>

Pinned source: 090c28970f1a6c6f3032aaa4cf086e0d475a84da

Native commands and expected outputs are guidance unless accompanied by a separate execution record. Reviewed-path progress is a personal learning record.
