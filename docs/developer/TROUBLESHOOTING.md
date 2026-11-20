# Troubleshooting by boundary

> Source snapshot: [`29abf5d8bd6f05b1f0c027d8753f4837840215dc`](https://github.com/mohammadrezwankhan/zephyrtrade/tree/29abf5d8bd6f05b1f0c027d8753f4837840215dc), inspected 20 November 2026. This is source documentation, not a new release, test run or deployment receipt.

| Symptom | Check first | Safe resolution path |
| --- | --- | --- |
| `python: No module named zephyrtrade` | Active virtual environment and editable install | Follow [setup](SETUP_AND_REPRODUCIBILITY.md) using `python -m pip install -e ".[dev]"` |
| HTTP 403 on local page | Browser Host header and actual loopback port | Use `http://127.0.0.1:<port>`; never disable host validation |
| HTTP 404 for asset | The [fixed asset allowlist](../../src/zephyrtrade/app.py) | Correct the route or add an explicitly tested asset |
| LP raises a price-order error | `down ≤ day-ahead ≤ up` and `up > down` | Repair fictional inputs, not the validation guard |
| LP rejects scenarios | All values finite, count 1–100, each in [0, capacity] | Preserve a minimal sanitized case and identify the rejected field |
| `revenue_capture_pct` is `None` | Non-positive perfect-foresight benchmark | Render *undefined* rather than treating it as 0% |
| Browser/Python objective mismatch | Correct source ref, browser module, Node and Python versions | Run `scripts/verify_engines.py` with its seeded inputs; retain exact failure and compare equations |
| CI pending forever | Matching GitHub runner labels and job queue | Inspect actual Actions run/jobs; preserve the required check and escalate runner capacity |
| Hosted demo differs from source | Bundle digest, release artifact, deployed origin and source revision | Rebuild and validate via [Cloudflare instructions](../CLOUDFLARE.md), then verify actual provider receipt |

Avoid printing secrets or private scenario records. A failed demo or browser screenshot is not proof that an optimizer has a scientific defect; isolate the layer before modifying source.
