# ZephyrTrade release verification

The 2026-10-20 audit tests are integrated against the maintained source. Each browser context has empty storage. Tests exercise actual downloaded bytes, JSON imports, saved-scenario deletion, all 156 ledger pages, numerical edge cases, date restoration, focus, both themes, four viewport sizes, offline behavior and final CSP hashes. Chromium, Firefox and WebKit run the same cases.

## Run from the repository root

1. Install Python project dependencies, then run `python scripts/build_app.py` to rebuild the portable application and validate all supplied source CSV revenues.
2. Run `node scripts/build-domain.mjs`, `node scripts/check-domain.mjs` and `node scripts/check-cloudflare.mjs`.
3. Run `npm ci --prefix tests/browser/audit` and `node tests/browser/audit/node_modules/playwright/cli.js install chromium firefox webkit` (Linux CI also uses `--with-deps`).
4. Set `AUDIT_EXPECTED_DOCUMENT_SHA256` to `document_sha256` from `.cloudflare/runtime-security-headers.json`.
5. Run `node tests/browser/audit/node_modules/playwright/cli.js test --config tests/browser/audit/playwright.config.ts`. With no explicit URL, Playwright starts the loopback review server automatically.

For a deployed check, set `AUDIT_BASE_URL` to the final `/run/` URL and set the digest from that exact release build. Certificate errors are never ignored for public hosts. `AUDIT_LOCAL_TLS=1` permits a self-signed certificate only on a loopback host, for machines whose filtering software rewrites plain HTTP. `AUDIT_RESULTS_DIR` selects a writable output directory; traces and screenshots are retained for failures, with JSON and HTML reports.

Do not change expected hashes to accommodate injected or rewritten HTML. Diagnose the serving layer or local proxy first. The loopback fixture proves application behavior and response configuration; public checks separately prove deployed HTTPS delivery.

The automated suite does not certify screen-reader speech, all keyboard order, text-spacing overrides or WCAG conformance. Manual assistive-technology checks remain a separate validation activity.

## Other checks

- `node --test tests/browser/engine.test.cjs scripts/runtime-security.test.mjs`
- `node tests/browser/audit/numerical-regression.cjs ZephyrTrade-Champion.html`
- `python -m pytest -W error`
- `python scripts/verify_engines.py`

Original audit evidence is retained separately in the user-provided package. These tests intentionally target current generated output instead of the audit snapshot hash.
