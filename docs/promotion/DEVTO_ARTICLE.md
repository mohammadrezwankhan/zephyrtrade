# Checking forecast quality and offer revenue separately

ZephyrTrade generates synthetic wind, weather and price tables, compares forecast and direct-offer strategies, and reconciles hypothetical revenue. Its Python and browser engines expose the assumptions so a researcher can inspect numerical agreement instead of relying on a dashboard alone.

## Trace the implementation

Start with `src/zephyrtrade/app.py`. The input side is **synthetic weather and prices**; the rule boundary is **forecast and offer strategies**; the displayed result is **revenue and parity evidence**. Keep these three concerns distinct when changing a screen or fixture. Follow [the source map](../../PROJECT_ANALYSIS.md) for the remaining modules.

The following are actual test names in the supplied source, selected as starting points for review rather than a coverage claim:

- `surplus, shortfall and interval settlement are explicit` — [`tests/browser/engine.test.cjs`](../../tests/browser/engine.test.cjs).
- `weighted quantile agrees with every piecewise breakpoint` — [`tests/browser/engine.test.cjs`](../../tests/browser/engine.test.cjs).
- `test health and loopback binding` — [`tests/test_app.py`](../../tests/test_app.py).
- `test packaged assets` — [`tests/test_app.py`](../../tests/test_app.py).

## A useful first investigation

Run the README demo with fictional inputs. Choose one displayed record or calculation and locate its source. Trace the rule that decides the visible state, then follow any local save or export. Record the actual value before and after a single input change. If the interface cannot explain that transition, submit a small reproduction linked to the responsible rule.

Use [QUALITY_REPORT.md](../../QUALITY_REPORT.md) for executed checks and limits. A green unit suite, a responsive initial screen and a validated domain service are different kinds of evidence; only the first two are within this repository-factory evaluation.

## Try the local workflow

```sh
git clone https://github.com/mohammadrezwankhan/zephyrtrade.git
cd zephyrtrade
node scripts/preview-demo.mjs
```

Draft for technical publication. Verify the cited release checks before posting. [Repository](https://github.com/mohammadrezwankhan/zephyrtrade).
