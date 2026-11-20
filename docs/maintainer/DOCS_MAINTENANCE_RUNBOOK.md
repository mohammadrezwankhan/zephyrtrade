# Documentation maintenance runbook

## Keep one accountable source

The [documentation index](../INDEX.md) maps all 24 requested entry points. Canonical Markdown remains editable source; the reference handbook is a generated reading view. Original README, changelog, contribution instructions, security policy, CFF and existing site content retain their established history. Dated additions explain newer observations without rewriting old test counts or release claims.

For a code or dependency change, first record the new source SHA and identify which API, unit, parameter, dataset, workflow and UI assertions changed. Replace relevant immutable source citations only after reviewing the new implementation. A successful parser is not semantic coverage, and a hash proves identity rather than mathematical correctness.

## Change-to-document map

| Changed source | Required documentation/recheck |
| --- | --- |
| `optimize.py`, `evaluate.py`, `direct.py` | Equations, probability/time conventions, public signatures, labs, edge-case tolerances and numerical parity |
| `data_loader.py`, `preprocessing.py` | Generation/rights, UTC/local-time and feature-availability assumptions, feature units, splits and gaps |
| `models.py`, Phase 2/3 | Losses, selected hyperparameters, data partitions, comparator identity, residual calibration, runtime scope |
| `app.py`, web engine/app | Payload schema, emitted/handled controls, persistence/import rules, loopback and stale-response behavior |
| Snapshot/results | Actual source CSV hashes, generation timestamp, recomputed revenue scope, model IDs; preserve separate run histories |
| Workflow/hosting configuration | Required check names, triggers, permission/policy evidence and publication provenance; do not infer provider state from YAML alone |
| CFF/license/security | Preserve actual author and rights decisions; schema validation plus human semantic review |

These relationships follow the current [architecture](../developer/ARCHITECTURE.md) and source locators in each corresponding page.

## Regenerate the handbook

```sh
python docs/reference/build_reference.py
```

The helper reads `docs/reference/chapters.json`, renders the canonical files through Pandoc and writes `docs/reference/index.html`. It uses MathML, local CSS, a restrictive CSP, semantic navigation and scrollable keyboard-focusable tables. Source images that are external or outside the published docs tree become readable links rather than blocked image tags. Already-linked images remain free of nested anchors. It does not download or edit original images. Directory links resolve a real published `index.html`; an unindexed directory is rejected instead of emitted as a broken page.

Review the generated HTML and repeat the command to establish determinism. Check all chapter links, local fragments, source links and safe image fallbacks. Run focused renderer cases for escaping, unsupported/active HTML, image nesting and CSP. A static check does not replace visual/browser acceptance; this worker's Chromium process could not launch.

## Evidence and drift checklist

1. Keep source, tested, candidate, PR-head, merged and deployed identities separate, with UTC times.
2. Record every tracked Git entry, including generated/vendor/media directories and files. Use indexed-only or unresolved dispositions when semantic inspection did not occur.
3. Account for Python declarations, CLI options, HTTP paths, JS/TS exports, browser control emitters and their handlers. Static dynamic patterns stay explicitly unresolved until exercised or exhaustively inspected.
4. Execute documented examples in an isolated copy; record exact dependencies and outputs. Preserve initial failures and their environment corrections.
5. Validate required outputs, current source-line bounds, local filenames/anchors, CFF1.2 schema, math rendering and full authorized diff. Never stage operational logs or large new runtime artifacts.
6. Obtain independent review of the frozen candidate. If it changes, invalidate the prior binding and retain the old report before a new review.
7. After approved integration, verify actual candidate checks and deployment content. Update the portfolio only with public-safe, dated outcomes.

## Review rhythm and ownership

Suggested maintainer cadence is a brief source/docs drift review at every code PR, dependency/replay review each quarter, and a release evidence check when an actual release is proposed. These are recommendations, not a newly adopted support commitment. Roadmap roles are proposed responsibilities; the repository owner must assign people. Preserve [security reporting](../../SECURITY.md) and the source's [CI economics](../../AGENTS.md) instructions.
