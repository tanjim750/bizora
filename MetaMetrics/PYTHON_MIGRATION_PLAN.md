# MetaMetrics PHP to Python Migration Plan

> **Revision 2** — rewritten after a full read of the PHP source (`src/`, `tests/`, `examples/`, `docs/`).
> Section 12 lists every change made relative to Revision 1 and why.

## Migration status

| Phase | Scope | Status |
|---|---|---|
| 0 | Parity harness (golden request fixtures) | ✅ complete — request & meta JSON fixtures |
| 1 | Foundation (exceptions, config, client, errors, diagnostics, query, auth, facade) | ✅ complete |
| 2 | Entity services + pagination | ✅ complete |
| 3 | Insights + metrics engine | ✅ complete |
| 4 | Historical + hierarchy | ✅ complete |
| 5 | Tracking URL parser | ✅ complete |
| 6 | Test parity hardening | ✅ complete — 384 unit tests, 96% coverage, ruff and mypy --strict clean |
| 7 | Docs, examples, release | ✅ complete — GETTING_STARTED.md, docs/ (10 files), examples/ (8 files), CI workflow |

The Python package lives at the repository root in `metametrics/`, alongside the original
`MetaMetrics-php/` checkout.

---

## 1. Project understanding summary

The PHP project is a framework-independent Meta Marketing API client **library**, not an application.
It has zero runtime dependencies beyond `ext-curl`, no framework hooks, no environment loading, and no
logger wiring inside `src/` (the `src/Logging/` classes are referenced only by one test).

Real module inventory (123 PHP files total — 89 in `src/`, 26 in `tests/`, 8 in `examples/`; ~10.7k lines):

| PHP namespace | Responsibility | Files |
|---|---|---|
| `MetaMetrics\` | `MetaAds` facade wiring one shared client into services | 1 |
| `Config\` | `MetaConfig` (immutable, validated, redacted) + `ConfigurationValidator` | 2 |
| `Client\` | `MetaClient` (cURL), `MetaClientInterface`, `Request`, `Response`, `JsonResponseDecoder` | 6 |
| `Client\Pagination\` | `Paginator` (cursor loop + repeat-cursor guard), `PaginationResult` | 2 |
| `Authentication\` | `AuthenticationService`, `AuthenticationResult`, `MetaError`, `MetaErrorParser`, `MetaErrorMapper` | 5 |
| `Account\` | `AccountService`, `AccountDTO`, `AccountNormalizer` | 3 |
| `Campaign\` | `CampaignService`, `CampaignDTO`, `CampaignNormalizer`, `CampaignQuery` | 4 |
| `AdSet\` | `AdSetService`, `AdSetDTO`, `AdSetNormalizer`, `AdSetQuery` | 4 |
| `Ad\` | `AdService`, `AdDTO`, `AdNormalizer`, `AdQuery` | 4 |
| `Insights\` | `InsightsService`, `InsightsQuery`, `InsightsDTO`, `InsightsRawData`, `InsightsResponse`, `InsightsLevel`, `InsightsFilterField` | 7 |
| `Insights\DateRange\` | `DateRange`, `DatePreset`, `AccountTimezone` | 3 |
| `Insights\Metric\` | `Metric`, `MetricType`, `MetricUnit`, `MetricAggregation`, `MetricDefinition`, `MetricRegistry`, `MetricCalculator`, `MetricAggregator`, `MetricAggregationResult`, `PurchaseActionMapping` | 10 |
| `Insights\Parser\` | `InsightsParser`, `ActionParser`, `ActionValueParser` | 3 |
| `Insights\Normalizer\` | `InsightsNormalizer` | 1 |
| `Historical\` | `HistoricalService`, `HistoricalQuery`, `HistoricalLevel`, `HistoricalResult`, `HistoricalResponse`, `DeliveryDiscovery(+Interface)`, `DeliveryAssessment`, `DeliveryEvidence`, `DeliveryStatus` | 9 |
| `Hierarchy\` | `HierarchyService`, `HierarchyNode`, `HierarchyResult` | 3 |
| `Tracking\` | `TrackingUrlParser`, `TrackingIdentifiers` | 2 |
| `Query\` | `Fields`, `Filter`, `FilterOperator`, `QueryBuilder` | 4 |
| `Exception\` | 10 exception classes rooted at `MetaAdsException` | 10 |
| `Support\` | `DiagnosticSanitizer` (used) + `Arr`, `Collection`, `Number` (**empty files — drop**) | 4 |
| `Logging\` | `LoggerInterface`, `NullLogger` (**not wired into `src/` — drop or keep as optional adapter**) | 2 |

Non-code assets to port: `README.md`, `GETTING_STARTED.md`, 10 files in `docs/`, 8 scripts in `examples/`,
22 unit test files + 1 integration test file, 2 fixture files under `tests/Fixtures/MetaResponses/`.

### Behavioural contract that must survive the port

1. `MetaAds` exposes `authentication()`, `account()`, `campaigns()`, `adSets()`, `ads()`, `insights()`,
   `historical()`, `hierarchy()`, `client()` — all backed by **one** shared client instance.
2. The HTTP client is **GET-only**, sends `Accept: application/json` + `Authorization: Bearer <token>`
   (token is *never* placed in the URL), and returns responses — it does **not** raise on HTTP failure.
   Mapping raw failures into typed exceptions is the job of the service layer.
3. `Response::isSuccessful()` is stricter than "2xx": it is `2xx` **and** the decoded body has no `error` key.
4. Every service catches its own non-2xx response and converts it via `MetaErrorMapper`.
5. Normalizers are hand-written and raise `UnexpectedResponseException` with field-specific messages.
6. The metric pipeline is: `MetricRegistry` (dependency resolution) → `InsightsParser` (raw payload →
   foundational values) → `MetricCalculator` (derived metrics) → `InsightsNormalizer` → `InsightsDTO`.
7. `InsightsDTO` exposes **two** metric maps: requested metrics (incl. derived) and *foundational* metrics.
8. Currency is resolved from `account_currency` on the insight row, falling back to a live
   `AccountService.get_currency()` call, and conflicting currencies across rows are a hard error.
9. `HistoricalService` always augments requested metrics with the delivery-evidence metrics
   (`impressions`, `spend`, `reach`) and filters out entities with no delivery.
10. `HierarchyService` regroups campaign/ad-set/ad results by `(parent id, date_start, date_stop)` and
    buckets orphans into `unattached_adsets` / `unattached_ads`.

---

## 2. Functional scope to preserve

### Core APIs

- `MetaConfig` — access token, ad account ID (`123` → `act_123` normalisation), API version (`vXX.X`),
  redaction on dump, refusal to be restored from a redacted payload.
- `MetaAds` facade with dependency injection of an optional `MetaClientInterface`.
- Authentication validation against the configured Ad Account (`GET /{v}/{act_id}?fields=id`).
- `AccountService.get()` and `AccountService.get_currency()`.
- `CampaignService.all(query)` / `.find(id, fields?)`.
- `AdSetService.all(query)` / `.for_campaign(campaign_id, query)` / `.find(id, fields?)`.
- `AdService.all(query)` / `.for_campaign(id, query)` / `.for_ad_set(id, query)` / `.find(id, fields?)`.
- Raw low-level access via `meta.client().send(Request(...))`.

### Analytics

- Account / Campaign / Ad Set / Ad level Insights with `InsightsQuery`.
- Daily (`time_increment=1`) and aggregate reporting periods.
- `Metric` enum + `MetricRegistry` dependency resolution + derived metric computation.
- `Fields` selection with required-field merging and per-service allow-listing.
- `Filter` + `FilterOperator` + `InsightsFilterField` allow-list, encoded as Meta `filtering` JSON.
- `DateRange`, `DatePreset`, `AccountTimezone`.
- Account currency propagation and conflict detection.
- `MetricAggregator` — daily-row aggregation into a single period, with overlap/entity/currency validation.
- `InsightsResponse` envelope (level + currency + rows).

### Historical analysis

- `DeliveryDiscovery` / `DeliveryAssessment` / `DeliveryEvidence` / `DeliveryStatus`.
- `HistoricalQuery`, `HistoricalService.get()` / `.get_response()`, plus
  `.campaigns()` / `.ad_sets()` / `.ads()` shortcuts.
- `HistoricalResult` with cross-field validation (period containment, evidence↔metric agreement).
- `HistoricalResponse` envelope.

### Support features

- Cursor pagination with repeat-cursor detection.
- Ad Set **configuration enrichment** (`optimization_goal`, `promoted_object`) for Ad Set-level Insights.
- Tracking URL parsing with configurable parameter mapping and `utm_campaign` fallback.
- `DiagnosticSanitizer` — URL / message / header redaction.
- Typed exception hierarchy with a safe, allow-listed diagnostic context.
- `InsightsRawData` — verbatim `spend`, `actions`, `cost_per_action_type` payloads.

---

## 3. Target architecture in Python

### Package layout

```text
metametrics/
  __init__.py
  py.typed
  config.py                     # MetaConfig, ConfigurationValidator
  client.py                     # MetaClient, MetaClientProtocol, Request, Response, JsonResponseDecoder
  meta_ads.py                   # MetaAds facade
  exceptions.py                 # full exception hierarchy
  errors/
    __init__.py
    model.py                    # MetaError value object
    parser.py                   # MetaErrorParser
    mapper.py                   # MetaErrorMapper
  auth/
    __init__.py
    service.py                  # AuthenticationService
    result.py                   # AuthenticationResult
  account/
    __init__.py
    service.py
    dto.py
    normalizer.py
  campaign/
    __init__.py
    service.py
    dto.py
    normalizer.py
    query.py
  adset/
    __init__.py
    service.py
    dto.py
    normalizer.py
    query.py
  ad/
    __init__.py
    service.py
    dto.py
    normalizer.py
    query.py
  insights/
    __init__.py
    service.py
    query.py
    level.py                    # InsightsLevel
    filter_fields.py            # InsightsFilterField
    dto.py                      # InsightsDTO
    raw_data.py                 # InsightsRawData
    response.py                 # InsightsResponse
    date_range/
      __init__.py
      range.py                  # DateRange
      timezone.py               # AccountTimezone
      preset.py                 # DatePreset
    metrics/
      __init__.py
      metric.py                 # Metric
      types.py                  # MetricType, MetricUnit, MetricAggregation
      definition.py             # MetricDefinition
      registry.py               # MetricRegistry
      calculator.py             # MetricCalculator
      aggregator.py             # MetricAggregator
      aggregation_result.py     # MetricAggregationResult
      purchase_actions.py       # PurchaseActionMapping
    parsers/
      __init__.py
      insights_parser.py
      action_parser.py
      action_value_parser.py
    normalizer.py
  historical/
    __init__.py
    service.py
    query.py
    level.py                    # HistoricalLevel
    delivery.py                 # DeliveryDiscovery(+Protocol), DeliveryAssessment, DeliveryEvidence, DeliveryStatus
    result.py                   # HistoricalResult
    response.py                 # HistoricalResponse
  hierarchy/
    __init__.py
    service.py
    node.py                     # HierarchyNode
    result.py                   # HierarchyResult
  tracking/
    __init__.py
    parser.py                   # TrackingUrlParser
    identifiers.py              # TrackingIdentifiers
  query/
    __init__.py
    fields.py                   # Fields
    filters.py                  # Filter, FilterOperator
    builder.py                  # QueryBuilder
  pagination/
    __init__.py
    paginator.py                # Paginator
    result.py                   # PaginationResult
  utils/
    __init__.py
    diagnostics.py              # DiagnosticSanitizer
    dates.py                    # parse_datetime, parse_date
    numbers.py                  # to_finite_float, to_strict_int
    payload.py                  # PayloadReader (strict field extraction)
    json.py                     # php_json_dumps (PHP-compatible encoding)
tests/
  ...
examples/
  ...
docs/
  ...
```

**Deviations from Revision 1 and why**

- `errors/` is a top-level package, not `auth/errors.py`. `MetaErrorMapper` is used by *every* service
  (Account, Campaign, AdSet, Ad, Insights, Paginator), not only by authentication. Placing it under
  `auth/` would be misleading.
- `insights/metrics/` is a sub-package rather than a flat `metrics.py`, because the PHP module holds
  10 collaborating classes.
- `insights/date_range/` keeps `DateRange`, `AccountTimezone` and `DatePreset` separate — they are three
  distinct value objects with distinct validation rules.
- The `typing/` package was removed; it is an anti-pattern in Python. Typing is delivered via the
  `py.typed` marker (PEP 561) instead.
- `Support\Arr`, `Support\Collection`, `Support\Number` are **empty files** in PHP and are not imported
  anywhere. They are dropped.
- `Logging\LoggerInterface` / `NullLogger` are **not wired into `src/`** — only one test touches them.
  They are dropped; the sanitized exception context is the supported logging surface.

### Design principles

- Zero-framework library; `httpx` is the only runtime dependency.
- Explicit dependency injection for the client and for every collaborator (normalizers, parsers,
  paginator, error mapper) — same seam the PHP code exposes via optional constructor arguments.
- Immutable value objects (`frozen=True` dataclasses).
- Validate early, raise the library's own exception types — never bare `ValueError`/`TypeError`.
- Keep Meta payload parsing isolated from metric business logic.
- Strict typing end-to-end; `py.typed` + `mypy --strict` on the package.

---

## 4. Recommended Python tech stack

### Runtime

- Python **3.11+** (Revision 1 said 3.12). 3.11 is the floor because the port uses
  `enum.StrEnum` (for `Metric.SPEND.value == "spend"` parity), `typing.Self`, and `datetime.UTC`.
- `uv` for dependency management and task running (`uv add`, `uv run pytest`, `uv build`).

### Core dependencies

```toml
dependencies = [
  "httpx>=0.27,<1.0",
]
```

**Pydantic is deliberately NOT a core dependency** (see §12 for the reasoning). `pydantic` is offered
only as an optional extra:

```toml
[project.optional-dependencies]
models = ["pydantic>=2.10,<3.0"]
```

### Dev tooling

```toml
[dev-dependencies]
pytest = ">=8.3,<9.0"
pytest-cov = ">=5.0,<7.0"
respx = ">=0.22,<1.0"
ruff = ">=0.6,<1.0"
mypy = ">=1.11,<2.0"
```

- `respx` over `pytest-httpx`: it routes on method + URL pattern, which is what the pagination and
  Ad Set-enrichment tests need.
- `mypy --strict` on `metametrics/`; `ruff check` + `ruff format`.

### Packaging

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "metametrics"
version = "1.0.0"
description = "Framework-independent Python library for the Meta Marketing API."
readme = "README.md"
requires-python = ">=3.11"
license = "MIT"
dependencies = ["httpx>=0.27,<1.0"]

[tool.hatch.build.targets.wheel]
packages = ["metametrics"]

[tool.mypy]
strict = true
packages = ["metametrics"]
```

`py.typed` must be shipped inside the wheel (add `metametrics/py.typed` to the package data).

---

## 5. Detailed mapping from PHP to Python

### 5.1 Configuration

`MetaConfig` → frozen dataclass.

```python
@dataclass(frozen=True, slots=True)
class MetaConfig:
    access_token: str
    ad_account_id: str
    api_version: str

    def __post_init__(self) -> None: ...
```

- `ConfigurationValidator.validate_access_token` → non-empty after `strip()`.
- `ConfigurationValidator.normalize_ad_account_id` → `^\d+$` ⇒ prefix `act_`; then must match
  `^act_\d+$`; else `InvalidConfigurationError`.
- `ConfigurationValidator.validate_api_version` → must match `^v\d+\.\d+$`.
- PHP's `__debugInfo()` → implement `__repr__` with `access_token='[REDACTED]'` **and**
  `__getstate__`/`__setstate__` that raise, so a `MetaConfig` can never be unpickled back into a
  credential-bearing object (PHP blocks `__unserialize` for exactly this reason).

### 5.2 Entry point and service composition

```python
class MetaAds:
    def __init__(self, config: MetaConfig, client: MetaClientProtocol | None = None) -> None: ...
    def authentication(self) -> AuthenticationService: ...
    def account(self) -> AccountService: ...
    def campaigns(self) -> CampaignService: ...
    def ad_sets(self) -> AdSetService: ...
    def ads(self) -> AdService: ...
    def insights(self) -> InsightsService: ...
    def historical(self) -> HistoricalService: ...
    def hierarchy(self) -> HierarchyService: ...
    def client(self) -> MetaClientProtocol: ...
```

PHP returns a **new** service instance per call. The Python port caches them in `functools.cached_property`
so that `meta.insights()` twice returns the same object (important because `HistoricalService` and
`HierarchyService` are built *on top of* the insights service). This is a deliberate, documented
improvement — the observable behaviour (same client, same config) is unchanged.

### 5.3 HTTP layer

- `MetaClientInterface` → `typing.Protocol` named `MetaClientProtocol` with `send(request) -> Response`.
- `MetaClient` → wraps `httpx.Client`.
  - `base_url = "https://graph.facebook.com"`, `timeout = httpx.Timeout(30.0, connect=10.0)`.
  - `follow_redirects = False` (PHP cURL does not follow redirects by default).
  - Headers: `Accept: application/json`, `Authorization: Bearer <token>`, `User-Agent: MetaMetrics/1.0`.
  - `send()` maps transport failures to `NetworkError(retryable=True)`:
    `httpx.TimeoutException`, `httpx.ConnectError`, `httpx.NetworkError` → `NetworkError`;
    `httpx.HTTPError` (other) → `NetworkError`.
  - Non-GET method → `InvalidInputError`.
  - Path must start with `/` and must not contain `?` → else `InvalidInputError`.
  - Response headers are lower-cased and filtered through `DiagnosticSanitizer.sanitize_headers`.
  - `httpx.Client` is closable: expose `close()` and support the context-manager protocol;
    `MetaAds` exposes `close()` / `__enter__` / `__exit__` too.

### 5.4 Request / Response

- `Request` → frozen dataclass with `method: str`, `path: str`, `query: Mapping[str, Scalar]`.
  `with_query_parameter(name, value)` returns a new `Request`.
- `Response` → frozen dataclass with `status_code: int`, `body: Any`, `raw_body: str | None`,
  `headers: Mapping[str, str]` (lower-cased). `is_successful()` implements
  `200 <= status < 300 and not (isinstance(body, dict) and "error" in body)`.
- `JsonResponseDecoder` → `json.loads` with `json.JSONDecodeError` → `UnexpectedResponseError`.

### 5.5 Response and exception model

See the table in §7 for the exact PHP → Python mapping.

Additional parity rules:

- The base class derives from `RuntimeError` (PHP's `MetaAdsException extends RuntimeException`).
- The base exception keeps the PHP constructor arguments:
  `meta_error_code`, `meta_error_subcode`, `meta_error_type`, `trace_id`, `http_status`,
  `retryable`, `retry_after_seconds`, `resource_type`, `resource_id`, `safe_context`.
- `context()` returns the same allow-listed, `None`-filtered dict as PHP, with the same key names.
- `safe_context` is validated on construction exactly as in PHP:
  values must be scalars/None; keys matching `token|secret|authorization|appsecret|credential`
  (case-insensitive) are rejected; keys must be a subset of
  `{"x_ad_account_usage", "x_app_usage", "x_business_use_case_usage"}`.
  The rejection raises `ValueError` (PHP raises `\InvalidArgumentException`) — it is a programming
  error, not a Meta failure, so it must **not** be a `MetaAdsError`.
- `to_dict()` mirrors `__debugInfo()`; `__str__`/`__repr__` never leak the token.

### 5.6 DTOs and query objects

- DTOs → frozen dataclasses with `Optional[...]` fields matching PHP nullability exactly.
- `CampaignDTO.created_time` / `updated_time` → `datetime | None`, always converted to **UTC**
  (PHP: `DateTimeImmutable::setTimezone(UTC)`).
- PHP accessor style `->id()` becomes Python attribute access `dto.id`.
  (PHP `->id()` and the property `id` are not both usable; Python attribute access is the idiomatic
  equivalent.)
- Query objects (`CampaignQuery`, `AdSetQuery`, `AdQuery`, `InsightsQuery`, `HistoricalQuery`) →
  frozen dataclasses with `__post_init__` validation. `metrics`/`filters` lists are stored as
  de-duplicated tuples (PHP de-duplicates metrics by enum value and keeps filter order).

### 5.7 Metrics and filters

- `Metric`, `MetricType`, `MetricUnit`, `MetricAggregation`, `InsightsLevel`, `HistoricalLevel`,
  `FilterOperator`, `DeliveryStatus`, `DatePreset` → `enum.StrEnum` (keeps `.value` parity).
- `Filter` → frozen dataclass; validation mirrors PHP:
  field must match `^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)?$`; list values must be scalars;
  `IN`/`NOT_IN` require a non-empty list; other operators require a scalar.
- `Fields` → frozen dataclass; non-empty; each field must match `^[a-z][a-z0-9_]*$`;
  `with_required(fields)` merges and de-duplicates; `to_query_value()` joins with `,`.
- `QueryBuilder.encode_filters(filters, allowed_fields)` → returns a JSON **string** or `None`;
  rejects unknown filter fields with `InvalidInputError`.

### 5.8 Metric registry, parser, normalizer, calculator

This is the highest-risk area and must be ported **statement for statement**.

- `MetricRegistry` keeps the same catalogue (12 metrics) and the same constructor validation:
  duplicate definition → `UnsupportedMetricError`; catalogue must cover **exactly** the `Metric` enum
  (no missing, no extra); dependencies must resolve; circular dependency → `UnsupportedMetricError`.
- `MetricDefinition` validation is preserved verbatim: derived metrics must have dependencies and no
  Meta fields; foundational metrics must have Meta fields and no dependencies;
  `is_derived` must equal `aggregation is RECALCULATE`; duplicate fields/dependencies rejected.
- `MetricCalculator` — same formulas, same `None` semantics:
  `COST_PER_PURCHASE = spend / purchases`, `ROAS = purchase_value / spend`,
  `CPC = spend / clicks`, `CTR = clicks / impressions * 100`, `CPM = spend / impressions * 1000`.
  Division by zero (or by a `None` operand) → `None`. Non-finite results → `InvalidInputError`.
- `MetricAggregator` — sorts rows by `(date_start, date_stop)`, validates that all rows share one
  entity, level and currency, rejects **overlapping** reporting periods
  (`row.date_start <= previous.date_stop` → error), sums `SUM` metrics, returns `None` for
  `META_ONLY` metrics when more than one row is present (`reach` is `META_ONLY`), and re-derives
  derived metrics through `MetricCalculator`.
- `PurchaseActionMapping` — the 6 default action types, non-empty, no duplicates, all non-blank.
- `ActionParser` / `ActionValueParser` — same "first matching action type wins" ordering, same
  duplicate-action-type rejection, same `None` vs `0.0` distinction:
  - `actions` is `None` → metric is `None`;
  - `actions` is present but contains no purchase action type → `0.0`;
  - `actions` present, contains a purchase type, but the *shared* type is `None`
    (i.e. `actions` and `action_values` disagree) → `None`.
- `InsightsParser` — same field mapping per level, same strict typing of every raw value,
  `account_currency` must match `^[A-Z]{3}$`.
- `InsightsNormalizer` — produces `InsightsDTO` with **both** `metrics` (requested, derived included)
  and `foundational_metrics`.

### 5.9 Ad Set configuration enrichment

`InsightsService` performs an extra `GET /{v}/{adset_id}?fields=id,optimization_goal,promoted_object`
per distinct `adset_id` when the level is `adset` **and** `include_ad_set_configuration` is true.
This is an N+1 request pattern and must be reproduced (or deliberately changed and documented).
`HistoricalService` always sets `include_ad_set_configuration=False`, so it does **not** trigger it.

### 5.10 Currency resolution

Order of precedence in `InsightsService.get()`:

1. `account_currency` present on a row → use it; two different values across rows → `UnexpectedResponseError`.
2. No row carried a currency → fall back to `AccountService.get_currency()` (a live HTTP call).
3. No rows at all → return `[]` **without** any currency lookup.
4. `get_response()` on an empty result still performs the account currency lookup, because the
   envelope requires a currency.

### 5.11 Historical and hierarchy

- `DeliveryDiscovery` — evidence metrics are `impressions`, `spend`, `reach`.
  Any of them `> 0` ⇒ `DELIVERED` with the positive indicators as evidence.
  All present but all zero ⇒ `NOT_DELIVERED`. None present ⇒ `INSUFFICIENT_EVIDENCE`
  (which `HistoricalService` turns into an `UnexpectedResponseError`).
- `DeliveryEvidence` — non-empty, keys must be valid `Metric` names, values must be positive finite floats.
- `HistoricalResult` — validates that the insight level is campaign/adset/ad, that the insight period
  is contained in the requested period, and that every evidence indicator equals the matching
  insight metric value.
- `HierarchyService` — builds the tree keyed by `(parent_id, date_start, date_stop)`; children that do
  not match the parent's level, parent id and reporting period are rejected by `HierarchyNode`;
  ad sets and ads that never attached to a parent land in `unattached_adsets` / `unattached_ads`.
- `HierarchyResult` — currency defaults to the first node's currency, or `None` when empty; all nodes
  (recursively) must share that currency; every node's requested period must equal the hierarchy's.

### 5.12 Tracking URL parsing

- `TrackingUrlParser.parse(url, parameter_mapping=None)` — the same 5 default mappings
  (`campaignId→utm_id`, `adSetId→utm_term`, `adId→utm_content`, `source→utm_source`, `medium→utm_medium`),
  the same override validation (known identifier only; parameter name must match `^[a-zA-Z][a-zA-Z0-9_-]*$`;
  all 5 names must remain unique), and the `utm_campaign` numeric fallback for `campaignId`.
- URL validation: non-empty, must parse, must have `scheme` + `host`, scheme must be `http`/`https`.

### 5.13 Diagnostic sanitiser

Port all six regexes from `DiagnosticSanitizer::sanitizeMessage` plus `sanitize_url` and
`sanitize_headers` (5 allowed response headers only).

---

## 6. Parity gotchas (critical — not covered by Revision 1)

These are the places where a naive Python port silently diverges from the PHP behaviour.

### 6.1 Query-string encoding

PHP builds the query with `http_build_query($query, '', '&', PHP_QUERY_RFC3986)`.

| Rule | PHP | Python pitfall | Required Python behaviour |
|---|---|---|---|
| Space | `%20` | `urlencode` gives `+` | use `quote_via=quote` |
| `true` | `1` | httpx gives `true` | pre-convert booleans to `1`/`0` |
| `false` | `0` | httpx gives `false` | pre-convert booleans to `1`/`0` |
| `null` | key omitted | httpx raises/skips differently | drop `None` values |
| `int` | `42` | fine | pass through |

Implement one helper used by every service:

```python
def encode_query(query: Mapping[str, Scalar | None]) -> str:
    items = [(k, _encode_scalar(v)) for k, v in query.items() if v is not None]
    return urlencode(items, quote_via=quote)
```

### 6.2 Numeric coercion

PHP's `is_numeric()` accepts numeric strings (including `" 12 "`, `"1e5"`) and rejects `bool`, `null`,
arrays, `"nan"`, `"inf"`. Python's `float()` accepts `"nan"`/`"inf"` and `bool` is a subclass of `int`.

Required helper (used by every normalizer/parser):

```python
def to_finite_float(value: object, *, error: type[MetaAdsError], message: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise error(message)
    if isinstance(value, str):
        text = value.strip()
        if not text or not _NUMERIC_RE.match(text):
            raise error(message)
        number = float(text)
    else:
        number = float(value)
    if not math.isfinite(number):
        raise error(message)
    return number
```

Also note PHP's `is_int()` rejects `true`/`false` and floats — Python must check `isinstance(x, int) and not isinstance(x, bool)`.

### 6.3 Date parsing

PHP's `DateTimeImmutable::createFromFormat('!Y-m-d', ...)` **rejects** `2026-9-1` and `2026-02-30`.
Python's `datetime.strptime("%Y-%m-%d", "2026-9-1")` **accepts** the first and `strptime` rejects the
second only inconsistently. Required pattern:

```python
date = datetime.strptime(value, "%Y-%m-%d")  # then:
if date.strftime("%Y-%m-%d") != value:
    raise InvalidInputError(...)
```

`DateRange` comparison is a plain string comparison in PHP (`since > until` on `YYYY-MM-DD` strings);
in Python compare `date` objects — equivalent because the format is fixed-width.

### 6.4 Timezones

`AccountTimezone` uses PHP's `DateTimeZone`, which accepts the IANA database plus some aliases.
Python should use `zoneinfo.ZoneInfo` and validate with `zoneinfo.available_timezones()`.
Note: `zoneinfo` needs the `tzdata` package on systems without a system tz database
(Windows, slim containers) — add `tzdata` to the dependencies for Windows support.

`DatePreset` must reproduce PHP's `modify('first day of this month')` /
`modify('last day of previous month')` semantics, including the "today" snapshot taken in the
**account's** timezone (`setTime(0, 0)`), not the caller's.

### 6.5 JSON encoding of filters and time ranges

`json.dumps` defaults to `", "` / `": "` separators; PHP's `json_encode` uses no spaces.
Meta tolerates both, but the golden-request tests will compare exact strings — use
`separators=(",", ":")`.

PHP's `json_encode` also escapes forward slashes (`/` becomes `\/`) unless
`JSON_UNESCAPED_SLASHES` is passed, and it escapes non-ASCII as `\uXXXX`. Python's
`json.dumps` does neither by default. `metametrics/utils/json.py::php_json_dumps`
reproduces PHP's defaults so that `effective_status`, `filtering`, and `time_range`
produce byte-identical query strings.

### 6.6 `array_is_list` semantics

PHP's `array_is_list()` requires keys `0..n-1` in order. Python: `isinstance(v, list)` (JSON arrays
always decode to `list`, so this matches) — but a JSON **object** decodes to `dict`, which must be
rejected where PHP would reject a non-list array.

### 6.7 `is_finite` and float overflow

`is_finite()` in PHP rejects `INF`/`NAN`. Python's `math.isfinite` is the equivalent. Note that PHP's
`(float) "1e400"` yields `INF`, and `is_numeric("1e400")` is `true` — so PHP **would** accept it and
then `is_finite` rejects it with the "must be finite" message. Python's `float("1e400")` is `inf`,
and `math.isfinite` rejects it identically. The *order* of the two checks determines the error
message, so keep "must be numeric" and "must be finite" as separate, distinct errors.

### 6.8 Exception-vs-`ValueError` boundary

`InvalidArgumentException` in PHP = a Python `ValueError`. It is used for:

- exception `safe_context` containing a sensitive/unsupported key,
- `MetaConfig` being unpickled (PHP `LogicException` ≈ Python `RuntimeError`).

Everything else must raise a `MetaAdsError` subclass.

### 6.9 `Metric::from` vs `MetricRegistry.from_name`

`Metric::from($name)` (used in `HistoricalResult`) throws `ValueError` in PHP for an unknown name.
In Python use `Metric(name)` and let `ValueError` propagate — but only after the
`DeliveryEvidence` constructor has already guaranteed the name is a valid metric.

### 6.10 `Response.is_successful()` vs HTTP status

A `200 OK` body containing `{"error": {...}}` is **not** successful. Reproduce exactly — the
`MetaErrorMapper` then maps it like any other failure.

---

## 7. Exception mapping

| PHP | Python | Notes |
|---|---|---|
| `MetaAdsException` | `MetaAdsError(RuntimeError)` | base class; carries the diagnostic fields |
| `AuthenticationException` | `AuthenticationError` | |
| `InvalidConfigurationException` | `InvalidConfigurationError` | |
| `InvalidInputException` | `InvalidInputError` | |
| `NetworkException` | `NetworkError` | `retryable=True` for transport failures |
| `PermissionException` | `PermissionDeniedError` | **not** `PermissionError` — that shadows the builtin `OSError` subclass |
| `RateLimitException` | `RateLimitError` | carries `retry_after_seconds` |
| `ResourceNotFoundException` | `ResourceNotFoundError` | |
| `UnexpectedResponseException` | `UnexpectedResponseError` | malformed payloads |
| `UnsupportedMetricException` | `UnsupportedMetricError` | metric catalogue violations |
| `\InvalidArgumentException` | `ValueError` | programming errors only |
| `\LogicException` | `RuntimeError` | e.g. unserialising `MetaConfig` |

`MetaErrorMapper` mapping table (must be reproduced exactly):

| Condition | Exception |
|---|---|
| HTTP 429 or code in `{4, 17, 32, 341, 613}` | `RateLimitError` (retryable, `retry_after_seconds` from the `Retry-After` header) |
| code in `{102, 190}` or HTTP 401 | `AuthenticationError` |
| code `10`, or code in `200..299`, or HTTP 403 | `PermissionDeniedError` |
| code `803`, subcode `33`, or HTTP 404 | `ResourceNotFoundError` |
| otherwise | `MetaAdsError` (retryable when `is_transient`, HTTP ≥ 500, or code in `{1, 2}`) |

The mapper's `safe_context` carries `x_app_usage`, `x_ad_account_usage` and
`x_business_use_case_usage` response headers (with `-` → `_`), which are exactly the three keys the
exception allow-list permits.

---

## 8. Test parity matrix

Every PHP test file gets a Python counterpart. `tests/Fixtures/MetaResponses/*.php` (which `return`
PHP arrays) become JSON fixture files.

| PHP test file | Python test file |
|---|---|
| `tests/Unit/MetaAdsTest.php` | `tests/unit/test_meta_ads.py` |
| `tests/Unit/Config/MetaConfigTest.php` | `tests/unit/test_config.py` |
| `tests/Unit/Account/AccountServiceTest.php` | `tests/unit/account/test_account_service.py` |
| `tests/Unit/Authentication/AuthenticationServiceTest.php` | `tests/unit/auth/test_authentication_service.py` |
| `tests/Unit/Authentication/ErrorHandlingTest.php` | `tests/unit/auth/test_error_handling.py` |
| `tests/Unit/Campaign/CampaignServiceTest.php` | `tests/unit/campaign/test_campaign_service.py` |
| `tests/Unit/Campaign/CampaignNormalizerTest.php` | `tests/unit/campaign/test_campaign_normalizer.py` |
| `tests/Unit/AdSet/AdSetServiceTest.php` | `tests/unit/adset/test_adset_service.py` |
| `tests/Unit/AdSet/AdSetNormalizerTest.php` | `tests/unit/adset/test_adset_normalizer.py` |
| `tests/Unit/Ad/AdServiceTest.php` | `tests/unit/ad/test_ad_service.py` |
| `tests/Unit/Ad/AdNormalizerTest.php` | `tests/unit/ad/test_ad_normalizer.py` |
| `tests/Unit/Insights/DateRangeTest.php` | `tests/unit/insights/test_date_range.py` |
| `tests/Unit/Insights/InsightsServiceTest.php` | `tests/unit/insights/test_insights_service.py` |
| `tests/Unit/Insights/MetricPipelineTest.php` | `tests/unit/insights/test_metric_pipeline.py` |
| `tests/Unit/Insights/MetricRegistryTest.php` | `tests/unit/insights/test_metric_registry.py` |
| `tests/Unit/Insights/MetricAggregatorTest.php` | `tests/unit/insights/test_metric_aggregator.py` |
| `tests/Unit/Insights/PurchaseActionMappingTest.php` | `tests/unit/insights/test_purchase_action_mapping.py` |
| `tests/Unit/Historical/DeliveryDiscoveryTest.php` | `tests/unit/historical/test_delivery_discovery.py` |
| `tests/Unit/Historical/HistoricalServiceTest.php` | `tests/unit/historical/test_historical_service.py` |
| `tests/Unit/Historical/HistoricalValueObjectTest.php` | `tests/unit/historical/test_historical_value_objects.py` |
| `tests/Unit/Hierarchy/HierarchyServiceTest.php` | `tests/unit/hierarchy/test_hierarchy_service.py` |
| `tests/Unit/Tracking/TrackingUrlParserTest.php` | `tests/unit/tracking/test_tracking_url_parser.py` |
| `tests/Integration/Authentication/AuthenticationServiceTest.php` | `tests/integration/test_authentication_live.py` |

### Test harness requirements

- A `FakeMetaClient` implementing `MetaClientProtocol`, recording every `Request` and returning
  queued `Response` objects — the Python equivalent of the PHP fakes.
- A `respx` router for true HTTP-level tests (query-string encoding, headers, timeouts).
- Golden-request assertions: the exact `path` + `query` string produced for each service must match
  the PHP fixtures byte for byte.
- Integration tests are marked `@pytest.mark.integration` and skipped unless
  `METAMETRICS_ACCESS_TOKEN` / `METAMETRICS_AD_ACCOUNT_ID` / `METAMETRICS_API_VERSION` are set.
  Default `pytest` run excludes them (`-m "not integration"` via `addopts`).

---

## 9. Suggested migration phases

### Phase 0 — Parity harness (new)

- Extract the PHP fixtures into language-neutral JSON (`tests/fixtures/meta/*.json`).
- Record the exact request path+query the PHP code produces for the golden scenarios and store them
  as `tests/fixtures/requests/*.json`. These become the Python golden assertions.

**Exit criteria:** the golden request/response fixtures exist and are reviewed.

### Phase 1 — Foundation

- `pyproject.toml`, `py.typed`, package skeleton, `ruff`/`mypy` config.
- `exceptions.py` (full hierarchy with the safe-context rules).
- `config.py` (`MetaConfig`, `ConfigurationValidator`).
- `client.py` (`MetaClient`, `Request`, `Response`, `JsonResponseDecoder`).
- `errors/` (`MetaError`, `MetaErrorParser`, `MetaErrorMapper`).
- `utils/diagnostics.py` (`DiagnosticSanitizer`).

**Exit criteria:** package installs and imports; a single authenticated GET works; config validation
and redaction behave as in PHP; every PHP exception case in `ErrorHandlingTest` has a Python twin.

### Phase 2 — Entity services

- `auth/`, `account/`, `campaign/`, `adset/`, `ad/`.
- `query/` (`Fields`, `Filter`, `FilterOperator`, `QueryBuilder`).
- `pagination/` (`Paginator`, `PaginationResult`).
- `meta_ads.py` facade.

**Exit criteria:** list/find operations match the PHP signatures; pagination, repeated cursors and
malformed payloads behave identically.

### Phase 3 — Insights and the metrics engine

- `insights/metrics/` (registry, definitions, calculator, aggregator, purchase mapping).
- `insights/parsers/`, `insights/normalizer.py`.
- `insights/` service, query, DTO, raw data, response, levels, filter fields.
- `insights/date_range/` (`DateRange`, `DatePreset`, `AccountTimezone`).
- Currency resolution and conflict detection.

**Exit criteria:** the metric pipeline produces identical numbers for identical payloads;
`MetricPipelineTest` and `MetricAggregatorTest` pass 1:1.

### Phase 4 — Historical and hierarchy

- `historical/` (query, service, delivery discovery, result, response).
- `hierarchy/` (service, node, result).

**Exit criteria:** delivery detection, evidence and hierarchy bucketing match PHP exactly.

### Phase 5 — Tracking and remaining utilities

- `tracking/` parser and identifiers.

**Exit criteria:** URL parsing works with default and custom parameter mappings; diagnostics stay secret-safe.

### Phase 6 — Test parity and hardening

- Port all 23 test files, then add the Python-specific tests:
  query-string encoding, boolean encoding, `None` dropping, strict date parsing, strict numeric
  coercion, pickling refusal, `httpx` transport-error mapping, `MetaAds` context-manager lifecycle.
- Coverage gate: `--cov-fail-under=90` on `metametrics/`.
- `mypy --strict` clean; `ruff check` clean.

### Phase 7 — Documentation, examples and release

- `README.md` (Python quick start), `GETTING_STARTED.md`.
- `docs/` — port all 10 PHP docs: `architecture.md`, `authentication.md`, `configuration.md`,
  `error-handling.md`, `campaigns.md`, `adsets.md`, `ads.md`, `insights.md`, `metrics.md`,
  `historical-data.md`.
- `examples/` — port all 8 PHP scripts (basic, campaigns, adsets, ads, insights, metrics,
  historical, hierarchy).
- `CHANGELOG.md`, CI workflow (lint → type-check → test → build), `twine`/PyPI publish step.

---

## 10. Risk areas and migration concerns

| # | Risk | Mitigation |
|---|---|---|
| 1 | **Metric semantics and currency handling** — derived metrics, purchase action-type alignment, currency fallback/conflict | Port the pipeline statement-for-statement; golden-payload tests for every metric and every action-type combination |
| 2 | **Purchase action-type alignment** between `actions` and `action_values` (the `None` vs `0.0` distinction) | Dedicated table-driven tests covering: missing `actions`, missing `action_values`, disjoint types, partial overlap |
| 3 | **Historical delivery detection** — `DELIVERED` / `NOT_DELIVERED` / `INSUFFICIENT_EVIDENCE` | Fixture-based tests for all three outcomes, including the "all present but zero" case |
| 4 | **Query-string encoding drift** (booleans, spaces, nulls) | Golden request-string assertions for every service |
| 5 | **Pagination** — cursor tracking, repeat-cursor guard, malformed `paging` payloads | Unit tests with a fake client, including a repeated-cursor page |
| 6 | **Strictness drift in numeric/date parsing** | Shared helpers with dedicated unit tests; never rely on implicit coercion |
| 7 | **Exception-contract drift** (Pydantic `ValidationError` leaking into the public API) | Frozen dataclasses + hand-written validators; a test asserting no `ValidationError` escapes |
| 8 | **Meta API changes** | `api_version` remains configurable; `MetaConfig` keeps validating `vXX.X` |
| 9 | **N+1 Ad Set configuration requests** | Documented behaviour; add an optional `include_ad_set_configuration=False` escape hatch (already in PHP) |
| 10 | **Timezone data availability** | Depend on `tzdata` so `zoneinfo` works everywhere |

---

## 11. Acceptance checklist

- [ ] `pip install .` succeeds; `import metametrics` works; `py.typed` ships in the wheel.
- [ ] Every PHP public entry point exists in Python with the same semantics.
- [ ] `MetaAds` exposes `authentication()`, `account()`, `campaigns()`, `ad_sets()`, `ads()`,
      `insights()`, `historical()`, `hierarchy()`, `client()`.
- [ ] Typed queries work for campaigns, ad sets and ads (list + find), with field selection and
      required-field merging.
- [ ] Insights support metric selection, filters, date ranges, all four levels, daily and aggregate.
- [ ] Derived metrics match PHP values exactly for every formula.
- [ ] Currency fallback and conflict detection match PHP.
- [ ] `MetricAggregator` output matches PHP, including `META_ONLY` handling and overlap rejection.
- [ ] Historical delivery detection and hierarchy reconstruction match PHP.
- [ ] Raw responses are reachable through `meta.client().send(...)` and are **not** auto-mapped.
- [ ] The exception hierarchy is complete, `context()` is safe to log, and no `ValueError`/`TypeError`
      escapes from public API misuse.
- [ ] Golden request strings match the PHP fixtures byte for byte.
- [ ] All 23 PHP test files have Python counterparts that pass; coverage ≥ 90 %.
- [ ] `mypy --strict` and `ruff check` are clean.
- [ ] `README.md`, `GETTING_STARTED.md`, all 10 `docs/` pages and all 8 `examples/` are ported.
- [ ] The library reads no environment variables and imports no framework.

---

## 12. Changes from Revision 1 (and why)

| # | Revision 1 said | Change | Reason |
|---|---|---|---|
| 1 | `PermissionError` | → `PermissionDeniedError` | `PermissionError` is a builtin (`OSError` subclass); shadowing it breaks `except PermissionError` for every consumer |
| 2 | Base class `MetaAdsError(Exception)` | → `MetaAdsError(RuntimeError)` | PHP's `MetaAdsException extends RuntimeException`; keeps `except RuntimeError` parity |
| 3 | `pydantic` as a core dependency | → removed from core; `models` extra only | Pydantic raises `ValidationError`, which breaks the typed-exception contract the library promises; hand-written validators map 1:1 to the PHP constructors |
| 4 | `auth/errors.py` | → top-level `errors/` package | `MetaErrorMapper` is used by every service, not only authentication |
| 5 | Flat `insights/metrics.py`, `insights/date_range.py` | → sub-packages `insights/metrics/`, `insights/date_range/` | 10 metric classes and 3 date-range classes, each with distinct validation rules |
| 6 | `typing/` package | → removed; `py.typed` marker instead | `typing/__init__.py` is a Python anti-pattern |
| 7 | No mention of `Support\Arr/Collection/Number` | → explicitly dropped | The three files are empty and unimported |
| 8 | No mention of `Logging/` | → explicitly dropped | Not wired into `src/`; only referenced by one test |
| 9 | No mention of `PurchaseActionMapping` | → added | It is user-configurable and drives the `None` vs `0.0` purchase semantics |
| 10 | No mention of `FilterOperator` / `InsightsFilterField` | → added | `FilterOperator` is a first-class enum; `InsightsFilterField` is the allow-list enforced by `QueryBuilder` |
| 11 | No mention of Ad Set configuration enrichment | → added (§5.9) | It is a real N+1 request path that changes both HTTP traffic and `InsightsRawData` |
| 12 | No mention of the currency-resolution order | → added (§5.10) | Three distinct branches (row currency / account fallback / empty result) with different HTTP side effects |
| 13 | No mention of `Response.is_successful()` excluding `error` bodies | → added (§1.3, §5.4) | A 200 with an `error` payload must not be treated as success |
| 14 | No mention of the exception `safe_context` allow-list | → added (§5.5) | It is a deliberate security control, not a detail |
| 15 | No mention of `MetaConfig` unserialisation refusal | → added (§5.1) | Prevents a redacted object being restored into credentials |
| 16 | No query-encoding parity rules | → new §6.1 | PHP renders booleans as `1`/`0` and spaces as `%20`; httpx does neither |
| 17 | No numeric/date strictness rules | → new §6.2, §6.3 | PHP `is_numeric` and `createFromFormat` are stricter than Python's defaults |
| 18 | No timezone notes | → new §6.4 | `zoneinfo` needs `tzdata` on Windows/slim containers |
| 19 | No `MetricRegistry` catalogue-validation rules | → added (§5.8) | The registry self-validates on construction; the port must too |
| 20 | "Python 3.12+" | → "3.11+" | `StrEnum`, `Self` and `datetime.UTC` are all 3.11 features; 3.11 broadens adoption |
| 21 | `respx` *or* `pytest-httpx` | → `respx` only | URL-pattern routing is required by the pagination and enrichment tests |
| 22 | No test-parity matrix | → new §8 | A 23-file mapping makes the parity claim auditable |
| 23 | No Phase 0 | → added | Golden fixtures must be captured before any code is written, otherwise parity is unverifiable |
| 24 | No integration-test marker strategy | → added (§8) | PHP separates unit and integration suites via two `phpunit*.xml` files; Python needs `@pytest.mark.integration` |
| 25 | `docs/` and `examples/` only mentioned for README | → full port listed in Phase 7 | The PHP project ships 10 docs pages and 8 example scripts; they are part of the product |
| 26 | No `py.typed` / packaging build backend | → added (§4) | The plan promised `mypy` support; without `py.typed` the types are not published |
| 27 | Services re-created per facade call | → cached on the facade | `historical()` and `hierarchy()` are built on top of `insights()`; caching keeps object identity consistent (e.g. for the shared `Paginator`) |
| 28 | No `close()`/context-manager lifecycle | → added (§5.3) | `httpx.Client` holds a connection pool; a library must not leak it |
| 29 | `MetaConfig` redaction described only as `__repr__` | → `__repr__` **and** `__getstate__` refusal | Mirrors PHP `__debugInfo` + `__serialize` + `__unserialize` |
| 30 | `logger`/`structlog` listed as optional | → removed | The PHP logger is dead code; the sanitized exception context is the real logging surface |

---

## 13. Immediate next step

Start with **Phase 0 + Phase 1**, in this order:

1. `pyproject.toml` (hatchling, `py.typed`, `ruff`, `mypy --strict`, `pytest` with `-m "not integration"`).
2. `metametrics/exceptions.py` — the full hierarchy, including the `safe_context` allow-list.
3. `metametrics/config.py` — `MetaConfig` + `ConfigurationValidator`.
4. `metametrics/client.py` — `MetaClient`, `Request`, `Response`, `JsonResponseDecoder`.
5. `metametrics/errors/` — `MetaError`, `MetaErrorParser`, `MetaErrorMapper`.
6. `metametrics/utils/diagnostics.py` — `DiagnosticSanitizer`.
7. `metametrics/query/` — `Fields`, `Filter`, `FilterOperator`, `QueryBuilder`.
8. `metametrics/auth/` — `AuthenticationService` + `AuthenticationResult`.
9. `metametrics/meta_ads.py` — the facade.
10. Port `tests/Unit/Config/MetaConfigTest.php`, `tests/Unit/Authentication/*`,
    `tests/Unit/MetaAdsTest.php` and the golden request fixtures.

Once the foundation is stable, continue with Phase 2 (entity services + pagination).
