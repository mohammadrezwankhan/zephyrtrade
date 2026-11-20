# APIs, commands and browser controls

This contract describes source `29abf5d8bd6f05b1f0c027d8753f4837840215dc`. The six installed commands, low-level numerical functions, local HTTP adapter, native dashboard and teaching companion have different validation and time conventions. See [equations](../math-and-physics/EQUATIONS_AND_DERIVATIONS.md) before reusing a result outside its original surface.

## Installed commands

Run these in the environment from [setup](SETUP_AND_REPRODUCIBILITY.md). `--help` is provided by each command's `argparse` parser. A command's path options can overwrite existing experiment outputs; use a new output directory. Advanced dataclass options are Python interfaces, not invented CLI flags. Entry-point registration: [pyproject.toml:44–50](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/pyproject.toml#L44-L50).

| Command | Explicit options and defaults | Source |
| --- | --- | --- |
| `zephyr-app` | `--port 8765`, `--no-browser` (off); port must be 1024–65535 | [src/zephyrtrade/app.py:317–349](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L317-L349) |
| `zephyr-data` | `--start 2022-01-01`, `--end 2025-01-01` (exclusive), `--seed 42`, `--negative-price-probability 0.012`, `--output-dir data/raw` | [src/zephyrtrade/data_loader.py:506–553](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/data_loader.py#L506-L553) |
| `zephyr-preprocess` | `--raw-data-dir data/raw`, `--output-dir data/processed`, `--farm-id bornholm_ronne_coastal`, `--train-fraction 0.70`, `--validation-fraction 0.15` | [src/zephyrtrade/preprocessing.py:338–377](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/preprocessing.py#L338-L377) |
| `zephyr-phase2` | `--processed-data-dir data/processed`, `--output-dir artifacts/phase2`, `--figure-dir docs/figures`, `--local-neighbors 192` | [src/zephyrtrade/phase2.py:771–810](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase2.py#L771-L810) |
| `zephyr-phase3` | `--processed-data-dir data/processed`, `--phase2-prediction-path artifacts/phase2/test_predictions.csv.gz`, `--output-dir artifacts/phase3`, `--figure-dir docs/figures` | [src/zephyrtrade/phase3.py:712–745](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase3.py#L712-L745) |
| `zephyr-run` | generation dates, seed and negative-price probability above; `--farm-id bornholm_ronne_coastal`, `--raw-data-dir data/raw`, `--processed-data-dir data/processed`, `--artifact-dir artifacts`, `--figure-dir docs/figures` | [src/zephyrtrade/pipeline.py:174–217](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/pipeline.py#L174-L217) |

`zephyr-run` generates new synthetic data, then preprocesses and runs both experiments. It does not download measured data or load a pretrained model. `scripts/smoke_research.py --output PATH` is a separate repository utility with reduced Phase 3 settings and a refusal to reuse any existing output path. [src/zephyrtrade/pipeline.py:91–172](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/pipeline.py#L91-L172) [scripts/smoke_research.py:1–75](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/smoke_research.py#L1-L75)

## Local HTTP adapter

`zephyr-app --no-browser` binds `127.0.0.1`. Its allow-listed static resources are `/`, `/index.html`, `/styles.css`, `/engine.js`, `/app.js` and `/snapshot.js`; `/favicon.ico` returns 204. `GET /api/health` reports service identity, and `POST /api/optimize` executes the SciPy LP. `HEAD` delegates to the GET path without the body. The exact POST path matters: this is not a general REST router. [src/zephyrtrade/app.py:22–35](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L22-L35) [src/zephyrtrade/app.py:199–315](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L199-L315)

```sh
curl --fail-with-body http://127.0.0.1:8765/api/optimize \
  -H 'Content-Type: application/json' \
  --data '{"capacity":30,"da":420,"up":610,"down":310,"hours":1,"scenarios":[3,7,11],"probabilities":[]}'
```

The fictional fixture has an optimal 7 MW offer and 2540 DKK expected one-hour revenue. The same native payload function was executed in the dated lab; this printed `curl` command is the reproducible transport equivalent, not a claim of a newly captured curl session. The existing HTTP test suite separately passed in the source run. [src/zephyrtrade/app.py:47–85](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L47-L85)

| Payload field | Required/default | Adapter contract |
| --- | --- | --- |
| `capacity` | Required | Finite JSON number, 0.1–10,000 MW |
| `da`, `up`, `down` | Required | Each −10,000–100,000 DKK/MWh; `down <= da <= up`, `up > down` |
| `hours` | Default 1 | Finite JSON number, 0.25–24 h |
| `scenarios` | Required | 1–100 finite numeric outcomes, each 0–capacity MW |
| `probabilities` | Missing/null/empty gives equal weights | Otherwise an aligned list, each 0–1.0000001, total within 1e−7 of one; accepted weights are normalized |

The adapter rejects unknown fields, booleans as numbers, numeric strings, duplicate JSON keys and nonfinite JSON constants. Success includes `offer_mw`, `expected_revenue_dkk`, `interval_hours`, a solver description and `data_kind: user_assumptions_not_live`. It multiplies the LP's implicit one-hour objective by the supplied duration. [src/zephyrtrade/app.py:38–100](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L38-L100) [src/zephyrtrade/app.py:237–315](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L237-L315)

Requests require one acceptable Host; absent Origin is allowed for local command-line callers. Supplied Origin and `Sec-Fetch-Site` are checked. JSON bodies are limited to 32,768 bytes; transfer encoding is refused. Eight request slots, an eight-entry queue and a nonblocking solver lock bound concurrency; a busy solver can return 503. The handler's ten-second socket timeout is not an optimizer deadline. These controls do not provide accounts or authentication; keep the service on loopback. [src/zephyrtrade/app.py:102–197](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L102-L197) [src/zephyrtrade/app.py:237–349](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L237-L349)

## Native numerical APIs

`solve_single_period_offer_lp` is a one-period, one-hour library function. It does not accept duration, normalize probability weights or implement the HTTP field schema. Its default `numpy.isclose(sum(p), 1)` admits a wider mass error than the API. A bounded source reproduction with one 10 MW scenario and weight 1.000005 produced a 10 MW offer with LP revenue 500 DKK versus 500.0025 DKK from `expected_scenario_revenue` for DA/up/down 50/80/30. The ordinary API rejects that input before solving. This is documented library debt, not evidence that the normalized UI pipeline fails. [src/zephyrtrade/optimize.py:97–168](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L97-L168) [src/zephyrtrade/optimize.py:214–255](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L214-L255)

`realized_market_revenue` and `revenue_metrics` accept duration but do not independently enforce market price ordering, farm capacity or nonnegative power. `expected_scenario_revenue` checks nonnegative offers/outcomes and price ordering but has no capacity argument. Callers must apply the appropriate economic domain before interpreting a result. `perfect_foresight_offers` is an oracle using realized power, not a dispatch recommendation known in advance. [src/zephyrtrade/evaluate.py:43–114](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/evaluate.py#L43-L114) [src/zephyrtrade/optimize.py:64–95](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L64-L95)

The automatically transcribed signature catalog below covers public definitions in all package Python modules; underscore helpers are implementation detail. Names alone do not promise a stable external API. Configuration defaults and units are in [parameters](../math-and-physics/PARAMETERS_AND_SYMBOLS.md).

## Browser engines and interchange

`window.ZephyrEngine` / CommonJS exposes `finite`, `priceOrder`, `revenue`, `statistics`, `optimize`, `verifyLPResult`, `parseNumbers` and `csvCell`. The optimizer evaluates endpoints and scenario breakpoints; an ascending search retains the lowest offer on an exactly equal objective. LP degeneracy can return another equally valuable offer. `verifyLPResult` checks finite values, offer bounds with 1e−8 MW allowance and absolute objective difference no greater than 1e−6 DKK; the separate 120-case parity script requires difference strictly below 1e−6. [src/zephyrtrade/web/engine.js:1–126](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/engine.js#L1-L126) [scripts/verify_engines.py:1–169](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/verify_engines.py#L1-L169)

The browser library requires positive finite capacity/duration; the dashboard's `validateInput` adds the API-like upper and lower ranges. Browser JSON import uses native `JSON.parse`, so it does not inherit Python's duplicate-key rejection. Imported schema version 1 uses only validated `input`, recalculates the result and ignores untrusted saved `calculated` values. Unknown input fields are not rejected by that browser projection. Files larger than 32,768 bytes are rejected. [src/zephyrtrade/web/app.js:486–524](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L486-L524) [src/zephyrtrade/web/app.js:601–611](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L601-L611)

Snapshot schema 1 includes timestamps, actual output, three prices, model offers, optional forecasts, farm metadata, quality summaries and source CSV hashes. It is a generated historical synthetic snapshot. Hashes support comparison with source files, not authenticity, a cryptographic signature or proof of future profitability. [src/zephyrtrade/web/browser-contracts.d.ts:1–72](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/browser-contracts.d.ts#L1-L72) [scripts/build_app.py:1–258](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/build_app.py#L1-L258)

## Emitted dashboard controls and handlers

This is source inspection of both HTML/template emitters and event handlers, not a fresh browser acceptance report. The static HTML contains shared controls; page-specific controls are generated from templates. Dynamic model options and saved-scenario rows depend on the bundled data/local storage. The complete conservative extraction retains such unresolved runtime instances separately.

| Control group | User effect and important state | Source emission / handling |
| --- | --- | --- |
| Overview, Strategy lab, Model arena, Data explorer, Method links | Hash navigation; `data-go` shortcuts select the same pages | [src/zephyrtrade/web/index.html:1–65](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/index.html#L1-L65); [src/zephyrtrade/web/app.js:537–573](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L537-L573) |
| Model selector; model-card selection | Selects an existing snapshot strategy; no retraining | [src/zephyrtrade/web/app.js:351–405](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L351-L405); [src/zephyrtrade/web/app.js:550–573](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L550-L573) |
| 7-day, 30-day, all, custom range; Apply dates | UTC calendar filtering, inclusive end date; rejected range retains valid state | [src/zephyrtrade/web/app.js:241–289](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L241-L289); [src/zephyrtrade/web/app.js:570–571](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L570-L571) |
| Output, revenue, prices; chart data details | Changes chart measure; over 180 records groups by UTC day; totals still use retained records | [src/zephyrtrade/web/app.js:317–347](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L317-L347); [src/zephyrtrade/web/app.js:357–357](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L357-L357) |
| Capacity, DA/up/down, duration, scenarios, probabilities; calculate | Seven input fields; edits mark previous result stale; submit recalculates | [src/zephyrtrade/web/app.js:407–459](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L407-L459); [src/zephyrtrade/web/app.js:478–516](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L478-L516) |
| Balanced/shortfall/surplus presets | Replaces three prices, retains the last committed scenario's non-price inputs, discards unsaved draft edits and recalculates | [src/zephyrtrade/web/app.js:577–579](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L577-L579) [src/zephyrtrade/web/app.js:518–524](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L518-L524) |
| Save, name, confirm, cancel; load/delete saved | Up to 20 entries, names limited in the UI/restoration; write failure preserves committed state; deletion requires confirmation | [src/zephyrtrade/web/app.js:580–592](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L580-L592) |
| Scenario JSON import/export; curve CSV | Validates/recalculates import; requires fresh inputs before result export; current draft survives a rejected import | [src/zephyrtrade/web/app.js:514–524](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L514-L524); [src/zephyrtrade/web/app.js:581–611](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L581-L611) |
| Python cross-check | Local HTTP only; five-second client abort and epoch guard ignore stale results; hosted build disables probing | [src/zephyrtrade/web/app.js:525–535](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L525-L535); [src/zephyrtrade/web/app.js:613–616](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L613-L616) |
| Data search, pagination, matching CSV; top CSV; model CSV | Search is timestamp text, pages contain 25 rows; matching export differs from global selection export | [src/zephyrtrade/web/app.js:363–405](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L363-L405); [src/zephyrtrade/web/app.js:460–477](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L460-L477); [src/zephyrtrade/web/app.js:574–576](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L574-L576) |
| Provenance JSON | Downloads declared generation date, quality and source identities | [src/zephyrtrade/web/app.js:587–587](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L587-L587) |
| Theme buttons; help/close dialog; skip link | Local preference, native dialog, keyboard focus target | [src/zephyrtrade/web/app.js:536–568](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L536-L568) |

View preferences use `zephyr-view-v1`, theme uses `zephyr-theme`, and saved scenario inputs use `zephyr-scenarios-v1`. They are browser-origin storage, not a synchronized notebook. Draft edits remain in memory. CSV string values are neutralized for leading spreadsheet formula characters; numeric values retain their numerical sign. The diagnostic namespace exposes `getState`, `getLab` and `getVisibleMetrics`; it is a test hook, not an authenticated service or an immutable data store. [src/zephyrtrade/web/app.js:537–546](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L537-L546) [src/zephyrtrade/web/app.js:594–620](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L594-L620) [src/zephyrtrade/web/engine.js:116–126](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/engine.js#L116-L126)

## Teaching companion and publication surfaces

`docs/index.html` is the existing basis-point opportunity lesson, with four parameter sliders, time/run/reset controls, four module tabs, metric tabs, preset/check actions, CSV/config export and a guidance dialog. Its `LabSimulation` namespace exposes `MODEL_SPECS`, `getModelSpec`, `resolveParameters`, `evaluateModel`, `checkCheckpoint`; `LabDashboard` exposes `getState`, `evaluateModel`, `getModelSpec`. These are separate from `ZephyrEngine`, the wind farm's MW/MWh settlement engine. The companion's CSV contains 241 samples across a 24-hour illustrative horizon. Lesson progress is in-memory evidence of matching checkpoints, not certification. [docs/index.html:160–348](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/docs/index.html#L160-L348) [docs/index.html:350–498](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/docs/index.html#L350-L498)

`docs/native-lessons.html`, the standalone Champion HTML, portfolio guide and generated Cloudflare exports are separately indexed publication surfaces; generated/vendor exports are not all hand-reviewed application APIs. Their current links and identity configurations are preserved. The new [reference handbook](../reference/index.html) adds documentation navigation without changing lesson controls, application JavaScript, CSP or hosting. No new deployment is claimed.

## Isolated documentation renderer

`python docs/reference/build_reference.py` regenerates the static reading view; `--check` compares it without writing. The inherited `-h` / `--help` displays parser usage. These are documentation-only interfaces; the helper does not change application models or publish a site. Its public-looking functions/methods and both explicit/inherited CLI behavior are accounted separately from pinned source APIs. All 20 existing Python `ArgumentParser` constructors in the pinned source likewise have an explicit inherited-help disposition; static accounting does not mean every tooling command was executed.

## Public Python signature catalog

### `src/zephyrtrade/__init__.py`

No public function or class declarations; package version metadata only.


### `src/zephyrtrade/app.py`

- `optimize_payload(payload: Any) -> dict[str, Any]` — [src/zephyrtrade/app.py:47–84](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L47-L84)
- `LocalServer` — [src/zephyrtrade/app.py:102–136](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L102-L136)
- `Handler` — [src/zephyrtrade/app.py:139–314](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L139-L314)
- `main() -> None` — [src/zephyrtrade/app.py:317–345](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L317-L345)

### `src/zephyrtrade/data_loader.py`

- `FarmSpec` — [src/zephyrtrade/data_loader.py:37–46](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/data_loader.py#L37-L46)
- `SyntheticDataConfig` — [src/zephyrtrade/data_loader.py:90–98](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/data_loader.py#L90-L98)
- `DataBundle` — [src/zephyrtrade/data_loader.py:102–109](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/data_loader.py#L102-L109)
- `filter_negative_price_intervals(market_prices: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float | int]]` — [src/zephyrtrade/data_loader.py:361–379](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/data_loader.py#L361-L379)
- `validate_data_bundle(bundle: DataBundle) -> None` — [src/zephyrtrade/data_loader.py:382–410](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/data_loader.py#L382-L410)
- `generate_synthetic_data(config: SyntheticDataConfig) -> DataBundle` — [src/zephyrtrade/data_loader.py:413–444](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/data_loader.py#L413-L444)
- `write_data_bundle(bundle: DataBundle, config: SyntheticDataConfig) -> dict[str, Path]` — [src/zephyrtrade/data_loader.py:454–503](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/data_loader.py#L454-L503)
- `main(argv: list[str] | None=None) -> int` — [src/zephyrtrade/data_loader.py:525–549](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/data_loader.py#L525-L549)

### `src/zephyrtrade/direct.py`

- `CapacityBracketEncoder` — [src/zephyrtrade/direct.py:22–85](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/direct.py#L22-L85)
- `probability_quantile_classes(probabilities: ArrayLike, classes: ArrayLike, decision_quantile: float) -> NDArray[np.int_]` — [src/zephyrtrade/direct.py:88–120](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/direct.py#L88-L120)
- `probability_quantile_offers(probabilities: ArrayLike, classes: ArrayLike, encoder: CapacityBracketEncoder, decision_quantile: float) -> tuple[NDArray[np.int_], NDArray[np.float64]]` — [src/zephyrtrade/direct.py:123–135](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/direct.py#L123-L135)

### `src/zephyrtrade/evaluate.py`

- `regression_metrics(actual_mw: ArrayLike, predicted_mw: ArrayLike) -> dict[str, float | None]` — [src/zephyrtrade/evaluate.py:28–40](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/evaluate.py#L28-L40)
- `realized_market_revenue(offer_mw: ArrayLike, actual_power_mw: ArrayLike, day_ahead_price_dkk_mwh: ArrayLike, up_regulation_price_dkk_mwh: ArrayLike, down_regulation_price_dkk_mwh: ArrayLike, interval_hours: float=1.0) -> NDArray[np.float64]` — [src/zephyrtrade/evaluate.py:43–69](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/evaluate.py#L43-L69)
- `revenue_metrics(offer_mw: ArrayLike, actual_power_mw: ArrayLike, day_ahead_price_dkk_mwh: ArrayLike, up_regulation_price_dkk_mwh: ArrayLike, down_regulation_price_dkk_mwh: ArrayLike, interval_hours: float=1.0) -> dict[str, Any]` — [src/zephyrtrade/evaluate.py:72–114](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/evaluate.py#L72-L114)

### `src/zephyrtrade/models.py`

- `ClosedFormLinearRegression` — [src/zephyrtrade/models.py:18–48](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/models.py#L18-L48)
- `GradientDescentLinearRegression` — [src/zephyrtrade/models.py:51–114](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/models.py#L51-L114)
- `LocallyWeightedLinearRegression` — [src/zephyrtrade/models.py:117–182](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/models.py#L117-L182)
- `ClusteredRidgeRegressor` — [src/zephyrtrade/models.py:185–259](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/models.py#L185-L259)
- `polynomial_ols_pipeline(degree: int=2) -> Pipeline` — [src/zephyrtrade/models.py:262–271](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/models.py#L262-L271)
- `polynomial_regularized_pipeline(penalty: Literal['ridge', 'lasso'], alpha: float, degree: int=2, random_state: int=42) -> Pipeline` — [src/zephyrtrade/models.py:274–301](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/models.py#L274-L301)

### `src/zephyrtrade/optimize.py`

- `validate_price_order(day_ahead_price: ArrayLike, up_regulation_price: ArrayLike, down_regulation_price: ArrayLike) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]` — [src/zephyrtrade/optimize.py:20–46](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L20-L46)
- `critical_fractile(day_ahead_price: ArrayLike, up_regulation_price: ArrayLike, down_regulation_price: ArrayLike) -> NDArray[np.float64]` — [src/zephyrtrade/optimize.py:49–61](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L49-L61)
- `perfect_foresight_offers(actual_power_mw: ArrayLike, day_ahead_price_dkk_mwh: ArrayLike, up_regulation_price_dkk_mwh: ArrayLike, down_regulation_price_dkk_mwh: ArrayLike, capacity_mw: float | ArrayLike) -> NDArray[np.float64]` — [src/zephyrtrade/optimize.py:64–94](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L64-L94)
- `solve_single_period_offer_lp(production_scenarios_mw: ArrayLike, scenario_probabilities: ArrayLike, day_ahead_price_dkk_mwh: float, up_regulation_price_dkk_mwh: float, down_regulation_price_dkk_mwh: float, capacity_mw: float) -> dict[str, float | NDArray[np.float64]]` — [src/zephyrtrade/optimize.py:97–168](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L97-L168)
- `optimize_offers_from_residuals(point_forecasts_mw: ArrayLike, calibration_residuals_mw: ArrayLike, day_ahead_price_dkk_mwh: ArrayLike, up_regulation_price_dkk_mwh: ArrayLike, down_regulation_price_dkk_mwh: ArrayLike, capacity_mw: float | ArrayLike) -> NDArray[np.float64]` — [src/zephyrtrade/optimize.py:171–211](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L171-L211)
- `expected_scenario_revenue(offer_mw: float, production_scenarios_mw: ArrayLike, scenario_probabilities: ArrayLike, day_ahead_price_dkk_mwh: float, up_regulation_price_dkk_mwh: float, down_regulation_price_dkk_mwh: float) -> float` — [src/zephyrtrade/optimize.py:214–255](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/optimize.py#L214-L255)

### `src/zephyrtrade/phase2.py`

- `Phase2Config` — [src/zephyrtrade/phase2.py:50–60](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase2.py#L50-L60)
- `load_phase2_data(processed_data_dir: Path) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]` — [src/zephyrtrade/phase2.py:74–97](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase2.py#L74-L97)
- `run_phase2(config: Phase2Config) -> dict[str, Path]` — [src/zephyrtrade/phase2.py:685–768](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase2.py#L685-L768)
- `main(argv: list[str] | None=None) -> int` — [src/zephyrtrade/phase2.py:793–806](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase2.py#L793-L806)

### `src/zephyrtrade/phase3.py`

- `Phase3Config` — [src/zephyrtrade/phase3.py:52–68](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase3.py#L52-L68)
- `run_phase3(config: Phase3Config) -> dict[str, Path]` — [src/zephyrtrade/phase3.py:532–709](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase3.py#L532-L709)
- `main(argv: list[str] | None=None) -> int` — [src/zephyrtrade/phase3.py:730–741](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/phase3.py#L730-L741)

### `src/zephyrtrade/pipeline.py`

- `PipelineConfig` — [src/zephyrtrade/pipeline.py:41–52](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/pipeline.py#L41-L52)
- `file_sha256(path: Path, chunk_size: int=1 << 20) -> str` — [src/zephyrtrade/pipeline.py:55–66](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/pipeline.py#L55-L66)
- `run_pipeline(config: PipelineConfig) -> dict[str, Path]` — [src/zephyrtrade/pipeline.py:91–171](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/pipeline.py#L91-L171)
- `main(argv: list[str] | None=None) -> int` — [src/zephyrtrade/pipeline.py:197–213](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/pipeline.py#L197-L213)

### `src/zephyrtrade/preprocessing.py`

- `PreprocessingConfig` — [src/zephyrtrade/preprocessing.py:62–72](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/preprocessing.py#L62-L72)
- `load_raw_tables(raw_data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]` — [src/zephyrtrade/preprocessing.py:90–100](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/preprocessing.py#L90-L100)
- `engineer_features(wind_power: pd.DataFrame, climate: pd.DataFrame, market_prices: pd.DataFrame, config: PreprocessingConfig) -> pd.DataFrame` — [src/zephyrtrade/preprocessing.py:120–198](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/preprocessing.py#L120-L198)
- `chronological_split(model_frame: pd.DataFrame, train_fraction: float, validation_fraction: float) -> dict[str, pd.DataFrame]` — [src/zephyrtrade/preprocessing.py:201–231](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/preprocessing.py#L201-L231)
- `scale_feature_splits(splits: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], StandardScaler]` — [src/zephyrtrade/preprocessing.py:234–247](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/preprocessing.py#L234-L247)
- `prepare_dataset(config: PreprocessingConfig) -> dict[str, Path]` — [src/zephyrtrade/preprocessing.py:264–335](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/preprocessing.py#L264-L335)
- `main(argv: list[str] | None=None) -> int` — [src/zephyrtrade/preprocessing.py:357–373](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/preprocessing.py#L357-L373)

