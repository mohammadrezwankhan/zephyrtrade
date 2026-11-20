# Worked examples and bounded labs

The following numerical observations were recorded on 2026-11-19 against source `29abf5d8bd6f05b1f0c027d8753f4837840215dc`, Python 3.12.14 and the scientific pins in `requirements-tested.txt`. They exercise synthetic mathematics and existing source utilities. They are neither live-market results nor a full replay of the archived three-year training run. Commands below assume the editable installation from [setup](SETUP_AND_REPRODUCIBILITY.md).

## 1. Settle a fixed quarter-hour offer

An offer is MW; duration converts the power discrepancy to MWh. For a fixed 10 MW offer, actual output 7 or 12 MW, DA/up/down 400/600/200 DKK/MWh and duration 0.25 h:

```python
from zephyrtrade.evaluate import realized_market_revenue

values = realized_market_revenue(
    actual_power_mw=[7, 12], offer_mw=[10, 10],
    day_ahead_price_dkk_mwh=[400, 400], up_regulation_price_dkk_mwh=[600, 600],
    down_regulation_price_dkk_mwh=[200, 200], interval_hours=0.25,
)
print(values)  # [550. 1100.]
print(0.4 * values[0] + 0.6 * values[1])  # 880.0 DKK
```

The first outcome pays `0.25 × (400×10 − 600×3) = 550`; the second pays `0.25 × (400×10 + 200×2) = 1100`. This example evaluates a chosen offer; it does not assert that 10 MW maximizes that distribution. Source: [src/zephyrtrade/evaluate.py:43–69](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/evaluate.py#L43-L69). Recorded lab 1 passed with both values and 880 DKK expectation.

## 2. Solve a fictional discrete offer

```python
from zephyrtrade.app import optimize_payload

result = optimize_payload({
    "capacity": 30, "da": 420, "up": 610, "down": 310,
    "hours": 1, "scenarios": [3, 7, 11], "probabilities": [],
})
print(result["offer_mw"], result["expected_revenue_dkk"])
# 7.0 2540.0
```

The critical quantile is `(420−310)/(610−310) = 0.36666666666666664`; equal weights select the second scenario. The adapter's objective includes the interval multiplier. A second recorded fixture used scenarios `[2,8,20]`, weights `[0.2,0.5,0.3]`, prices 400/600/200 and a quarter-hour interval: the result was 8 MW and 800 DKK. Change the duration and verify that revenue scales while the maximizing offer remains unchanged for a fixed positive duration. [src/zephyrtrade/app.py:47–85](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L47-L85) [src/zephyrtrade/optimize.py:97–168](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L97-L168)

## 3. Separate residual uncertainty from capacity classes

```python
from zephyrtrade.optimize import optimize_offers_from_residuals

offers = optimize_offers_from_residuals(
    point_forecasts_mw=[10, 10, 10], calibration_residuals_mw=[-3, 0, 4],
    day_ahead_price_dkk_mwh=[200, 400, 600], up_regulation_price_dkk_mwh=[600]*3,
    down_regulation_price_dkk_mwh=[200]*3, capacity_mw=30,
)
print(offers)  # [7. 10. 14.]
```

The price triples produce quantiles 0, 0.5 and 1. With the implementation's inverted empirical CDF, the selected residuals are −3, 0 and 4 MW. The result is clipped to farm capacity. These residuals are deliberately small invented teaching data; the actual Phase 2 pipeline calibrates on validation residuals, not held-out test outcomes. [src/zephyrtrade/optimize.py:171–211](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L171-L211) [src/zephyrtrade/phase2.py:500–579](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase2.py#L500-L579)

The separate capacity-bracket example used three classes over 30 MW with training powers `[1,5,12,18,23,29]`. Fitted representatives were `[3,15,26]` MW. Class probabilities `[0.2,0.5,0.3]` and quantile 0.5 selected class 1 and a 15 MW representative. Equal-width bin boundaries do not force midpoint representatives when the training bin contains data. [src/zephyrtrade/direct.py:22–135](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/direct.py#L22-L135)

## 4. Audit the bundled snapshot without retraining

The existing builder validates retained Phase 2/3 CSV alignment and recomputes each model's settlement values before emitting a snapshot. Call the existing function without overwriting the application bundle:

```python
from scripts.build_app import make_snapshot

snapshot = make_snapshot()
print(snapshot["quality"])
print(snapshot["sources"])
```

Run from the repository root. The fresh observation at 23:33:59–23:34:00 UTC on 2026-11-19 found 3,888 retained records between `2024-07-20T18:00:00Z` and `2024-12-31T22:00:00Z`, 3,941 possible hourly positions and 53 excluded positions. Nine model series yielded 34,992 checked revenue values with a maximum discrepancy of 0.0 DKK in this environment. This is a fresh recomputation; the original README's different tiny discrepancy remains its historical observation. [scripts/build_app.py:1–258](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/build_app.py#L1-L258)

| Input | SHA-256 of retained source CSV |
| --- | --- |
| `artifacts/phase2/test_predictions.csv.gz` | `082476e06d676874f92332b1347393f5eb5f35bb64f19750362f506050a4ae72` |
| `artifacts/phase3/test_direct_predictions.csv.gz` | `eff44a8cc642b8f3f2fcf542c42d28b81ed3540b7a03ca71e7327669f87afd5c` |

The generation timestamp `2026-07-13T17:42:44.545187+00:00` and total 319 removed negative-price hours come from retained provenance. The full original raw hourly tables are not present in this pinned tree, so this lab does not independently regenerate that historical exclusion count. Missing hours are not zero output and are not profit-free hours.

## 5. Rebuild a bounded experiment into a new directory

```sh
python scripts/smoke_research.py --output /tmp/zephyr-smoke-new
```

The existing script generates January–February 2023 data and runs Phase 2 plus reduced Phase 3. The observed run completed in about 50.3 seconds on this worker; this is not a performance guarantee. Reduced Phase 3 uses ten boosting iterations, seven leaves, three brackets and a smaller quantile grid. It does not certify the default 250-iteration three-year experiment. [scripts/smoke_research.py:1–75](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/smoke_research.py#L1-L75)

The new bounded run selected Lasso as its Phase 2 winner. Phase 3 still uses the hard-coded locally weighted offer column as its indirect comparator. Do not relabel that comparison as “the newly selected best Phase 2 model.” Preserve both outputs and compare their explicit model IDs. [src/zephyrtrade/phase3.py:283–333](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase3.py#L283-L333)

## 6. Inspect the teaching companion

The existing market lesson is an independent basis-point calculation: with base spread 30 bps, fees 10 bps, slippage 5 bps and notional USD 10,000 at time zero, edge is 15 bps and illustrative P&L is USD 15. Increasing slippage to 25 bps makes edge −5 bps and P&L −USD 5; at USD 40,000 notional this becomes −USD 20. These are per-opportunity values, not cumulative wind settlement. Its four lesson modules and eight numeric checks are source-inspected here; a new interactive browser acceptance run was blocked before page load. [docs/index.html:160–348](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/docs/index.html#L160-L348)

## What this lab set leaves open

The existing Python test suite passed 255 tests plus 54 subtests, native Node tests passed 58 distinct cases across recorded subsets, and the existing 120-case cross-language parity check stayed below its 1e−6 DKK threshold. These do not establish accessibility, native persistence, browser sandbox behavior, market execution, out-of-sample commercial returns or exact reproducibility on every supported interpreter. The [evidence ledger](../maintainer/VERIFICATION_EVIDENCE_LEDGER.md) retains the failed setup attempts and browser limitation alongside the passes.
