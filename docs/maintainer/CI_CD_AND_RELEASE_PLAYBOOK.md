# CI, release and existing publication playbook

## Configured workflows

Preserve check names, matrices, permissions, event coverage and publication guards. Repository instructions explicitly prohibit weakening required behavior to reduce CI spending. This documentation package does not alter workflows or security tooling. [AGENTS.md](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/AGENTS.md)

| Workflow | Triggered work and boundary | Source |
| --- | --- | --- |
| `ci` | Push to main/championization and PR; Python 3.11/3.12 lint, format, warnings-as-errors tests, Node 22 numerical parity and distributions; separate pinned Python 3.13.5 / Node 24 job with bounded research smoke | [.github/workflows/ci.yml](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/.github/workflows/ci.yml) |
| `Hardened CI` | Main push, PR, merge group, manual, schedule; five security modes and seven language-quality modes; preserved raw reports | [.github/workflows/hardened-ci.yml](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/.github/workflows/hardened-ci.yml) |
| `CodeQL security analysis` | Python and JS/TS analysis with SARIF gate; explicit workflow does not duplicate SARIF upload | [.github/workflows/codeql.yml](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/.github/workflows/codeql.yml) |
| `Verify Cloudflare browser export` | Builds/checks collection and dedicated exports; native tests then Chromium/Firefox/WebKit audit against the generated runtime document hash. This workflow verifies exports; it is not a deployment job | [.github/workflows/cloudflare.yml](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/.github/workflows/cloudflare.yml) |
| `MKLab traceability sync` | `traceability-links` checks pinned mapping/live links; conditional source-observation event uses an existing bridge secret and writes a separate registry branch | [.github/workflows/mklab-traceability-sync.yml](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/.github/workflows/mklab-traceability-sync.yml) |
| `Flagship dashboard` | Existing docs/assets path-filtered validation; main-only Pages deployment of `docs` after validation | [.github/workflows/deploy-dashboard.yml](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/.github/workflows/deploy-dashboard.yml) |
| `Publish learning dashboard (manual)` | Existing manually dispatched public-main preview route; validate, assemble `_site`, deploy Pages | [.github/workflows/preview-pages.yml](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/.github/workflows/preview-pages.yml) |
| `Portfolio guide checks` | Path-scoped guide data/source/SVG validation using a hash-verified parser dependency | [.github/workflows/portfolio-dashboard-check.yml](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/.github/workflows/portfolio-dashboard-check.yml) |

The remote source response also included GitHub-managed code-scanning/dependency jobs not represented as new workflow YAML here. Inspect actual PR check contexts and policy; do not derive a required-check list solely from filenames.

## Local documentation gate

1. Confirm the intended base/source revision and clean scope. Preserve original source, result artifacts, licensing and security policy.
2. Run the established application checks appropriate to the changed surface, keeping exact interpreter/dependency versions. This package's numerical code is unchanged; its retained source runs are described in the [ledger](VERIFICATION_EVIDENCE_LEDGER.md).
3. Regenerate the scriptless handbook with `python docs/reference/build_reference.py` (Pandoc required), then check that a second generation is byte-identical. Validate local paths/anchors, source permalinks, math rendering, image fallbacks, table accessibility and CFF schema.
4. Inspect the complete diff. Expected changes are canonical Markdown, the isolated reference renderer/CSS/manifest/generated HTML, a static navigation link and a dated start-guide clarification. No workflow, executable application, dataset, dependency or asset change belongs in this package.
5. Freeze the candidate file manifest and Git tree, six structured handoffs and independent review. Author verification does not substitute for independent QA.

The new `docs/reference/index.html` is a committed derivative included in the existing `docs` Pages upload. The companion's static link makes it discoverable. The existing workflow does not regenerate this handbook; maintainers run its isolated renderer before submitting a documentation update. This avoids introducing a new deployment service or modifying browser calculation code.

## PR and merge policy

The latest source baseline is dated 2026-11-19, not a candidate pass. Refresh policy, base/head, complete diff, check contexts and required reviews before integration. Observed rulesets were [history protection](https://github.com/mohammadrezwankhan/zephyrtrade/rules/25357399) and [traceability gate](https://github.com/mohammadrezwankhan/zephyrtrade/rules/25913571); the latter requires `traceability-links` strictly against the current branch context. Classic branch-protection access was denied (403), leaving additional requirements unknown. Do not interpret incomplete access as permission to merge.

Use the repository's permitted merge strategy and an atomic expected-head guard. Respect a required merge queue or protected environment if discovered. A queued or auto-merge-enabled PR is not a confirmed merge. Record PR-head, synthetic merge/queue revision, tested SHA and final merged SHA separately. Agent review does not impersonate a platform-required human approval.

## Existing publication routes

| Surface | Declared source and URL | Verification still required after merge |
| --- | --- | --- |
| Documentation/teaching Pages | `docs/`, including the new handbook; existing Pages workflow | Resolve actual Pages deployment/environment through an available supported route, bind it to merged SHA and inspect distinctive handbook content |
| Collection browser export | `cloudflare.json`; `https://mklab.co.technology/apps/zephyrtrade/` | Existing hosting owner must associate deployed artifact/runtime hash and source SHA; a build pass alone is insufficient |
| Dedicated browser export | `cloudflare-domain.json`; `https://mktrade.co.business/`, project `mktrade-zephyr` | Same artifact/deployment/content identity check; no DNS or new-hosting operation in this package |

The local dedicated build/check passed on 2026-11-19 with three pages and 58 files; its runtime document SHA-256 was `8cfad9a62632a92006b1d00630194410cd65d9f3de386dac474d7f3e72d5f31d`. The collection runtime hash was `deaab7ccfc8ea21cd5d084339e864f372c5d75c008e3a343dd8c7cfd3ab4195a`. These identify local output bytes at the pinned source, not live canonical responses. [cloudflare.json](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/cloudflare.json) [cloudflare-domain.json](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/cloudflare-domain.json) [scripts/build-domain.mjs](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/build-domain.mjs)

Pages metadata access was unavailable through the supported connector route in the authoring environment. Preserve `PUBLICATION_UNVERIFIED` until a later successful deployment and content observation. An HTTP 200 or unchanged home page is not proof that the new reference route is public.

## Release history and rollback

The bounded release query (first page, maximum 20) on 2026-11-19 returned [preview-2026.09.30](https://github.com/mohammadrezwankhan/zephyrtrade/releases/tag/preview-2026.09.30), published September 30. Package metadata declares 1.1.0; CFF deliberately retains the preview version and contributor authorship. Do not manufacture a new tag, DOI, release date or wheel publication to reconcile these different records. [pyproject.toml:5–18](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/pyproject.toml#L5-L18) [CITATION.cff](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/CITATION.cff) [CHANGELOG.md](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/CHANGELOG.md)

If a documentation deployment fails, retain its run, candidate and merged identities; restore a known-good documentation artifact through the established reviewed route without rewriting history or disabling guards. If application assets differ unexpectedly, stop integration and investigate the full diff. Recovery details are in the [owner runbook](../owner/BUS_FACTOR_RECOVERY_RUNBOOK.md).
