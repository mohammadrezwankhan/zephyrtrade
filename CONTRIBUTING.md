# Contributing to ZephyrTrade

Contributions should preserve chronological evaluation, physical feasibility,
and reproducibility. Do not introduce random train/test shuffling or use
realized delivery information as an inference feature.

## Development setup

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Before submitting a change, run:

```bash
python -m ruff format --check src tests
python -m ruff check src tests
python -m pytest -W error
python -m build
```

New public functions require concise docstrings. Behavioral changes require
tests, and changes to data or artifact contracts require corresponding README
and report updates. Generated files under `data/` and `artifacts/` should not be
committed; publication figures may be committed when the reported default
experiment changes.

## Research changes

Document the information set available at bid time, selection interval, test
interval, random seed, settlement assumptions, and any price filtering. Report
both predictive and economic metrics. A new trading policy must enforce
capacity bounds and should be compared on the existing common test timestamps.

Real-data pull requests must describe licensing, retrieval time, forecast
vintage, timezone, market resolution, missing-data handling, and whether later
provider revisions can alter historical observations. Never commit credentials,
commercial telemetry, or data whose redistribution terms are unclear.

## Documentation and evidence additions · 19 November 2026

Use the [current source contracts](docs/developer/API_CLI_AND_INTERFACES.md) and [docs maintenance runbook](docs/maintainer/DOCS_MAINTENANCE_RUNBOOK.md) when reviewing changes. Keep source/tested/candidate/merged/deployed identities distinct. Record actual commands, versions, failures, scopes and tolerances; a successful install, AST parse or source baseline is not a fresh browser or scientific validation.

For a documentation-only change, preserve application/scientific code, test assertions, workflow gates, dependencies, license and existing evidence. Add runnable bounded examples with new output paths. Regenerate the scriptless handbook with `python docs/reference/build_reference.py`, then verify `--check`, internal navigation, source locators and citation schema. Obtain independent review of the frozen diff. Proposed numerical repairs in the roadmap require separate behavior tests and review before implementation.

The [evidence ledger](docs/maintainer/VERIFICATION_EVIDENCE_LEDGER.md) records a local clean-plugin pytest run and a nested audit dependency install after first-attempt failures. Reproduce the root cause before applying those environment adjustments elsewhere; never weaken tests or erase original failures.
