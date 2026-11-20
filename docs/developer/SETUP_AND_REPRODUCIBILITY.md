# Setup and reproducibility

> Source snapshot: [`29abf5d8bd6f05b1f0c027d8753f4837840215dc`](https://github.com/mohammadrezwankhan/zephyrtrade/tree/29abf5d8bd6f05b1f0c027d8753f4837840215dc), inspected 20 November 2026. This is source documentation, not a new release, test run or deployment receipt.

## Minimum local setup

The package declares **Python 3.11+**, while the original CI tests include Python 3.11/3.12 and a pinned Linux Python 3.13.5 job. Node.js is needed for browser-engine parity. From an authorized clean clone:

```sh
python -m venv .venv
python -m pip install -e ".[dev]"
python -m ruff check src tests
python -m ruff format --check src tests
python -m pytest -W error
node --test tests/browser/engine.test.cjs
python scripts/verify_engines.py
python -m build
```

These are **source-declared commands**, not recorded as executed by this documentation change. Install Node.js separately according to the platform. For the pinned original Linux environment, use [requirements-tested.txt](../../requirements-tested.txt) and [CI configuration](../../.github/workflows/ci.yml) rather than assuming your installed versions are equivalent.

## First local experience

The existing README documents a single-file portable candidate and `node scripts/preview-demo.mjs` for a separate synthetic browser preview. The Python research server runs on loopback:

```sh
python -m zephyrtrade.app --no-browser --port 8765
```

Open `http://127.0.0.1:8765`; do **not** expose this server on a public network. The local server's allowed asset list and request guards are defined in [app.py](../../src/zephyrtrade/app.py). On a busy port, choose an unused alternative.

## Traceability for every numerical result

Record the full commit SHA, Python/Node versions, platform, declared dependency versions, seed, interval length, price filter, train/calibration/test chronology, scenario units and any input hash. [pipeline.py](../../src/zephyrtrade/pipeline.py) writes a configuration/environment/output manifest and SHA-256 values for its declared outputs. Separate the **historical report** from a **freshly executed** run; do not overwrite historical evidence.
