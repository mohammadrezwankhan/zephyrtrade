# Replay, comparison and revenue: cross-browser observations

On 9 November 2026, source commit `4c3034aaeeea6e3e07f0a1180565d01eb8659e86` was served with `node scripts/preview-demo.mjs` at `http://127.0.0.1:4173/`. Playwright 1.64.1 used Firefox 157.0 and WebKit 27.2 on Windows, with a 1440 × 900 viewport and a fresh browser context for each engine.

1. Run `python scripts/verify_engines.py --manifest tests/fixtures/fictional-scenario-v1.json`. The browser JavaScript module and Python each returned a 7 MW offer and 2,540 DKK expected interval revenue; objective difference was 0 DKK, below the 0.000001 DKK tolerance.
2. Open **Model arena** and inspect **Value leaderboard**. In both engines all cells in the nine strategy rows matched. The leading row was Direct continuous, 18,761,431 DKK revenue and 99.38% perfect-foresight capture; the final row was 24-hour persistence, 16,719,259 DKK and 88.56%. These are aggregate values from the dashboard's separate synthetic historical dataset, not outcomes of the imported scenario.
3. Open **Strategy lab**, select **Import JSON**, and choose the same committed scenario. Both displayed scenarios `3, 7, 11` MW, a 7.00 MW optimal offer and 2,540.00 DKK expected revenue. After reload the unsaved input reset and the default offer was 9.00 MW. These are hypothetical assumptions, not trades.

The browser run asserted identical text in every comparison-table cell, the scenario result and reload state. There were no uncaught page errors or page-level horizontal overflow on either route. Firefox logged no console errors; WebKit logged one CSP inline-style refusal and one optional `/api/health` 404 per load, four messages across initial load and reload. The [prior note](strategy-lab-cross-browser-partial.md) records a minimal native-select reproduction; visual impact is unknown.

The comparison table is not recalculated from the scenario manifest: importing affects Strategy lab only. Therefore this sequence records the requested surfaces and their actual boundary; it does not establish a manifest-driven strategy comparison or general browser compatibility. The baseline `python -m pytest -W error tests/test_direct.py tests/test_evaluate.py` passed seven tests locally.

## Standalone health response follow-up

A later preview-server change gives `/api/health` a distinct
`zephyrtrade-preview` identity. Repeating the same journey on 9 November
2026 with Firefox 157.0 and WebKit 27.2 yielded the same nine comparison
rows, 7 MW / 2,540 DKK scenario and 9 MW reload boundary. Neither browser
logged the earlier optional-health 404. Firefox logged no console errors;
WebKit logged one CSP inline-style refusal per load, two in total. Both
still displayed **How to enable the Python cross-check**: the preview does not
provide the local Python solver. The CSP policy and its unresolved visual
impact are unchanged.
