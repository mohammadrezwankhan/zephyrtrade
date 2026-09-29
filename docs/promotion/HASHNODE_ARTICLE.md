# Three boundaries in ZephyrTrade

ZephyrTrade generates synthetic wind, weather and price tables, compares forecast and direct-offer strategies, and reconciles hypothetical revenue. Its Python and browser engines expose the assumptions so a researcher can inspect numerical agreement instead of relying on a dashboard alone.

## 1. The input boundary

Synthetic weather and prices enter through the supplied catalogue or local controls. Preserve their scope and source labels when adding examples.

## 2. The rule boundary

Forecast and offer strategies determine what the interface may display. The [engineering case study](../engineering/CASE_STUDY.md) names actual regression tests and files to inspect before changing that behavior.

## 3. The output boundary

Revenue and parity evidence are the user-facing result. A saved local action should remain distinguishable from external delivery or verification. Check error, reload and export behavior with fictional data before proposing a broader integration.

## Reproduce and review

Follow [the quick start](../../README.md), then [the current check report](../../QUALITY_REPORT.md). The next useful contribution is a small, reproducible improvement to this specific workflow. [Adjacent tools](../ALTERNATIVES.md) explain the scope tradeoffs.

Draft article; not published. Repository: https://github.com/mohammadrezwankhan/zephyrtrade.
