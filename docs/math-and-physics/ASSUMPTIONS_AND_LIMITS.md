# Model assumptions and evidence limitations

> Source snapshot: [`29abf5d8bd6f05b1f0c027d8753f4837840215dc`](https://github.com/mohammadrezwankhan/zephyrtrade/tree/29abf5d8bd6f05b1f0c027d8753f4837840215dc), inspected 20 November 2026. This is source documentation, not a new release, test run or deployment receipt.

## Mathematical applicability

The two-price calculation assumes one interval with the specified up/down settlement prices, known or sampled production, and no-arbitrage price ordering `p_down ≤ p_da ≤ p_up`, with `p_up > p_down`. The scenario LP treats its supplied weights as the probability model; empirical-residual quantiles depend on representativeness and the calibration period. The perfect-foresight benchmark is a retrospective oracle, not a strategy available at bid time.

The synthetic input generator uses plausible *illustrative* Bornholm proxies; even when external data-source URLs are named, the default generated data are not observed current wholesale prices, weather measurements or metered physical output. Backtests may filter negative-price hours, and missing timestamps alter comparability. Inspect generation, filtering, chronology and sample selection.

## Execution and publication boundaries

The local server deliberately binds loopback and checks Host, JSON shape and concurrency. The separately built static application does not enable market orders, brokerage, live provider feeds, credentials, shared accounts or real-time optimiser inference. A successful web deployment, screenshot, CI check or SciPy-vs-JavaScript objective comparison does not validate market calibration, profit, grid compliance, operational security or external datasets.

## Appropriate use

Use only synthetic or appropriately licensed input, document forecast vintage, calibration/test separation, time resolution, costs, capacity and local jurisdictional settlement rules. A live-market application would require a separate design, permissions, security review, risk owner, evidence and deployment architecture. See [historical quality evidence](../../QUALITY_REPORT.md) and [security policy](../../SECURITY.md).
