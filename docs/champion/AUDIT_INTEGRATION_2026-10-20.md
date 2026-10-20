# MKTrade audit integration — 2026-10-20

The user supplied an audit report and package and authorized full integration, a merge commit and publication. The attachments were evaluated as technical proposals. The application remains an offline synthetic wind-energy research desk with no live market feed or order execution.

Integration starts from `59f43788a9f654222771a617fd5637c8fb143af0`. All 118 entries in the supplied package's SHA256SUMS file matched. Repairs were ported into the maintained source, preserving the local Python cross-check; the hosted build still disables that local-only integration.

## Repairs and evidence

| Audit issue | Integrated behavior |
| --- | --- |
| ISS-001 | Numeric lists reject leading, trailing and repeated comma/semicolon fields. Optional blank weights and whitespace-separated lists remain supported. |
| ISS-002 | Case-insensitive ledger search and CSV download use one matching predicate. |
| ISS-003 | Custom dates are validated, persisted and restored. Both Apply and Custom reject invalid edited ranges before committing state. |
| ISS-004 | Failed imports preserve the current draft and stale-result state across navigation. |
| ISS-005 | The optimizer compares expected revenue at all breakpoints instead of using a fixed CDF epsilon. |
| ISS-006 | The skip link focuses the current workspace without changing the route or discarding a draft. |
| ISS-007 | Rerenders restore focus for charts, pagination, presets and saved scenarios. Confirmed deletion focuses a remaining Delete button or Save scenario. |
| ISS-008 | Light-theme navigation indices meet the tested contrast threshold. |
| ISS-009 | Input borders use a contrast-checked theme token. |
| ISS-010 | The persistent polite search status survives content replacement and reports matches while focus stays in search. |
| ISS-011 | Charts measure their container and use compact geometry on narrow screens. |
| ISS-012 | The build generates CSP hashes from the final hosted document. Publication must disable automatic analytics injection and remove the stale runtime edge-policy override. |

The audit supplied a captured HTML file. It was not installed over the repository source. The portable HTML was regenerated from the preserved upstream CSVs. Windows output now uses portable POSIX provenance paths and deterministic LF newlines; the dataset and snapshot-verification evidence remain unchanged.

## Verification before merge

- The original maintained engine baseline passed 13 tests. The supplied numerical audit reproduced 9 failures before repairs; the integrated audit passes all 16 checks, including 1,000 seeded comparisons.
- The maintained Node suite passes 22 tests: 15 engine regressions, 4 runtime security tests and 3 engineering-hero tests. CodeQL identified script-extraction edge cases; all three JavaScript extractors now recognize case-insensitive tags and HTML closing-tag syntax, with a regression that failed before the repair.
- Source-data verification reconciles all 34,992 stored revenues across 3,888 observations and 9 strategies. Maximum error is `3.637978807091713e-12`; the 53 missing hours remain gaps. Both upstream compressed source hashes match.
- The independent Python/SciPy engine comparison passes 120 cases; maximum objective difference is `5.820766091346741e-11`. Different optimal offers are allowed when objective values tie.
- The unchanged Python suite passes all 86 tests with warnings treated as errors on GitHub's Python 3.11 and 3.12 runners, using ordinary HTTP. It also passes locally when loopback transport uses TLS. On this host AdGuard rewrites plain HTTP, injects HTML and removes Content-Length, causing the original local plain-HTTP HEAD test to fail (85 passed, 1 failed). The diagnostic TLS wrapper changes server/client transport only, not application handlers or assertions.
- Ruff checking and formatting pass. Wheel and source distribution builds succeed.
- Both Cloudflare export checkers pass, including generated CSP/document consistency and the existing hero policies.
- The final browser suite passes all 180 checks in 4.9 minutes (60 each in Chromium, Firefox and WebKit) against the corrected build served over loopback TLS. It checks actual export/import bytes, native confirmation accept/cancel, all 156 ledger pages, source provenance, numeric regressions, focus, four viewports, both themes, offline behavior and CSP. A separate deployed run is required after publication.

The reviewed runtime document SHA-256 is `902d66e8601cb108645b0985c067e55e6f15677d8d0ee7d957be704263e66007`. Expected hashes must come from the final build artifact, never from an injected public response.

An independent read-only review used the explicitly pinned `deep-read` agent (GPT-6 Luna, maximum reasoning) with a fresh, bounded prompt. Its date-validation and deletion-focus observations were repaired with failing regressions first, then verified in all three browsers. No Critical or Important findings remained in its reviewed scope.

## Publication and ongoing builds

1. Merge the reviewed PR using a merge commit and build from that revision with `PUBLIC_SOURCE_REVISION` set to its full SHA.
2. Run `node scripts/build-domain.mjs`, `node scripts/check-domain.mjs` and `node scripts/check-cloudflare.mjs`. Upload the resulting site, including `_headers` and `_redirects`, to the existing `mktrade-zephyr` Pages project on branch `main`.
3. Disable zone Web Analytics automatic injection (`rum = off`). Keep runtime HTML free of injected scripts.
4. Exclude the `/run/` path prefix from the legacy zone response-header rule so the runtime uses the build-generated Pages CSP. Preserve the rest of that rule and the engineering-hero exception. During the transition, an old/new hash union can keep both deployed revisions functional.
5. Verify the public runtime's exact SHA-256, all three inline script hashes in both CSP directives, absence of injected analytics and full browser behavior. Keep the previous deployment and edge-rule snapshot for rollback.

`scripts/runtime-security.mjs` is the shared authority for generated runtime security headers. Build and check scripts use the same final HTML; security metadata stays outside public assets. `scripts/generate-security-headers.py` is also retained as the audit's standalone regeneration utility. The review server and browser instructions are in [the browser test README](../../tests/browser/audit/README.md).

## Limits

Automated focus, contrast, geometry and browser checks do not certify screen-reader speech, every keyboard sequence, zoom/text-spacing behavior or WCAG conformance. Manual assistive-technology review remains outstanding.

The optimizer deterministically keeps the first breakpoint with the greatest *computed* revenue. Floating-point near-ties can select a later offer even when mathematical revenues are equal; the observed difference is immaterial to the objective. No tolerance was added that could reintroduce the extreme-price/CDF defect.

The merge SHA, deployment ID, hosted CI status and public verification results are recorded in the PR and final release receipt rather than guessed in this pre-merge document.
