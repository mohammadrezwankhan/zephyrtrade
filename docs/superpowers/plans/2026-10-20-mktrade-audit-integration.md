# MKTrade audit integration plan

> Execute with superpowers:executing-plans. The user authorized integration, a merge commit, and publication.

**Goal:** Integrate and verify all twelve audit repairs in the maintained ZephyrTrade source, merge with a merge commit, and publish the verified site.

**Architecture:** Preserve the existing offline synthetic research application. Port P001–P005 into `src/zephyrtrade/web`, regenerate `ZephyrTrade-Champion.html`, and produce deployment CSP from final hosted bytes. Keep the local Python cross-check enabled only for the local application.

**Tech stack:** Vanilla JavaScript, Python, Playwright, Cloudflare Pages/edge, GitHub.

**Spec:** User-supplied MKTrade-Audit-Report.md and MKTrade-Audit-Package.zip (2026-10-20), treated as technical proposals. Package integrity: all 118 SHA256SUMS entries pass. Source base: `59f43788a9f654222771a617fd5637c8fb143af0`.

## Global constraints

- Preserve synthetic historical data and no-order-execution disclosures.
- Do not replace repository source with the hosted snapshot; preserve the local Python integration.
- Keep final inline script hashes in both CSP script directives, without script unsafe-inline.
- Preserve source artifacts and unrelated site content.
- Use the isolated Git checkout in the system temporary directory. Downloads denies Git rename/unlink operations; the temporary checkout supports normal commits and expected-head-checked PR merge.

## Review focus

- Delimiter-only and mixed empty fields must not silently alter weights.
- Failed import must preserve unsaved inputs across navigation, including stale state.
- Rerenders, chart resizing and pagination boundaries must retain meaningful focus.
- Final hosted scripts must match CSP after build transforms and CDN delivery.
- The audit proposal chooses the first breakpoint with the greatest computed revenue. Verify objective parity with Python; floating-point near-ties are not exact mathematical ties.

## Task 1: Application repairs

Files: `src/zephyrtrade/web/{engine.js,app.js,styles.css,index.html}`, `tests/browser/engine.test.cjs`, `tests/browser/audit/*`, `ZephyrTrade-Champion.html`.

- [x] Run existing numerical baseline and reproduce audit parser/optimizer failures.
- [x] Import reviewed browser acceptance tests and add numerical regressions to the maintained engine tests.
- [x] Port the exact verified source changes, preserving the localhost Python condition.
- [x] Rebuild the portable app from source CSVs; verify source hashes and revenue values.
- [x] Run numerical, state, rendering and browser acceptance checks against rebuilt output (180/180).

## Task 2: Deployment integration

Files: `scripts/build-domain.mjs`, `scripts/build-cloudflare.mjs`, CSP generator/review server, `.github/workflows/cloudflare.yml`, release documentation.

- [x] Inspect actual serving resources and existing edge policy.
- [x] Integrate reproducible CSP generation into hosted build and add consistency assertions.
- [x] Verify final hosted build in Chromium, Firefox and WebKit, including downloads, import, offline, themes and viewport matrix (180/180 against loopback TLS).
- [x] Run existing project tests, parity, export checks and build checks; record limitations explicitly.

## Task 3: Review, merge, publish

- [x] Obtain bounded independent code review with an explicitly pinned smaller agent.
- [x] Address substantive findings and rerun affected checks.
- [ ] Create a PR from reviewed file changes, verify the uploaded head and CI status, and merge using the merge method.
- [ ] Build from the merge revision, publish through the existing hosting path, and verify live document hash, CSP and browser behavior.
- [ ] Record merge/deployment IDs, reproducible results and remaining manual accessibility limits.
