# Governance, purpose and scope

ZephyrTrade is a public synthetic wind-market research and teaching repository. It generates hypothetical data, compares forecasting/direct-offer strategies, evaluates ordered two-price settlement and exposes inspectable local/browser examples. It does not place orders, hold accounts, ingest live feeds or certify prospective strategy performance. These boundaries are visible in the package, local API, source provenance and browser publication configuration. [pyproject.toml](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/pyproject.toml) [src/zephyrtrade/app.py](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py) [data/raw/provenance.json](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/data/raw/provenance.json) [cloudflare.json](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/cloudflare.json)

## Known ownership and policy

The repository is `mohammadrezwankhan/zephyrtrade`. The preserved CFF credits **ZephyrTrade contributors**, retains the preview release identity and declares MIT. This package does not invent an individual author, DOI, citation release or new license grant. The existing [security policy](../../SECURITY.md), [contribution guide](../../CONTRIBUTING.md), [code of conduct](../../CODE_OF_CONDUCT.md) and [support guidance](../../SUPPORT.md) remain authoritative. [CITATION.cff](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/CITATION.cff) [LICENSE](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/LICENSE)

| Responsibility | Suggested role, not an assertion of staffing | Review boundary |
| --- | --- | --- |
| Merge/release authority | Repository maintainer | Effective policy, required reviews/checks, expected-head integration and actual release metadata |
| Numerical/economic interpretation | Research maintainer plus independent domain reviewer | Units/signs, price regime, distributions, information timing, oracle and filtered-window limits |
| Data rights/provenance | Data steward | Synthetic versus measured source, redistribution rights, timestamps, revisions and input identities |
| Browser/documentation | Interface/docs maintainer | Emitted controls, accessibility evidence, storage/import behavior and canonical-source drift |
| Security/publication | Security and hosting maintainers | Existing secret ownership, least privilege, actual deployed bytes and rollback route |

These role assignments are proposed responsibilities, not hiring, support or response-time commitments. Independent agent QA checks the frozen package technically; it does not replace a required human review, domain approval or hosting-environment authorization.

## Allowed changes in this package

The current work adds complete documentation, narrowly extends documentation navigation and generates a local reference reading view. It preserves every calculation, test, workflow, dependency, license, security policy, model/result and original asset. Source defects and research questions are recorded as debt and roadmap proposals. Application fixes, measured-data integrations, new hosting, account systems, strategy deployment and new releases require separate reviewed work.

The 12-month roadmap is a proposal from 2026-11-19 through 2027-11-18, with suggested roles and effort ranges. Its acceptance criteria are measurable gates, not promised completion dates. Existing generic roadmap statements remain visible as historical source prose.

## Evidence and data boundaries

The retained data is synthetic. The named Bornholm farms are site proxies with configured capacities, not commercial-asset performance records. A forecast-error score, perfect-foresight capture percentage or numerical parity pass is narrower than trading validation. Negative-price filtering and missing hours limit calendar interpretation. Source and input hashes establish byte identity, not a provider's authenticity or a person's approval. [src/zephyrtrade/data_loader.py:37–110](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/data_loader.py#L37-L110) [src/zephyrtrade/evaluate.py:72–114](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/evaluate.py#L72-L114) [scripts/build_app.py:87–211](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/build_app.py#L87-L211)

Use fictional scenario inputs for public examples. Browser-origin storage and exported JSON/CSV can be read by other software on the device. Future measured-data work must establish rights, forecast issue/valid times, resolution, timezone, revisions and missing-data handling before public redistribution. The existing contribution instructions already require these distinctions. [CONTRIBUTING.md](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/CONTRIBUTING.md) [SECURITY.md](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/SECURITY.md)

## Outcome reporting

Report documentation completeness, independent QA, candidate CI, merge and publication separately. The authoring record includes a historical source CI baseline, denied classic-protection metadata and an unavailable Pages metadata route. Those limits are not resolved by local tests. Refresh effective rules and verify actual merged deployment content through the established routes before claiming delivery. See [CI/release playbook](../maintainer/CI_CD_AND_RELEASE_PLAYBOOK.md).
