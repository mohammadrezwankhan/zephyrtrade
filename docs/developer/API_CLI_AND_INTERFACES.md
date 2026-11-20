# CLI, local HTTP and numerical interfaces

> Source snapshot: [`29abf5d8bd6f05b1f0c027d8753f4837840215dc`](https://github.com/mohammadrezwankhan/zephyrtrade/tree/29abf5d8bd6f05b1f0c027d8753f4837840215dc), inspected 20 November 2026. This is source documentation, not a new release, test run or deployment receipt.

## Installed command entry points

The source [pyproject.toml](../../pyproject.toml) declares: `zephyr-app` (local app), `zephyr-data` (synthetic data), `zephyr-preprocess`, `zephyr-phase2`, `zephyr-phase3`, and `zephyr-run` (full pipeline). Each maps to the corresponding `zephyrtrade.*:main`. `python -m zephyrtrade.app --no-browser` is a documented alternative. Consult `--help` for current command flags; no commands in this page have been executed as part of this docs PR.

## Local service

[app.py](../../src/zephyrtrade/app.py) binds `127.0.0.1`, validates the `Host` header against the loopback address/port, restricts static files to an explicit allowlist and exposes `GET /api/health`. The optimisation JSON handler parses a bounded request body with rejection of duplicate keys and non-finite JSON numbers. It is **not** a public multiuser API.

`optimize_payload` accepts required keys `capacity`, `da`, `up`, `down`, `scenarios` and optional `hours`, `probabilities`. It enforces positive capacity (0.1–10,000 MW), duration (0.25–24 h), 1–100 physical production scenarios, price ordering via the LP, and probabilities summing to one within 1e-7 (or defaults to equal weights). Returns `offer_mw`, `expected_revenue_dkk`, `interval_hours`, `solver` and `data_kind=user_assumptions_not_live`. The exact HTTP route/method and error status semantics should be read from the current handler before integration.

## Python contracts

- [optimize.py](../../src/zephyrtrade/optimize.py): `critical_fractile`, `solve_single_period_offer_lp`, `optimize_offers_from_residuals`, `perfect_foresight_offers`, `expected_scenario_revenue`.
- [evaluate.py](../../src/zephyrtrade/evaluate.py): `regression_metrics`, `realized_market_revenue`, `revenue_metrics`.
- Finite aligned vectors and nonnegative physical production are required. A one-interval regression returns undefined `r2=None`; capture is `None` when the benchmark is not positive. Do not silently coerce either to zero.

For an interface change, update consumer tests, browser parity fixtures and [unit/symbol definitions](../math-and-physics/PARAMETERS_AND_SYMBOLS.md).
