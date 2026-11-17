# Changelog

All notable changes to MetaMetrics Python will be documented in this file.

## [1.0.0] - 2026-11-16

### Added
- Complete Python port of MetaMetrics from PHP with full functional and test parity.
- **Foundation Layer**:
  - `MetaConfig`: immutable credential model with redaction and unpickling safeguards.
  - `MetaClient`: low-level HTTP client wrapping `httpx` with safe header filtering.
  - `MetaAds`: primary facade coordinating all entity and analytics services.
  - Typed exception hierarchy rooted at `MetaAdsError` with diagnostic context isolation.
  - Standard error parser and mapper matching Meta error codes and headers.
  - Utility sanitizers and strictly validated numeric and ISO date parsers.
- **Entity Services & Pagination**:
  - `AuthenticationService`, `AccountService`, `CampaignService`, `AdSetService`, and `AdService`.
  - Typed query builders with allowlist field validation and filter encoding.
  - Cursor-based `Paginator` with repeat-cursor loop guards.
- **Insights & Metrics Engine**:
  - Full catalogue of 12 foundational and derived metrics.
  - `MetricRegistry` with dependency validation and topological resolution.
  - `MetricCalculator` implementing safe division-by-zero derived metric math.
  - `MetricAggregator` validating multi-day rows, overlap rejection, and recalculating metrics.
  - Comprehensive action and action value parsers for purchase tracking.
- **Historical & Hierarchy Analysis**:
  - `HistoricalService`: delivery evidence discovery and validation across reporting periods.
  - `HierarchyService`: reconstruction of campaign-to-adset-to-ad tree structures.
- **Tracking URL Parser**:
  - `TrackingUrlParser`: parses and maps UTM parameters and Meta identifiers from URLs.
- **Documentation & Examples**:
  - Full suite of 10 architecture and guide documents under `docs/`.
  - 8 runnable examples under `examples/`.
