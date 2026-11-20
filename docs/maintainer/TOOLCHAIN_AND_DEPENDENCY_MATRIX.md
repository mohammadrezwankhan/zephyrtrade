# Toolchain and dependency matrix

> Source snapshot: [`29abf5d8bd6f05b1f0c027d8753f4837840215dc`](https://github.com/mohammadrezwankhan/zephyrtrade/tree/29abf5d8bd6f05b1f0c027d8753f4837840215dc), inspected 20 November 2026. This is source documentation, not a new release, test run or deployment receipt.

| Layer | Declared source requirement | Verification command / proof |
| --- | --- | --- |
| Python package | `>=3.11`, source package `zephyrtrade` 1.1.0 in [pyproject.toml](../../pyproject.toml) | `python --version`; `python -m pip show zephyrtrade` |
| Runtime numerical stack | NumPy 1.26–under 3, pandas 2.1–under 4, SciPy 1.11–under 2, scikit-learn 1.4–under 2, plus joblib/matplotlib | `python -m pip check`, show installed/frozen versions |
| Development | pytest, Ruff, build, Playwright and typed Python/JS test tooling | `python -m pytest -W error`, `python -m ruff check src tests` |
| Original GitHub CI | Python 3.11/3.12 Ubuntu matrix | [CI YAML](../../.github/workflows/ci.yml), original run IDs per commit |
| Pinned reproducibility | Python 3.13.5 on Ubuntu 24.04 with [requirements-tested.txt](../../requirements-tested.txt) | Workflow pinned job and `pip freeze` |
| Browser parity | Node 22 on matrix and Node 24 for pinned job | `node --test tests/browser/engine.test.cjs` and `python scripts/verify_engines.py` |
| Publication | Node 24 and source-defined Cloudflare build scripts | [Cloudflare guide](../CLOUDFLARE.md), complete output and provider receipt |

Declared version ranges are **not** proof of the versions installed in an evaluator environment. The CFF's historical `preview-2026.09.30` reference and Python package's `1.1.0` are distinct metadata contracts. Never silently rewrite historical citation/release records to match a working-tree version.
