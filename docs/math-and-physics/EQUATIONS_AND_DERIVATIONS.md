# Settlement equations and optimisation derivation

> Source snapshot: [`29abf5d8bd6f05b1f0c027d8753f4837840215dc`](https://github.com/mohammadrezwankhan/zephyrtrade/tree/29abf5d8bd6f05b1f0c027d8753f4837840215dc), inspected 20 November 2026. This is source documentation, not a new release, test run or deployment receipt.

**Source:** [optimisation](../../src/zephyrtrade/optimize.py), [evaluation](../../src/zephyrtrade/evaluate.py), and the [browser numerical engine](../../src/zephyrtrade/web/engine.js).

## Two-price single-interval revenue

Let `q` be the offer in MW, `a` actual wind generation in MW, `h` duration in hours, and `p_da,p_up,p_down` prices in DKK/MWh. Define `surplus=max(a−q,0)` and `shortfall=max(q−a,0)` in MW. Then:

```text
revenue_DKK = h × [p_da × q + p_down × surplus − p_up × shortfall]
```

The implementation requires finite values; offer/physical generation must satisfy applicable capacity constraints and `p_down ≤ p_da ≤ p_up` with `p_up > p_down` for the optimisation formulation. Multiply the power terms by duration to obtain MWh before combining with DKK/MWh prices.

## Scenario LP

For production scenarios `a_i` with weights `w_i ≥ 0` and `sum(w_i)=1`, choose `0 ≤ q ≤ C` plus `s_i,t_i ≥ 0` so that `q + s_i − t_i = a_i`. Maximise:

```text
p_da × q + Σ_i w_i (p_down × s_i − p_up × t_i)
```

[solve_single_period_offer_lp](../../src/zephyrtrade/optimize.py) minimises the negative of this expression with `scipy.optimize.linprog(..., method="highs")`. For an interval other than 1 h, the [app wrapper](../../src/zephyrtrade/app.py) multiplies the solver's expected value by `hours`. The LP may have multiple optimal offers under ties; objective equality does not imply identical selected offer.

## Empirical critical fractile

Under the validated ordering, an empirical scenario quantile at

```text
alpha = (p_da − p_down) / (p_up − p_down)
```

maximises the expected piecewise linear revenue. The code clips `alpha` to [0,1] and uses `numpy.quantile(..., method="inverted_cdf")` for residuals. Forecast plus empirical residual quantile is clipped to the physical interval [0, capacity]. This is a *scenario distribution assumption*, not a calibrated probability of field output.

## Forecast and economic metrics

`RMSE_MW = sqrt(mean((actual−predicted)^2))`; `MAE_MW = mean(abs(actual−predicted))`. The perfect-foresight oracle uses actual generation as offer under the model assumptions; `regret_DKK = oracle_revenue − realized_revenue`. `capture_pct = 100×realized/oracle` is defined only if the oracle total is positive. R² is intentionally undefined for a one-interval sample.

Worked numerical substitution is in [the labs](../developer/WORKED_EXAMPLES_AND_LABS.md). These synthetic economic formulas omit actual venue fee structures, gate closures and real trading constraints.
