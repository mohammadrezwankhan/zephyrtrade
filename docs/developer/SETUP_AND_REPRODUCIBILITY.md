# Setup and reproducibility

Start from the repository root at the revision you intend to inspect. This guide describes source `29abf5d8bd6f05b1f0c027d8753f4837840215dc`. [Index](../INDEX.md) · [Worked examples](WORKED_EXAMPLES_AND_LABS.md) · [Toolchain matrix](../maintainer/TOOLCHAIN_AND_DEPENDENCY_MATRIX.md).

## Choose the task

| Goal | Entry point | Installation or output boundary |
| --- | --- | --- |
| Explore saved research and hypothetical offers | Open `ZephyrTrade-Champion.html` | Complete standalone artifact; no Python required |
| Use the native SciPy cross-check | `python -m zephyrtrade.app --no-browser` | Python environment, loopback service, default port 8765 |
| Read the teaching companion | Open `docs/index.html` | Separate generic sensitivity model, not native settlement |
| Read the reference handbook | Open `docs/reference/index.html` | Static HTML/CSS; no runtime dependency for reading |
| Rebuild the handbook | `python docs/reference/build_reference.py` | Python standard library plus Pandoc; documentation only |
| Reproduce a bounded training workflow | `scripts/smoke_research.py --output NEW_DIRECTORY` | Newly generated data, default Phase 2 and reduced Phase 3 |

These entry points are defined by [README.md](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/README.md), [src/zephyrtrade/app.py:317–345](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L317-L345), [scripts/smoke_research.py](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/smoke_research.py) and the new handbook's `chapters.json`. Opening `src/zephyrtrade/web/index.html` alone is not equivalent to the packaged standalone artifact: its sibling scripts, stylesheet and snapshot must be available.

## Python environment

The package declares Python 3.11 or later. Source CI has Python 3.11/3.12 jobs and a separate Linux/Python **3.13.5** reference job. `requirements-tested.txt` pins scientific packages for that reference environment; it is not a universal platform lock. Sources: [pyproject.toml](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/pyproject.toml), [requirements-tested.txt](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/requirements-tested.txt), [.github/workflows/ci.yml](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/.github/workflows/ci.yml).

```bash
python -m venv .venv-zephyr
# POSIX shell:
. .venv-zephyr/bin/activate
# PowerShell alternative: .venv-zephyr\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m zephyrtrade.app --no-browser
```

Use the displayed `http://127.0.0.1:8765` address. `--port 8766` selects another allowed port; the CLI accepts 1024–65535. `--no-browser` prevents the automatic browser-opening timer. Stop with Ctrl+C. The Windows launcher creates its own `.venv-champion`; inspect the launcher before running it and do not mix that environment with a historical uploaded environment. Sources: [src/zephyrtrade/app.py:317–345](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L317-L345), [START_PYTHON_WINDOWS.bat](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/START_PYTHON_WINDOWS.bat), [start-python.sh](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/start-python.sh).

For the reference scientific dependency set, use a clean Python 3.13.5 environment and install `requirements-tested.txt` before the development extra, then run `python -m pip check` and record `python -m pip freeze`. Do not call a Python 3.12 installation the 3.13.5 reference run merely because the scientific package versions match. The 19 November documentation run used Python **3.12.14** with the seven exact scientific pins and retained its interpreter difference.

## Existing checks

```bash
python -m ruff check src tests
python -m ruff format --check src tests
python -m pytest -W error
python -m build
npm ci --ignore-scripts
npm ci --prefix tests/browser/audit --ignore-scripts
npm run quality:lint
npm run quality:typecheck
npm run quality:format
npm run quality:browser
node --test tests/browser/engine.test.cjs
python scripts/verify_engines.py
```

Node 22 or newer is declared at the root; the Cloudflare workflow uses Node 24. The nested audit lock is needed for the type-aware lint scope as well as browser automation. The format script checks its explicit five-file list, not every file in the repository. TypeScript's configured source scope excludes the vendor tree. Sources: [package.json](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/package.json), [tsconfig.json](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/tsconfig.json), [.github/security/quality.py:141–182](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/.github/security/quality.py#L141-L182), [.github/workflows/cloudflare.yml](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/.github/workflows/cloudflare.yml).

If unrelated globally installed pytest plugins fail before collection, first reproduce in a clean virtual environment. The retained local workaround used `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`; this removed an unrelated host AnyIO plugin's deprecation under `-W error`. It did not suppress warnings from the source tests. Record the original failure and the changed invocation, rather than replacing the first receipt. [Troubleshooting](TROUBLESHOOTING.md) describes this and the initial nested-dependency lint failure.

## Reproduce without replacing retained results

The pinned repository retains only selected historical data artifacts. Generate fresh raw and processed files in a separate directory. The shortest complete research exercise supplied by the source is:

```bash
python scripts/smoke_research.py --output /tmp/zephyr-smoke-new
```

The output directory must not already exist. This script generates January–February 2023 synthetic observations, runs default Phase 2, then a reduced Phase 3 with 10 boosting iterations and a smaller candidate grid. It does not rerun the original three-year/default-Phase-3 study. The 19 November run completed successfully in about 50.30 seconds in the recorded local environment; that is an observation, not a runtime guarantee. Source: [scripts/smoke_research.py:18–75](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/smoke_research.py#L18-L75).

For an intentional full default experiment, direct **all** outputs away from the retained paths:

```bash
zephyr-run --start 2022-01-01 --end 2025-01-01 --seed 42 \
  --raw-data-dir /tmp/zephyr-full-new/raw \
  --processed-data-dir /tmp/zephyr-full-new/processed \
  --artifact-dir /tmp/zephyr-full-new/artifacts \
  --figure-dir /tmp/zephyr-full-new/figures
```

This full command is source-defined guidance, **not executed in this documentation task**. Check that the destination is new before running it. The source pipeline creates directories and can overwrite matching outputs. A seed supports reproducibility within a declared software environment; compression timestamps, machine metadata, dependency changes and floating-point libraries can alter bytes. `run_manifest.json` records runtime/dependencies and four summary/provenance hashes; it is not a signature of every produced file. Source: [src/zephyrtrade/pipeline.py:91–194](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/pipeline.py#L91-L194).

## Static builds and browser capability

```bash
node scripts/build-domain.mjs
node scripts/check-domain.mjs
python docs/reference/build_reference.py --check
```

The first two commands write/check `.cloudflare/site` and the separate collection export. They do not publish. Existing builders accept a fresh `CLOUDFLARE_OUTPUT_ROOT` beneath `.cloudflare`; set `PUBLIC_SOURCE_REVISION` to an exact source commit for exported copies without Git metadata. The dedicated local build and checker passed on the pinned source. Its three static information pages and 58 emitted files are build observations, not hosted availability evidence. Sources: [scripts/build-domain.mjs:1–62](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/build-domain.mjs#L1-L62), [scripts/check-domain.mjs](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/check-domain.mjs).

The local Chromium harness was attempted and failed before page initialization with `socket() failed: Operation not permitted`. Host Playwright 1.62.0 also differed from the declared 1.65.0. No fresh screenshots, visual acceptance, native storage persistence or three-browser run are claimed. The harness itself uses `set_content` and a Storage test double; even a passing run would not prove native-origin persistence or browser-to-Python end-to-end behavior. Source: [scripts/check_browser.py:1–135](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/check_browser.py#L1-L135).
