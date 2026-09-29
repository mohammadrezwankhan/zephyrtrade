# ZephyrTrade: ML-Driven Wind Energy Market Optimizer

ZephyrTrade is a reproducible research repository for optimizing the hourly
offering strategy of a wind farm in Bornholm, Denmark (the DK2 bidding zone).
It compares an indirect workflow that predicts wind production before solving
a trading optimization problem with a direct workflow that predicts the bid
itself.

The four-phase repository is complete. It includes a deterministic four-farm
data pipeline, leakage-safe features, a stochastic trading linear program, six
wind-power models plus a persistence baseline, revenue backtesting,
regularization and clustering analysis, direct continuous and discrete offer
learning, automated tests, continuous integration, and a final academic report.

## Research questions

1. Which regression family produces the most useful wind forecast when value
   is measured by realized market revenue rather than forecast error alone?
2. Can local models discovered with clustering outperform a single global
   regression model?
3. Does direct strategy learning outperform the conventional
   predict-then-optimize pipeline?
4. How do forecast accuracy, bid feasibility, and realized revenue trade off?

## Model architecture

- **Model 1 - indirect trading:** climate and lagged production features feed
  linear, nonlinear, locally weighted, Ridge, Lasso, and clustered regressors.
  Their wind forecasts feed a day-ahead/balancing-market linear program.
- **Model 2 - direct trading:** the same information set, augmented only by
  variables available at bid time, predicts either a continuous offer or a
  discrete bid bracket learned from perfect-foresight optimal decisions.
- **Evaluation:** models are compared on RMSE, MAE, R-squared, realized revenue,
  revenue regret, and operational feasibility.

## Repository layout

```text
ZephyrTrade/
|-- data/
|   |-- raw/                  # Generated source tables (gitignored)
|   `-- processed/            # Features, splits, scaler, schema (gitignored)
|-- docs/
|   |-- figures/              # Versioned publication figures
|   `-- report.md             # Final academic report
|-- src/zephyrtrade/
|   |-- data_loader.py        # Phase 1 data synthesis and validation
|   |-- preprocessing.py      # Phase 1 features, split, and scaling
|   |-- models.py             # OLS, gradient descent, LOESS, clustering
|   |-- optimize.py           # Trading LP and exact quantile solution
|   |-- evaluate.py           # Forecast and realized-revenue metrics
|   |-- direct.py             # Direct target/bracket decision utilities
|   |-- phase2.py             # Reproducible indirect-model experiment
|   |-- phase3.py             # Direct-model selection and comparison
|   `-- pipeline.py           # One-command workflow and run manifest
|-- tests/                    # Deterministic pipeline tests
|-- CONTRIBUTING.md
|-- CHANGELOG.md
|-- pyproject.toml
`-- requirements.txt
```

## Data strategy and provenance

The default path is fully synthetic so that every experiment is deterministic,
offline-capable, and free of API credentials. It creates four **synthetic site
proxies** around Bornholm; their names and capacities do not describe real
commercial assets. Weather is generated with correlated seasonal and
autoregressive processes, production follows a turbine power curve with
availability effects, and prices reproduce diurnal, seasonal, wind-cannibalized,
spike, and negative-price regimes.

The schema is intentionally aligned with public data that can replace the
synthetic tables in a sensitivity study:

- [Energinet Energi Data Service API](https://api.energidataservice.dk/index.html)
  for Danish market datasets;
- [Energinet Elspot Prices](https://www.energidataservice.dk/tso-electricity/Elspotprices)
  for the historical hourly DK2 series (the dataset is discontinued for new
  observations, so its metadata must be checked before use);
- [Energinet Imbalance Price](https://www.energidataservice.dk/tso-electricity/ImbalancePrice)
  for imbalance-price data, subject to retrieval-time schema checks;
- [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/) for European
  day-ahead prices, balancing information, and aggregated generation; and
- [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api)
  for hourly reanalysis fields including 100 m wind speed, temperature,
  humidity, and pressure.

The generated tables use UTC timestamps. Calendar features are derived in
`Europe/Copenhagen`, which handles daylight-saving time without ambiguous local
timestamps. All rows containing a negative day-ahead, upward-regulation, or
downward-regulation price are removed from the market table and recorded in the
provenance manifest.

## Phase 1 data contract

Running the data command produces:

- `farm_metadata.csv`: farm identifier, site-proxy coordinates, and capacity;
- `wind_power.csv.gz`: hourly power, capacity, and availability for four farms;
- `climate.csv.gz`: farm-level weather and climate variables;
- `market_prices.csv.gz`: DK2 price series after negative-price filtering; and
- `provenance.json`: configuration, source references, row counts, and filter
  statistics.

Preprocessing selects `bornholm_ronne_coastal` by default. It creates an exact
24-hour power lag, trailing 168-hour production quantiles at 0.05, 0.50, and
0.95, forecast-time climate variables, and cyclic calendar/direction features.
It retains prices for later revenue evaluation but does not use realized prices
to predict wind power.

## Quick start

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the full default experiment with one command. It may take several minutes
because locally weighted regression and the direct-model search are fitted from
scratch.

```bash
python -m zephyrtrade.pipeline \
  --start 2022-01-01 \
  --end 2025-01-01 \
  --seed 42
```

The command writes a run manifest containing configuration, runtime versions,
principal output paths, and SHA-256 hashes to `artifacts/run_manifest.json`.
The following commands expose the same stages for partial reruns.

Generate three years of hourly source data. The end timestamp is exclusive.

```bash
python -m zephyrtrade.data_loader \
  --start 2022-01-01 \
  --end 2025-01-01 \
  --output-dir data/raw \
  --seed 42
```

Build the selected-farm feature matrix and chronological splits.

```bash
python -m zephyrtrade.preprocessing \
  --raw-data-dir data/raw \
  --output-dir data/processed \
  --farm-id bornholm_ronne_coastal
```

The default allocation is 70% training, 15% validation, and 15% testing,
ordered strictly by timestamp. `StandardScaler` is fit on the training split
only, then applied unchanged to validation and test data.

Run the quality checks:

```bash
python -m pytest -W error
python -m ruff check src tests
python -m ruff format --check src tests
```

## Phase 2 indirect-model experiment

Run the complete forecast-then-optimize backtest:

```bash
python -m zephyrtrade.phase2 \
  --processed-data-dir data/processed \
  --output-dir artifacts/phase2 \
  --figure-dir docs/figures
```

On the seeded three-year synthetic dataset, locally weighted linear regression
is the leading indirect model: test RMSE is 1.876 MW and realized test revenue
is DKK 18.497 million, equal to 97.98% of the perfect-foresight benchmark.
Polynomial OLS ranks second. Three k-means regimes improve on global linear OLS
but do not outperform the nonlinear models. Full assumptions, equations, tuning
paths, coefficient analysis, and rankings are in the academic report.

## Phase 3 direct-strategy experiment

Run target engineering, direct model selection, and the shared-test comparison:

```bash
python -m zephyrtrade.phase3 \
  --processed-data-dir data/processed \
  --phase2-prediction-path artifacts/phase2/test_predictions.csv.gz \
  --output-dir artifacts/phase3 \
  --figure-dir docs/figures
```

Under the maintained no-arbitrage price order, the deterministic
perfect-foresight LP label equals realized production. The implementation
verifies this analytical result against explicit LP solves. On the seeded test
period, continuous direct regression earns DKK 18.761 million and captures
99.38% of perfect-foresight revenue. Fifteen-bracket classification earns DKK
18.672 million, while the best indirect model earns DKK 18.497 million. The
report explains why these gains are conditional on the synthetic experiment,
the degenerate perfect-foresight target, and unequal learner families.

## Final comparison

All strategies use the same 3,888-hour chronological test period.

| Strategy | Offer RMSE (MW) | Revenue (million DKK) | Capture (%) | Regret (million DKK) |
|---|---:|---:|---:|---:|
| Perfect foresight | 0.000 | 18.879 | 100.000 | 0.000 |
| Direct continuous regression | 0.781 | 18.761 | 99.375 | 0.118 |
| Direct bid-bracket classification | 0.975 | 18.672 | 98.902 | 0.207 |
| Indirect locally weighted plus LP | 1.965 | 18.497 | 97.976 | 0.382 |

The complete methodology, equations, coefficient analysis, figures, validity
threats, and deployment design are in the [academic report](docs/report.md).

## Reproducibility and research limits

- A fixed seed makes every generated numeric table reproducible.
- The end-to-end manifest records runtime metadata and hashes core summaries.
- Source tables remain unscaled; processed files preserve both the original
  feature table and scaled model matrices.
- Synthetic results demonstrate the method, not the profitability of a real
  Bornholm asset. Production deployment requires licensed asset telemetry,
  point-in-time weather forecasts, current market settlement rules, transaction
  costs, and an independent risk review.
- Filtering negative prices follows the supplied project specification. It can
  bias the evaluated regime and must be reported as a scope choice rather than
  interpreted as normal market practice.

## License

MIT. Public datasets remain subject to their providers' terms and licenses.
