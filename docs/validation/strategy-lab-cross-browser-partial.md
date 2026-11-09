# Strategy-lab cross-browser observations (partial)

On 9 November 2026, source commit `8ba45ae12aa5ccfeb68aca9c833db158cadc4e45`
was served with `node scripts/preview-demo.mjs` at
`http://127.0.0.1:4173/`. Playwright 1.64.1 used Firefox 157.0 and WebKit
27.2 on Windows at 1440 × 900.

In each engine, open **Strategy lab**, retain the default one-hour prices
(420 / 610 / 310 DKK/MWh for day-ahead / up / down) and 30 MW capacity,
enter `3, 7, 11` MW scenarios with equal weights, then calculate. Both
displayed a 7.00 MW offer and 2,540.00 DKK expected interval revenue; neither
showed an uncaught page error or page-level horizontal overflow. After reload,
the unsaved draft reset to the default scenarios and the displayed offer reset
to 9.00 MW. Firefox logged no console errors. WebKit logged four console
errors across the initial load and reload: a strict-CSP inline-style refusal
and a 404 for the preview's optional `/api/health` request on each load.

The same WebKit CSP refusal reproduced on a minimal page with only a native
`select` under `style-src 'self'` and `style-src-attr 'none'`. This points to
a browser/native-control interaction; visual impact was not established and
the security policy was not weakened.

The requested manifest replay was not performed: `scripts/verify_engines.py`
generates seeded cases and has no manifest input. The observations above are
limited strategy-lab evidence, not general browser compatibility certification
or evidence of actual trades. The requested baseline
`python -m pytest -W error tests/test_direct.py tests/test_evaluate.py` passed
seven tests locally.
