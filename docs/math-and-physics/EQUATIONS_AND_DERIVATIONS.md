# Equations and derivations

This is an interpretation of the implemented model at `29abf5d8bd6f05b1f0c027d8753f4837840215dc`, reviewed 19 November 2026. Equations below separate literal source behavior from explanatory derivations. No measured wind-farm calibration, current market-rule assessment or trading recommendation follows from these calculations. [Symbols](PARAMETERS_AND_SYMBOLS.md) · [Limits](ASSUMPTIONS_AND_LIMITS.md) · [Examples](../developer/WORKED_EXAMPLES_AND_LABS.md).

## 1. One-interval asymmetric settlement

Let $b$ be offered power, $y$ actual power, $d$ the day-ahead price, $u$ the shortfall/up-regulation price, $\ell$ the surplus/down-regulation price, and $\Delta t>0$ the duration in hours. The implemented settlement formula is

$$R(b,y)=\Delta t\left[db+\ell(y-b)^+-u(b-y)^+\right],\qquad x^+=\max(x,0).$$

MW × DKK/MWh × hours gives DKK. Positive `actual - offer` is a surplus; negative imbalance is a shortfall. `realized_market_revenue` validates finite aligned nonempty vectors and positive duration, but **does not** impose price ordering, nonnegative MW or capacity. The browser's lower-level `revenue` additionally rejects negative MW. Interpretation as a physically feasible offer requires the appropriate caller's contract. Sources: [src/zephyrtrade/evaluate.py:43–69](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/evaluate.py#L43-L69), [src/zephyrtrade/web/engine.js:32–40](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/engine.js#L32-L40).

For offer 10 MW, duration 0.25 h, prices 400/600/200 DKK/MWh and actual production 7 or 12 MW, the receipts are 550 and 1,100 DKK. With probabilities 0.4/0.6 the fixed-offer expectation is 880 DKK. This arithmetic verifies a specified offer, without asserting it is optimal. The existing fixture and fresh documentation example agree. Source: [tests/fixtures/settlement-quarter-hour-v1.json](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/tests/fixtures/settlement-quarter-hour-v1.json).

## 2. Stochastic linear program

For scenarios $y_i$, normalized nonnegative probabilities $p_i$ and capacity $C>0$, the intended one-hour program is

$$\max_{b,s_i,h_i}\; db+\sum_i p_i(\ell s_i-u h_i)$$
$$b+s_i-h_i=y_i,\quad 0\le b\le C,\quad s_i,h_i\ge0.$$

There are $1+2n$ variables. The implementation minimizes the negative objective with SciPy `linprog(method="highs")`, exact equality rows and explicit bounds. It requires finite nonempty aligned vectors, physical scenarios and $\ell\le d\le u$ with $u>\ell$. It supplies no custom solver tolerances or duration argument; the reported low-level objective therefore assumes one hour. The HTTP API multiplies the result by its supplied duration. Source: [src/zephyrtrade/optimize.py:97–168](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L97-L168), [src/zephyrtrade/app.py:47–84](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L47-L84).

**Observed library boundary debt:** the direct LP accepts probability sums using NumPy's default `isclose` without normalizing them. Its day-ahead term is unweighted, while `expected_scenario_revenue` weights the entire interval expression. A source-only probe with `scenarios=[10]`, `probabilities=[1.000005]`, capacity 20 and prices 50/80/30 returned 500 DKK from the LP and 500.0025 DKK from the evaluator at the same 10 MW offer. The API rejected that input at its per-probability bound; API and browser paths also enforce a tighter sum tolerance and normalize accepted weights. This is a low-level interface discrepancy, not a demonstrated failure of normal unit-mass pipeline inputs. See debt `ZT-N01` and the [evidence ledger](../maintainer/VERIFICATION_EVIDENCE_LEDGER.md). Sources: [src/zephyrtrade/optimize.py:117–168](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L117-L168), [src/zephyrtrade/optimize.py:214–255](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L214-L255), [src/zephyrtrade/app.py:61–77](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L61-L77), [src/zephyrtrade/web/engine.js:63–87](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/engine.js#L63-L87).

## 3. Why a quantile is optimal

The following is an **explanatory derivation for unit probability mass**, the ordered-price model and a fixed positive duration. Away from atoms, differentiating expected revenue gives

$$\frac{1}{\Delta t}\frac{d\mathbb E[R]}{db}=d-\ell-(u-\ell)F_Y(b).$$

The slope decreases with $b$. Hence the objective is concave and a quantile at

$$\alpha=\frac{d-\ell}{u-\ell}\in[0,1]$$

is optimal, subject to capacity. At an atom, the subgradient brackets zero when $F_Y(b^-)\le\alpha\le F_Y(b)$. Flat segments create multiple equally good offers. At $d=\ell$ or $d=u$, endpoint ties can extend beyond the minimum/maximum scenario toward the capacity bounds. Multiplying the entire objective by positive duration changes DKK but not the optimizer.

`critical_fractile` implements this ratio. The browser actually evaluates **all unique breakpoints** `{0, capacity, ...scenarios}` and chooses the first strict maximum after sorting, so exact ties choose the lowest breakpoint. It does not implement the native LP or call a quantile library. HiGHS can choose a different equal-value offer. The parity script tests objective difference strictly below $10^{-6}$ DKK; the UI verifier rejects differences greater than $10^{-6}$ DKK and allows an offer-bound tolerance of $10^{-8}$ MW. Those two comparisons differ at the exact threshold. Sources: [src/zephyrtrade/optimize.py:49–61](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L49-L61), [src/zephyrtrade/web/engine.js:60–99](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/engine.js#L60-L99), [scripts/verify_engines.py:93–169](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/verify_engines.py#L93-L169).

For a known production value $y\in[0,C]$, $b=y$ is an optimum under the maintained ordering. It is an oracle because it uses realized production. Equality prices can make it nonunique. `perfect_foresight_offers` returns the validated actual vector; Phase 3 audits up to 25 strictly ordered training rows with explicit one-scenario LPs. Sources: [src/zephyrtrade/optimize.py:64–94](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L64-L94), [src/zephyrtrade/phase3.py:335–366](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase3.py#L335-L366).

## 4. Residual offers and direct brackets

Phase 2 takes validation errors $e_j=y_j-\hat y_j$ and applies

$$b_t=\operatorname{clip}\left(\hat y_t+Q^{\mathrm{inverted\_cdf}}_{\alpha_t}(e),0,C_t\right).$$

The residual sample is equiprobable and shared across test observations. It is not a demonstrated conditional uncertainty model. NumPy's `inverted_cdf` convention matters at finite-sample boundaries; do not silently replace it with linear interpolation. The ratio uses realized test prices ex post. Sources: [src/zephyrtrade/optimize.py:171–211](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L171-L211), [src/zephyrtrade/phase2.py:500–578](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase2.py#L500-L578).

`CapacityBracketEncoder` divides `[0,C]` into equal-width brackets. Values exactly at internal edges enter the upper class. A class representative is its training median, or the interval midpoint when the class is empty. `probability_quantile_classes` sorts class IDs, validates/normalizes probability rows, and selects the first cumulative probability reaching the chosen quantile with its $10^{-12}$ comparison allowance. This is not argmax classification. A selected decision quantile is tuned on inner-holdout revenue; it is not necessarily each interval's price-dependent critical fractile. Sources: [src/zephyrtrade/direct.py:22–135](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/direct.py#L22-L135), [src/zephyrtrade/phase3.py:221–280](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase3.py#L221-L280).

## 5. Forecast estimators

| Estimator | Implemented mathematical operation | Scope and boundary |
| --- | --- | --- |
| Closed-form linear | `numpy.linalg.lstsq` on `[1, X]`; objective $\frac{1}{2n}\|X_a\theta-y\|^2$ | Least-squares factorization; no explicit normal-equation inversion |
| Gradient descent demonstration | $\theta\leftarrow\theta-\eta(H\theta-g)$, $H=X_a^TX_a/n$, $g=X_a^Ty/n$ | Default $\eta=1/\lambda_{\max}(H)$; step must be in $(0,1/L]$; records convergence flag and iteration cap |
| Polynomial OLS | `PolynomialFeatures(include_bias=False)` then linear regression | Degree 2 by default; no internal feature scaler in this OLS pipeline |
| Polynomial Ridge/Lasso | Polynomial features, training scaler, sklearn penalty model | Alpha selected by training time-series folds; Lasso CV retry can increase iteration cap |
| Locally weighted linear | Query-centered local plane with tricube weights and Ridge stabilization | Nearest-neighbor radius, weights floored at $10^{-10}$, unpenalized intercept; solve with least-squares fallback |
| Clustered Ridge | K-means on selected regime features, local Ridge per sufficiently populated cluster | Global Ridge fallback when a cluster has fewer than `n_features + 2` observations |

For local regression, $r$ is the farthest-neighbor distance (at least machine epsilon), $w_i=\max(10^{-10},[1-(\min(d_i/r,1))^3]^3)$, and the fitted query-centered intercept is the prediction. Phase 2 clips model predictions to `[0,C]` before forming validation residuals and test offers. Source: [src/zephyrtrade/models.py:18–301](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/models.py#L18-L301), [src/zephyrtrade/phase2.py:152–316](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase2.py#L152-L316).

Phase 3 uses histogram gradient boosting: squared-error or quantile-loss regression, and log-loss classification. Economic sample weights are `(up - down) / mean(up - down)` on the fitting period. Selected models refit on all training rows, with early stopping disabled. Its inputs are the same 15 features; realized prices affect weights and historical selection, not the inference feature vector. Sources: [src/zephyrtrade/phase3.py:94–280](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase3.py#L94-L280), [src/zephyrtrade/phase3.py:532–709](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase3.py#L532-L709).

## 6. Metrics and temporal meaning

$$\mathrm{RMSE}=\sqrt{\frac1n\sum_i(y_i-\hat y_i)^2},\quad \mathrm{MAE}=\frac1n\sum_i|y_i-\hat y_i|.$$
$$\mathrm{capture}=100\frac{\sum_i R_i}{\Delta t\sum_i d_i y_i},\quad \mathrm{regret}=\Delta t\sum_i d_i y_i-\sum_iR_i.$$
$$\mathrm{absolute\ imbalance\ (MWh)}=\Delta t\sum_i|y_i-b_i|.$$

Capture is `None`/`null` when its denominator is nonpositive. One-observation $R^2$ is undefined. For two or more observations, Python uses sklearn's $R^2$; the browser explicitly returns 1 for an exactly predicted constant target and 0 otherwise. The browser arena evaluates **offer** error. Phase 2's forecast table evaluates **power forecast** error before residual-based optimization. Comparing those RMSE values as though they measure the same object is invalid. Sources: [src/zephyrtrade/evaluate.py:28–114](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/evaluate.py#L28-L114), [src/zephyrtrade/web/engine.js:42–58](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/engine.js#L42-L58), [src/zephyrtrade/phase2.py:500–578](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase2.py#L500-L578).

Dashboard charts aggregate means of available hourly values when more than 180 records are selected. Cumulative charts use included-hour cumulative totals, sampled at each displayed group's end. Missing hours are not zero-filled; a daily view can conceal an intraday gap visually while retaining the correct included-hour total. Source: [src/zephyrtrade/web/app.js:309–347](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L309-L347).

## 7. Synthetic generator and independent teaching proxy

The generator uses seeded autoregressive weather drivers, a generic turbine curve with cut-in 3 m/s, rated speed 12 m/s and cut-out 25 m/s, site multipliers, wake efficiency, stochastic derating and measurement noise. Its cubic ramp is $(v^3-3^3)/(12^3-3^3)$ on $3\le v<12$, rated fraction 1 on $12\le v\le25$, and zero otherwise before noise/clipping. This is a synthetic observation generator, not an aerodynamic certification model. Public-provider URLs in the provenance are references; the generator makes no provider download. Sources: [src/zephyrtrade/data_loader.py:112–358](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/data_loader.py#L112-L358), [data/raw/provenance.json](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/data/raw/provenance.json).

The `docs/index.html` **markets** companion instead computes

$$s(t)=b_0+12\sin(2\pi t/12)+5\sin(2\pi t/5),\quad e(t)=s(t)-f-\sigma,$$
$$P(t)=N_{\mathrm{USD}}e(t)/10000,\qquad K=N_{\mathrm{USD}}(f+\sigma)/10000.$$

Here $t$ is the selected model time in hours; $P(t)$ is one hypothetical opportunity, not cumulative P&L. The page defaults are 30 bps spread, 10 bps fees, 5 bps slippage and USD 10,000, overriding the generic shared runtime's 35/15/8 bps defaults. The page selects four controls and four modules. Its shared library includes other teaching-model branches, which are not this site's wind-settlement engine. Sources: [docs/lesson-config.json](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/docs/lesson-config.json), [docs/index.html:160–348](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/docs/index.html#L160-L348), [docs/index.html:359–379](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/docs/index.html#L359-L379).

## Upstream context

SciPy's [linprog documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html) describes the minimization form and solver result fields. Scikit-learn's [TimeSeriesSplit documentation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) explains expanding ordered folds and notes equal spacing when comparing equal-duration folds. ZephyrTrade splits the retained **rows** after filtering, so equal row counts need not mean equal calendar durations. These upstream pages were inspected on 19 November 2026; current manuals can differ from the pinned runtime and do not replace its source/tests.
