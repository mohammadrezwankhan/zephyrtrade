#!/usr/bin/env sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ ! -x .venv-champion/bin/python ]; then
  python3 -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11 or newer is required"'
  python3 -m venv .venv-champion
fi
if ! .venv-champion/bin/python -c 'import zephyrtrade.app' >/dev/null 2>&1; then
  .venv-champion/bin/python -m pip install -e .
fi
exec .venv-champion/bin/python -m zephyrtrade.app "$@"
