# Original CI, release and publication playbook

> Source snapshot: [`29abf5d8bd6f05b1f0c027d8753f4837840215dc`](https://github.com/mohammadrezwankhan/zephyrtrade/tree/29abf5d8bd6f05b1f0c027d8753f4837840215dc), inspected 20 November 2026. This is source documentation, not a new release, test run or deployment receipt.

## Required original checks

The existing [CI workflow](../../.github/workflows/ci.yml) runs a Python 3.11/3.12 Ubuntu matrix and pinned Linux Python 3.13.5 reproducibility, Ruff lint/format, Python pytest with warnings treated as errors, browser numerical tests, Python/Node SciPy parity and distribution builds. Additional configured workflows include Cloudflare, CodeQL, hardened CI, traceability sync, dashboard checks and preview. Their exact trigger and required status context must be read from GitHub at the actual PR head.

A queued workflow is **not** a pass. Supplemental CircleCI, Buildkite or Azure validations have separate scopes and must not replace any required GitHub Actions producer. Never weaken workflow permissions or branch protections to accelerate merge.

## Safely promote a change

1. Record default-branch and candidate-head SHAs; check diff, protected source and any review feedback.
2. Run local targeted tests when possible, and obtain original GitHub Actions checks **for the final head or applicable merge queue ref**.
3. Verify branch protection, signed commit requirements, review policy and all required checks. If the connector cannot read policy, do not infer its absence.
4. Only then merge using an expected-head SHA guard; re-read the actual merged main SHA and source tree.
5. Re-run applicable post-merge checks and separately verify the exact release artifact/provider publication receipt. Updating `README` or passing CI does not publish a website.

## Separate Cloudflare routes

[docs/CLOUDFLARE.md](../CLOUDFLARE.md) documents the dedicated-domain output `.cloudflare/site` and separate multi-app output `.cloudflare/app`. Do not overwrite a collection deployment with a single-app artifact. Preserve origin, content hash, CSP and noindex/canonical contracts. The present documentation PR does not request any deploy, live trade integration, tag or release.
