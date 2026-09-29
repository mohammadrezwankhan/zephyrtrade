# Champion 1.1.0 — local research candidate

Adds the offline research interface, optional loopback SciPy API, focused numerical boundary repairs, validation and export workflows. See docs/champion/AUDIT_AND_RELEASE.md for evidence and limits. No production release occurred.

# Changelog

All notable changes to ZephyrTrade are documented in this file.

The project follows semantic versioning.

## 1.0.0 - 2026-07-13

### Added

- Deterministic synthetic data for four Bornholm wind-farm proxies and DK2
  market prices, including negative-price filtering and provenance.
- Leakage-safe lagged, rolling, climate, directional, and calendar features.
- Explicit stochastic trading LP and exact critical-fractile offer solution.
- OLS, batch gradient descent, polynomial, locally weighted, Ridge, Lasso, and
  k-means local regression models.
- Direct continuous offer regression and probabilistic bid-bracket
  classification.
- Chronological statistical and realized-revenue backtests with publication
  figures and interval-level audit artifacts.
- One-command pipeline with environment metadata and SHA-256 output hashes.
- Automated tests, Ruff quality gates, GitHub Actions CI, final report,
  citation metadata, and MIT license.

### Research limitations

- Default observations and profitability results are synthetic.
- Negative prices are filtered to follow the project specification.
- The indirect backtest uses realized prices ex post.
- The perfect-foresight direct target equals realized production under the
  maintained single-scenario price ordering.
