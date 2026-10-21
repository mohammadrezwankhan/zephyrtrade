# Alternatives and adjacent tools: ZephyrTrade

ZephyrTrade generates synthetic wind, weather and price tables, compares forecast and direct-offer strategies, and reconciles hypothetical revenue. Its Python and browser engines expose the assumptions so a researcher can inspect numerical agreement instead of relying on a dashboard alone.

These are current, primary-source comparisons of adjacent scope, checked on 2026-09-30. They are not a recommendation for regulated or operational use and do not claim feature parity. Repository language is GitHub's dominant-language field, not the entire stack. Licences below are repository metadata; inspect the upstream terms for a specific distribution.

| Tool | Documented scope | Main repository language | Licence metadata |
|---|---|---|---|
| [wind-python/windpowerlib](https://github.com/wind-python/windpowerlib) | Wind turbine and farm output modelling | Python | MIT |
| [PyPSA/PyPSA](https://github.com/PyPSA/PyPSA) | Power-system analysis and optimization library | Python | MIT |
| [pvlib/pvlib-python](https://github.com/pvlib/pvlib-python) | Photovoltaic performance modelling library | Python | BSD-3-Clause |

## When this repository is useful

Use ZephyrTrade to inspect **forecast and offer strategies** around **synthetic weather and prices** and see **revenue and parity evidence** in its delivered interface. Its contribution is the supplied domain example, source trail and testable boundaries. An adjacent framework may be a better starting point when its larger operational scope is the requirement; this demo does not claim to replace it.

For one small calculation or record filter, a short script is reasonable. This repository becomes useful when the interaction, saved state, evidence labels and failure behavior need to be reviewed together. No speed, accuracy, cost or adoption advantage has been measured against the tools above. No interoperability or API compatibility is implied.

## Primary evidence

- [wind-python/windpowerlib README](https://github.com/wind-python/windpowerlib/blob/dev/README.rst); latest repository push timestamp reported by GitHub: `2024-02-20T20:59:41Z`.
- [PyPSA/PyPSA README](https://github.com/PyPSA/PyPSA/blob/master/README.md); latest repository push timestamp reported by GitHub: `2026-09-29T11:42:28Z`.
- [pvlib/pvlib-python README](https://github.com/pvlib/pvlib-python/blob/main/README.md); latest repository push timestamp reported by GitHub: `2026-09-28T09:57:07Z`.
