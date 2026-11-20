# Parameters, symbols and units

> Source snapshot: [`29abf5d8bd6f05b1f0c027d8753f4837840215dc`](https://github.com/mohammadrezwankhan/zephyrtrade/tree/29abf5d8bd6f05b1f0c027d8753f4837840215dc), inspected 20 November 2026. This is source documentation, not a new release, test run or deployment receipt.

| Symbol or API field | Meaning | Unit / source contract |
| --- | --- | --- |
| `a`, `actual_power_mw` | Actual or simulated generated power | MW, nonnegative and capacity-bounded |
| `q`, `offer_mw` | Day-ahead offered power | MW, within [0, capacity] for LP |
| `capacity`, `capacity_mw` | Physical nameplate upper bound | MW, positive |
| `p_da`, `da` | Day-ahead market price | DKK/MWh |
| `p_up`, `up` | Price charged for shortfall | DKK/MWh |
| `p_down`, `down` | Price paid for surplus | DKK/MWh |
| `h`, `hours`, `interval_hours` | Delivery interval duration | h; app accepts 0.25–24 |
| `s_i`, `surplus_mw` | Production above offered power | MW, nonnegative |
| `t_i`, `shortfall_mw` | Offered power above production | MW, nonnegative |
| `w_i`, `probabilities` | Scenario weighting | Dimensionless, sum approximately 1 |
| `alpha`, `critical_fractile` | Optimal scenario-quantile index | Dimensionless [0,1] |
| `expected_revenue_dkk` | Weighted expected settlement | DKK per chosen interval |
| `total_absolute_imbalance_mwh` | Duration-weighted absolute imbalance | MWh |
| `rmse_mw`, `mae_mw` | Forecast error metrics | MW |
| `r2` | Forecast determination coefficient | Dimensionless or `None` |
| `revenue_capture_pct` | Revenue divided by positive oracle total | Percent or `None` |

Source locators: [app request bounds](../../src/zephyrtrade/app.py), [optimisation arrays](../../src/zephyrtrade/optimize.py), [evaluation metrics](../../src/zephyrtrade/evaluate.py), [project runtime declaration](../../pyproject.toml). Input validation can differ between the local JSON wrapper and direct Python calls; do not generalise wrapper bounds to all functions.

Timezones, retained hourly records, and timestamp filters belong to [data generation/preprocessing](../../src/zephyrtrade/data_loader.py) rather than these per-interval equations. Negative-price policies and data vintage require explicit documentation when comparing outcomes.
