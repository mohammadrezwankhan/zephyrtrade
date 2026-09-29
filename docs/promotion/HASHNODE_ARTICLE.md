# Tracing a ZephyrTrade demo result back to source

Research application that generates synthetic wind/weather/price tables, compares wind-forecast and direct-offer strategies, backtests revenue and explores hypothetical offers without placing trades.

## The engineering problem

For wind-market and numerical-method researchers, a screen is useful only when its displayed result can be traced to a rule and a source. In this project the supplied records and examples are synthetic. That choice makes exploration possible without pretending a provider is connected or a current fact is verified.

## Follow the implementation

- `src/zephyrtrade/app.py`
- `src/zephyrtrade/optimize.py`
- `src/zephyrtrade/web/engine.js`
- `scripts/verify_engines.py`
- `tests/test_app.py`
- `artifacts/reproduction/results/run_manifest.json`

Begin at the first source entry, identify one visible output, then follow the calculation or state transition to its fixture. Change one synthetic input and rerun the smallest relevant check. The architecture document shows the delivered demo path rather than an imagined production stack.

## A deliberate boundary

Local state is useful for trying a workflow; it is not proof of remote receipt, clinical safety, official guidance or multi-user synchronization. The interface's demo language is part of the contract. Preserve unknown/stale states rather than filling them with a plausible answer.

## Reproduce it

```sh
git clone https://github.com/mohammadrezwankhan/zephyrtrade.git
cd zephyrtrade
node scripts/preview-demo.mjs
```

The current quality report separates executed checks from historical reports and unavailable environments. It also identifies remaining release blockers; no performance improvement is inferred from a new screenshot.

## What would improve it

Review one native-origin persistence journey, one keyboard interaction, or one bilingual explanation using the contribution guide. Bring a small reproduction and a specific invariant. Repository: https://github.com/mohammadrezwankhan/zephyrtrade.

Draft article, not published. Technical evidence must be refreshed at the release commit before external publication.
