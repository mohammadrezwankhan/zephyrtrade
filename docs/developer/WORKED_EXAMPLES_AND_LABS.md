# Worked research examples and labs

> Source snapshot: [`29abf5d8bd6f05b1f0c027d8753f4837840215dc`](https://github.com/mohammadrezwankhan/zephyrtrade/tree/29abf5d8bd6f05b1f0c027d8753f4837840215dc), inspected 20 November 2026. This is source documentation, not a new release, test run or deployment receipt.

All numbers below are **new, fictional arithmetic examples**, not measured site data, repository test receipts or investment advice. Use the [implemented equations](../math-and-physics/EQUATIONS_AND_DERIVATIONS.md) and source to reproduce them.

## Lab 1 — Reconcile an hourly day-ahead offer

Set offer `q = 10 MW`, interval `h = 1 h`, day-ahead `p_da=50 DKK/MWh`, down-regulation `p_down=20 DKK/MWh`, up-regulation `p_up=80 DKK/MWh`, all synthetic. In case A, actual generation is 8 MW, so shortfall is 2 MWh and revenue is `50×10 − 80×2 = 340 DKK`. In case B, actual generation is 12 MW, so surplus is 2 MWh and revenue is `50×10 + 20×2 = 540 DKK`. With equal probabilities, the expected revenue at this fixed offer is **440 DKK**.

The price-order contract holds: `20 ≤ 50 ≤ 80`; the empirical critical fractile is `(50−20)/(80−20)=0.5`. Check the solver choice separately using `solve_single_period_offer_lp`; do not infer its tie-breaking from this fixed-offer arithmetic.

## Lab 2 — Express physical capacity as a constraint

Using the example above, capacity `C=15 MW` permits actual 8/12 MW and offer 10 MW. A production scenario of 16 MW violates the implemented physical capacity limit and should be rejected before optimisation. Inspect [optimize.py](../../src/zephyrtrade/optimize.py) and add a focused test if changing validation.

## Lab 3 — Distinguish forecast error from revenue

Calculate `MAE=mean(|actual−forecast|)` and `RMSE=sqrt(mean((actual−forecast)^2))` in MW with `regression_metrics`. Settlement revenue additionally depends on the offer, prices and interval hours; a forecast with better RMSE does not necessarily generate better hypothetical revenue under asymmetric penalties. A one-row sample has undefined R².

## Lab 4 — Verify browser and SciPy agreement

With Node.js and installed Python dependencies, run:

```sh
node --test tests/browser/engine.test.cjs
python scripts/verify_engines.py
```

The verifier defines 120 seeded cases and compares browser objectives to the Python HiGHS LP with a difference threshold of 1e-6 DKK; **run it yourself** to obtain candidate-specific evidence. The historical [quality report](../../QUALITY_REPORT.md) describes prior source revisions.

## Lab 5 — Inspect reproducibility

Run `zephyr-run --help`, choose a safe scratch output directory and record seed, date interval, farm ID, filtered prices, Git SHA and manifest digests. No synthetic wind result establishes operational forecast accuracy or live market access.
