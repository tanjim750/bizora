# Overview & Monitoring implementation

Implemented on `codex/overview-monitoring`, based on `0a6d904` from
`codex/integration-data-observability`. The earlier feature remains in its own commit.

This Django backend implements all eight monitoring groups in
[the feature specification](features/overview-monitoring.md). It supplies authenticated
JSON APIs for a future dashboard. This repository has no frontend application.
The [75-feature traceability matrix](overview-monitoring-progress.md) maps the specification
to routes, implementation, and regression coverage.

## Ownership and data flow

`app/overview/` projects existing BusinessMetric, MetricSnapshot, BusinessFact,
BusinessIssue, BusinessRelationship, Graph, Knowledge, AiRecommendation, AiAction,
and operational records. It never creates authoritative metrics, facts, issues,
relationships, recommendations, approvals, or executions during monitoring reads.
It performs no network or LLM calls. Missing upstream results remain unavailable.

The built-in metric catalog is a set of selectable display keys. BI owns each
metric's actual name, category, unit, calculation rule, dimensions, and snapshots.
The catalog includes revenue, orders, customers, marketing, website, support,
delivery, and payments. Businesses may also select their own active BI metric keys.
No revenue is recomputed from orders, and no percentages or ROAS values are summed.

Migration `0003_overview_monitoring` adds only `MonitoringConfiguration` and
append-only `MonitoringConfigurationRevision` tables. These provide the narrow
Monitoring Configuration contract described by Business Configuration, whose
larger module is now implemented in [Business Configuration](business-configuration.md). Configuration records are business scoped,
versioned, and attributed to the actor; reads never create default rows.

## API

All paths below are relative to `/api/businesses/<business_id>/overview/`.
Use the existing Django/DRF session or Basic authentication. An active user must
have `BusinessAccess` with role `READER` or `MANAGER` for that business; superusers
may inspect any business. Only managers may update configuration. Monitoring data
routes are read-only, including recommendation and issue details.

| Route | Purpose | Supported filters |
| --- | --- | --- |
| `GET summary/` | Executive summary, current state, KPIs, health, issues, recommendations, activity, ranked attention | metric, period, dimension_type + dimension_value, from + to |
| `GET catalog/` | Catalog and active business metric definitions, registration and selection flags | none |
| `GET kpis/` | Exact-period values, comparison, source freshness, calculation and evidence references | metric, domain, period, dimension_type + dimension_value, from + to |
| `GET trends/` | Upstream time series and adjacent comparable-period changes | same as kpis |
| `GET issues/` | Active prioritized issues with confidence, entity, trend, context, evidence summary | status, severity, entity_type, entity_id, from + to, page, page_size |
| `GET issues/<id>/` | Description, evidence, graph context, associated stored recommendations | none |
| `GET health/` | Explainable overall/domain health, goal evaluation, trend and separate integration reliability | period, from + to |
| `GET activity/` | Chronological operational and intelligence events | domain, entity_type, entity_id, severity, from + to, page, page_size |
| `GET recommendations/` | Ranked current recommendations, issue/goal links, evidence and action status summaries | status, priority, issue, from + to, page, page_size |
| `GET recommendations/<id>/` | Full stored explanation, evidence, graph context, redacted action preview and approval/execution status | none |
| `GET cross-domain/` | Nine supported scenarios grounded in existing BI issues and deterministic relationships | none |
| `GET configuration/` | Effective settings, version and last editor | none |
| `PUT configuration/` | Validate and merge monitoring settings; replace submitted lists | none |
| `GET entities/<type>/<id>/` | Safe scoped operational reference, status, label and local graph context | none |
| `GET evidence/<kind>/<id>/` | Source evidence drill-down | none |

Evidence kinds: `facts`, `snapshots`, `relationships`, `nodes`, `edges`, `knowledge`.
Entity types: order, customer, product, product_variant, payment, refund, campaign,
conversation, shipment, call, website_session, website_visitor. Unmodeled region,
courier, or segment context may be displayed as explicit BI issue metadata; it
does not become a newly inferred canonical entity or a fabricated operational link.

Collection pages default to 25, with a maximum of 100 and stable secondary ordering.
Unknown/repeated filters, invalid statuses, partial dimension filters, naive dates,
future ranges, and invalid page sizes return 400. Foreign business access returns
403; foreign or invalid evidence/entity IDs under an accessible business return 404.

`metric` accepts up to 50 comma-separated unique keys. `domain` uses sales,
customers, marketing, website, support, delivery, payments; activity additionally
supports calling, issues, ai. Status filters are uppercase. Issues support OPEN,
NEW, ACKNOWLEDGED, ONGOING, IN_PROGRESS, RESOLVED, DISMISSED. Recommendation statuses
include SUGGESTED, UNDER_REVIEW, APPROVED, REJECTED, EXECUTED, ACTIONED, COMPLETED,
EXPIRED, DISMISSED. `status=EXPIRED` includes unreviewed recommendations whose
expiry time has passed; `effective_status` distinguishes that from the stored status.

## Periods, comparisons, and freshness

`period` is DAY, WEEK, MONTH, ROLLING_7D, or ROLLING_30D, matching the BI snapshot's period_type. Defaults
select the last complete business-calendar period in `Business.timezone`. Weeks
start Monday unless General Settings specifies another business week boundary. The default comparison is the preceding calendar period, preserving DST
boundaries and different month lengths. Responses expose UTC bounds and the
business timezone. Invalid business timezones require configuration correction.

Explicit `from` and `to` must be timezone-aware ISO datetimes, supplied together,
with positive duration at most 366 days and ending no later than evaluation time.
They use half-open `[from,to)` semantics and compare the immediately preceding
equal-duration period. KPI snapshots must exactly match these bounds and period
type. Missing exact windows return UNAVAILABLE rather than an estimate or zero.

For each metric, dimension, and window, the latest calculated revision available
at evaluation time wins, with ID as a deterministic tiebreaker. Null and empty
total dimensions share one revision group. Snapshot metric/business ownership is
checked independently; future and pre-completion calculations are excluded.
Totals never include dimension-specific snapshots. Trend points retain native
periods. Overlapping, missing-adjacent, or incompatible periods cannot imply a
comparison. No interpolation or aggregation is performed.

Values and differences are decimal strings. Percentage change uses the absolute
previous value as the denominator. Zero baselines return null percent_change and
ZERO_BASELINE. Units `%`, PERCENT, and PERCENTAGE label the absolute change as
PERCENTAGE_POINTS. Numeric UP/DOWN is separate from configured IMPROVING/DECLINING;
the module does not assume that increasing refunds or support backlog is good.
PostgreSQL preserves the full original DecimalField precision. SQLite's native
numeric storage has its usual floating-point precision limits for large values.

Trends default to the preceding 30 days for DAY or 366 days for WEEK/MONTH. Results
are limited to 5,000 points across the selected series, with explicit truncation.
Clients can compare dimensions by requesting the same metric/window for each
dimension value; dimensions are never blended into one total.

A KPI is usable for health only when its calculation is within snapshot_ttl_seconds
and every explicitly configured source dependency has fresh, complete, confirmed
coverage from an actively monitored connection. Missing, disabled, disconnected,
future-confirmed, partial, delayed, or stale source coverage cannot establish a
healthy metric. Source policies and timestamps come from Integration & Data
Observability. With no explicit dependency, the metric's calculation age is checked;
the module does not guess which provider supplies a BI metric. Reliability is
returned separately from business health, including when integrations are unknown.

## Configuration and health rules

Example request body for `PUT configuration/`:

```json
{
  "version": 0,
  "period": "DAY",
  "snapshot_ttl_seconds": 172800,
  "domains": ["sales", "delivery"],
  "kpis": [
    {"key": "realized_revenue", "direction": "HIGHER", "target_min": "100000", "goal": "Sustainable revenue"},
    {"key": "delivery_failure_rate", "direction": "LOWER", "warning": "10", "critical": "25", "target_max": "9", "goal": "Reduce delivery failure", "sources": [{"connection_id": 1, "entity_type": "ORDER"}]}
  ],
  "issue_severities": ["CRITICAL", "HIGH", "MEDIUM"],
  "recommendation_priorities": ["CRITICAL", "HIGH"],
  "cross_domain": ["marketing_delivery", "courier_revenue"]
}
```

Use connection IDs belonging to the requested business. Source entity types use
uppercase integration entity names. KPI keys must be in the display catalog or
the business's active BI registry. Defaults choose nine prominent KPIs across all
seven domains, without assuming desired direction or target values.

Targets and thresholds use the BI metric's own units. Directions are HIGHER,
LOWER, NEUTRAL. HIGHER thresholds require critical <= warning; LOWER requires
critical >= warning. Target ranges require min <= max. Critical thresholds win,
then warning thresholds, then missed target ranges. A configured non-neutral
direction can assess comparable period movement where no absolute range is set.
Unconfigured or unusable metrics are UNKNOWN, not healthy.

Active CRITICAL issues establish critical health; other active issues establish
warning health. Issue visibility preferences do not suppress these health inputs.
Domains without usable rules/evidence remain UNKNOWN. Overall HEALTHY requires
all monitored domain states to be healthy; known warnings/critical conditions
remain visible even if another domain is unknown. There is no numerical health
score. Evidence includes contributing issue IDs, metric/snapshot IDs, rule values,
goal labels and working drill-down paths.

Health trend consolidates stored BI issue trend metadata and comparable KPI
movement; mixed movement is explicit. It is not a reconstructed historical health
score. The API evaluates current issue/recommendation state and does not support
arbitrary historical as-of reads. All responses identify their evaluation time.

Writes lock the business even when creating its first policy, then save an actor-
attributed revision in the same transaction. Supply the last observed version to
prevent overwrites; mismatches return 409. Omitting version performs a serialized
merge into the latest settings. There is no independent monitoring configuration
admin editor that bypasses validation or revision recording.

## Findings, evidence, and activity contracts

BI may supply `BusinessIssue.metadata.domains`, `trend` (IMPROVING, WORSENING,
STABLE), and concise region/courier/product/campaign/customer_segment context.
Absent trend information remains UNKNOWN. Existing issue status/resolution
timestamps control lifecycle display; monitoring cannot acknowledge or resolve it.
Stored recommendations may supply `metadata.goals` as explicit upstream goal
alignment. This module does not generate goal links, recommendations, or actions.

Cross-domain scenarios are marketing_revenue, marketing_delivery, website_sales,
product_support, product_delivery, customer_retention, support_customer_outcome,
courier_revenue, campaign_customer_quality. BI declares scenario keys in issue
`metadata.monitoring_scenarios`. A scenario is surfaced only with a valid existing
deterministic relationship and evidence covering its required domains. Tags alone,
coincident metrics, foreign entities, and expired relationships do not establish
a finding. NO_VERIFIED_FINDING means no grounded finding is available, not that
the monitored pathway is proven healthy. The bounded view scans up to 500 active
prioritized issues and indicates truncation.

Evidence projections verify every referenced business independently, including
snapshot definitions, graph endpoints/relationships, and knowledge chunk/document/
source chains. Invalid evidence is omitted as a whole. Entity lookup types are
allowlisted. Credentials are redacted from text and bounded action previews;
provider payloads, customer contact details, recordings, transcripts, and arbitrary
source metadata are not dumped into monitoring responses. Evidence details return
at most 50 eligible rows from a bounded 101-row source scan, graph context at most
50 edges, and action previews at most 20 actions. Feed evidence summaries show up
to three references and feed action summaries show up to three statuses.

Activity uses a SQL UNION over canonical event records and explicit timestamps:
orders/status changes, payments/refunds, customers/timelines, conversations/
assignments/resolutions, shipments/events, campaigns/conversions, website events,
calls/events, BI issues, and AI recommendations/actions. Pagination, counts, time
filters, and ordering happen in the database, without a capped in-memory merge.
Stable IDs include model, event kind, and source ID. Rows derived from an entity's
latest status are labelled LATEST_STATE_OBSERVATION; actual events/timestamps are
labelled RECORDED_EVENT. Existing models do not preserve every historical state
transition, so the module does not invent missing events. Default activity covers
the last 30 days. New upstream records become visible on the next request.

## Setup and verification

Use Python 3.12 and the pinned dependencies in requirements.txt. Apply the additive
migration before using these APIs:

```bash
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Use a disposable SQLite path to run the reproducible acceptance demo without
touching the tracked developer database:

```bash
export BIZORA_DB_PATH="$(mktemp /tmp/bizora-overview.XXXXXX.sqlite3)"
python manage.py migrate --noinput
python manage.py simulate_overview --seed 76001 --at 2026-10-25T12:00:00+00:00
```

The demo owns only its `overview-demo-*` business namespace, declares upstream BI
inputs, and validates real monitoring views and access checks. It covers +21%
orders, +18% spend, 9% to 20% delivery failure, +24% refunds, +5% realized revenue,
grounded cross-domain issues, stored recommendations, goals, fresh sources, stale
and empty businesses, tenant isolation, and evidence drill-down. Reruns revalidate
current data; tampering yields a failing command. Scenario inputs/expectations are
recorded using existing MockScenario, MockScenarioEvent, and MockExpectedResult.

PostgreSQL verification uses BIZORA_DATABASE=postgresql and POSTGRES_DB, USER,
PASSWORD, HOST, PORT variables. The original KnowledgeEmbedding field requires
pgvector in the target database and disposable test template; see
[the existing database setup notes](integration-data-observability.md#local-setup-and-verification).
The PostgreSQL-only suite checks first-write serialization, optimistic-version
conflicts, full decimal precision, and existing observability concurrency. SQLite
explicitly skips those database-specific tests.

No polling worker, notification system, or websocket transport is added. Clients
may refresh these read APIs; elapsed freshness is evaluated at read time. Upstream
ingestion, BI computation, graph building, AI generation, and action execution
retain their own domain ownership.
