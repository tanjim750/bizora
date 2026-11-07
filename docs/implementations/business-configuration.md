# Business Configuration implementation

Implemented on `codex/business-configuration`, created before the first tests or
code changes. The base is Overview & Monitoring commit `ce41d54`; earlier features
remain committed on their own branches. This is the Django backend implementation
of all eight groups and 90 named features in
[the specification](features/business-configuration.md). The repository has no
frontend application. See the [feature matrix and test-loop record](business-configuration-progress.md).

## Ownership and persistence

Business Configuration defines administrative inputs. Existing runtime domains
still own ingestion, synchronization, observations, BI findings, graph projection,
document processing, AI generation, approvals, and execution. A configuration write
never claims that those activities completed.

Migration `0004_business_configuration` adds ConfigurationRecord,
ConfigurationRevision, ConfigurationEvent, and KnowledgeReprocessingRequest.
It preserves existing Business, IntegrationConnection, KnowledgeSource,
MonitoringConfiguration, MonitoringConfigurationRevision, MonitoringPolicy, and
all runtime records. It does not seed policies, fabricate history, or copy secrets.

Each new settings record has a stable business/kind/key identity and a current
version. Every successful write appends an actor-attributed revision and a durable
change notice in the same transaction. History endpoints are read-only; no delete
endpoint is provided. Version mismatches return 409. Supplying the last read version
prevents overwrites; omitting it performs a serialized merge into the current state.
Nested objects merge recursively; lists replace the previous list.

Business name, currency, and timezone remain authoritative on Business. Profile
and general settings update/read those same fields, so Overview immediately uses
the configured timezone and currency. Profile extensions, formatting, operational
defaults, and preferences are validated structured settings, not duplicate business
entities. Currency syntax is a three-letter uppercase code; timezone validation
uses the installed IANA timezone database.

Monitoring retains its existing tables and service. The new monitoring endpoint
and legacy Overview endpoint share one configuration/history. Freshness and retry
settings retain MonitoringPolicy and its existing precedence: connection/entity,
connection default, business/entity, business default, platform defaults. Changes
through either the configuration or legacy Observability endpoint now append
configuration history. The FRESHNESS configuration record is an audit snapshot;
MonitoringPolicy remains the runtime source of truth.

## Authenticated API

Paths are relative to `/api/businesses/<business_id>/configuration/`. Existing
Django/DRF session or Basic authentication is supported. Active business READERs
and MANAGERs may read; MANAGERs may write. Superusers may access all businesses.
Services check permissions as well as views. Foreign business access is denied;
foreign source/connection/resource IDs cannot be read or edited under another
business. Public/provider catalogs expose provider definitions, never another
business's credentials or connections.

| Route | Behavior |
| --- | --- |
| `GET / PUT profile/` | Name, description, industry, contact, location, operating regions, channels, currency, timezone, metadata |
| `GET / PUT general/` | Locale/language, formats, separators, decimals, reporting period, business week, operational defaults, feature preferences, metadata |
| `GET / PUT ai/` | Provider/model/task controls, context, response preferences, confidence, escalation, proposed actions, execution restrictions, parameters, workflow restrictions |
| `GET / PUT knowledge/` | Categories, ingestion limits/types, chunking, embedding model, vector/keyword/hybrid settings, workflow scope, historical retrieval |
| `GET rules/`, `POST rules/` | List or create deterministic rule definitions |
| `GET / PATCH rules/<key>/` | Inspect, revise, prioritize, enable/disable a stable rule |
| `GET policies/`, `POST policies/` | List or create delivery, return, refund, cancellation, support, product policies |
| `GET / PATCH policies/<key>/` | Draft, publish, schedule, supersede, archive, or revise a policy |
| `GET providers/` | Active provider catalog and declared entity/scope capabilities |
| `GET connections/`, `POST connections/` | List existing connections or configure one using an active provider |
| `GET / PATCH connections/<id>/` | Versioned integration settings, enable/disable, mock settings, secret references |
| `POST connections/<id>/test/` | Existing audited/idempotent integration test operation; requires idempotency_key |
| `GET sources/`, `POST sources/` | Knowledge source administration and approval |
| `GET / PATCH sources/<id>/` | Revise, approve, disable, archive a source |
| `GET reprocessing/`, `POST reprocessing/` | Inspect or request idempotent REPROCESS/REEMBED work |
| `GET / PUT monitoring/` | Existing KPI selection/targets/thresholds, windows, comparisons, visibility and source dependencies |
| `GET / PUT freshness/` | Existing integration freshness, monitoring, sample, latency and retry policies |
| `GET effective/` | Effective settings and applicable rules, policies, approved sources at evaluation time |
| `GET changes/` | Paginated durable change notices for downstream owners |

History routes: `<profile|general|ai|knowledge>/history/`,
`<rules|policies>/<key>/history/`, `<connections|sources>/<id>/history/`,
`monitoring/history/`, and `freshness/<policy_id>/history/`.

Collection/history pagination defaults to 25, maximum 100. Rules and policy lists
also accept status. Unknown/repeated query parameters, invalid page sizes,
unrecognized settings, invalid scopes, and malformed JSON objects return 400.
Resource keys use lowercase letters, digits, underscores or hyphens, beginning
with a letter. Settings reads return a settings object plus version/status/editor
metadata. Writes accept settings fields directly, with optional version and reason.
Rule/policy writes also support status, priority, valid_from, valid_to. Singleton
settings apply immediately and cannot accept lifecycle or scheduling fields.

`effective/` accepts validated scope fields product_id, campaign_id, customer_id,
region, courier, channel, customer_type, category; plus workflow and historical.
Workflow is business_assistant, customer_support, marketing, summarization, or
recommendations. Historical knowledge retrieval requires `historical=true` and an
explicitly enabled business preference. Effective AI controls reapply the current
platform minimum even if platform settings changed after the business last saved.

## Rules and policy versions

Example `POST rules/`:

```json
{
  "key": "high_delivery_failure",
  "status": "ACTIVE",
  "category": "DELIVERY",
  "priority": 10,
  "scope": {"courier": "Courier X", "region": "Gazipur"},
  "conditions": {"all": [{"field": "delivery_failure_rate", "operator": "gt", "value": "15"}]},
  "sample_metric": "shipment_count",
  "min_samples": 20,
  "window_days": 30,
  "outcome": {"type": "ALERT", "code": "HIGH_DELIVERY_FAILURE", "severity": "HIGH"}
}
```

The bounded DSL supports exactly one all/any condition list, with gt, gte, lt, lte,
eq, ne, in, not_in operators. It contains no eval, executable expressions, dynamic
imports, or client-supplied handlers. Numeric conditions use finite decimals;
membership and equality compare supplied scalar values. Missing/invalid inputs
remain UNKNOWN, and insufficient samples cannot trigger an outcome. BI supplies
the correctly calculated metric values and evaluation-period data; configuration
does not calculate them. A matching rule returns an outcome proposal for its
owning deterministic domain, not a newly created issue or fact.

Rules have stable references such as
`config:rule:high_delivery_failure:v1`. BI can store that reference in rule_key to
explain which configuration produced a finding. Applicable rules are ordered by
priority then stable key. Policy precedence uses priority, scope specificity, key.
Product, campaign, and customer IDs in scopes are checked against the business.
Region/courier/channel labels remain bounded dimensions where no canonical model
exists in this prototype.

Policy categories have typed parameter contracts: delivery coverage/time/charge/
courier/COD/failure guidance; returns window/eligibility/exclusions/procedure;
refund window/methods/approval/eligibility/procedure; cancellation states/cutoff/
procedure; support response expectation/escalation/instructions; product
constraints/instructions. Active policies require complete parameters and terms.
Incomplete drafts can be saved and must be completed before activation.

Editing a draft does not displace the previous published policy. Effective selection
uses the latest non-draft publication whose start has arrived; only then checks
its active status and exclusive end. Thus future versions do not apply early,
disabled/archived versions stop applicability, and expired newer versions never
resurrect older rules. History preserves all revisions. Policy terms and approved
versions are available as structured grounding context to Business Memory/AI;
configuration does not invent a second copy of policy knowledge or generate chunks.

## Integration controls and secrets

Provider selection uses the existing IntegrationSource registry. Declared entity
and authorization scope selections are validated by provider category. Selected
entities require their corresponding read scope. Provider settings are bounded
JSON and cannot contain credential keys. Sync supports FULL, INCREMENTAL,
SCHEDULED, MANUAL and bounded interval settings. Webhooks define subscriptions,
HTTPS endpoint, enable flag, and a signing-secret reference for live connections.
Mock settings control deterministic connection outcomes, timeouts, and product
field mapping in the existing prototype adapter.

The connection's existing config stores the validated runtime selections. Disabling
keeps settings and sets DISABLED. Renaming/editing a connection does not overwrite
ERROR/EXPIRED runtime observations with a fictional successful status. Existing
connections can be adopted with version zero; unknown legacy settings are not
silently deleted. Reads redact legacy credential-like fields as well as new data.
The retry/replay pipeline enforces explicit entity, scope, and webhook selections;
legacy connections without explicit selections retain their prior behavior.

Credentials are references to deployment-managed secret values, for example:

```json
{"credentials": {"api_key": "env:BIZORA_BUSINESS_1_COMMERCE_TOKEN"}}
```

Use the actual business ID. Allowed credential slots are api_key, access_token,
refresh_token, client_id, client_secret, webhook_secret. References must use the
same business's environment namespace. Raw secrets are rejected; configuration
history stores references only, and API reads expose only configured/field-presence
information. An operator provisions the secret outside this API. Trusted adapters
call `resolve_credentials(connection)`; missing references fail without disclosing
secret names or values. There is no secret-read endpoint or network call during
setup. A future vault backend can replace the deployment resolver without moving
secret values into configuration JSON.

Connection testing uses the existing operation owner and audit ledger. Mock
connection checks are executable locally. Live checks require a registered adapter
for that provider; absence returns the existing UNSUPPORTED result. Declared
configuration capabilities do not imply all live adapters or processors exist.
The bundled canonical mock processor supports PRODUCT payloads. Scheduling settings
are available to integration owners; this configuration module does not install a
background sync scheduler or perform provider synchronization.

## AI and knowledge controls

AI providers/models must be registered by installation code/settings:
`BIZORA_AI_PROVIDERS` maps provider keys to allowed model lists; default is mock.
`BIZORA_EMBEDDING_MODELS` registers supported embedding names; default mock-embedding.
No model API is called when saving configuration. Defaults disable AI features and
proposed actions. Per-workflow models, features, context, language/detail/tone,
confidence, allowed actions, and response preferences can be narrowed independently.
Workflow contexts/actions cannot exceed the business's approved sets; confidence
cannot fall below the business or platform threshold.

Mandatory controls always remain in effect: deterministic evidence for verified
facts/authoritative relationships, approval for external execution, no automatic
external execution, and low-confidence escalation. The platform confidence minimum
defaults to 0.6 and may be raised by BIZORA_AI_MIN_CONFIDENCE. Business settings
cannot weaken it. Removing a registered provider/model disables its effective AI
configuration. `action_policy` reports whether an action may be proposed and that
approval remains mandatory; it never executes an action.

Knowledge settings validate categories, allowed ingestion types/size limits, chunk
size/overlap, embedding model, vector/keyword limits, similarity, hybrid weights,
retrieval cap, and workflow category subsets. Hybrid weights must sum to one and
require both retrieval modes. Unknown workflows are rejected. Archived knowledge
is available only for explicitly historical requests when the business enables it.

Knowledge source approval uses versioned settings over the existing KnowledgeSource.
Draft edits preserve approved source settings. Active approval requires enabled
source type and category. Approved-source consumers exclude foreign/unapproved/
disabled sources; historical archived-source retrieval requires a prior approval.
Website references are configuration inputs; saving them never fetches content.

Reprocessing requests use a business-scoped idempotency key and choose exactly one
source/document plus REPROCESS or REEMBED. Source and document ownership chains are
checked. New requests pin the knowledge settings revision, approved source revision,
and document version so later configuration edits cannot change the requested
inputs. Reusing a key for another intent returns 409. Requests remain REQUESTED;
the response explicitly states that no knowledge worker is installed. The owning
processing domain must validate current approvals/input versions and execute or
reject the request. Documents and embeddings are not rewritten by configuration.

## Monitoring integration

General reporting defaults flow into Overview unless monitoring explicitly overrides
them. Existing migration-0003 rows retain their explicit period. New settings inherit
until an explicit period is selected; inherit_reporting_period can restore inheritance.
Business week_start uses Monday=0 through Sunday=6. DAY, WEEK, MONTH, ROLLING_7D,
ROLLING_30D are supported; rolling KPIs require exact upstream rolling snapshots,
not an invented sum of daily rates or values.

Comparisons support PREVIOUS_PERIOD, TARGET, BASELINE, NONE. KPI rules may set
target_value, baseline_value, target_min/max, warning/critical values and displayed
warning/critical severities. Missing reference values stay unavailable. Target or
baseline comparisons expose reference_value and do not mislabel it previous_value.
Goal assessment is distinct from temporal health trend. All existing monitoring
visibility, domain, cross-domain scenario and source freshness controls remain in
the shared configuration. Alert severity settings annotate health evidence; they
do not create BI issues.

## Consumer interfaces and change delivery

Trusted owning domains use `app.configuration.selectors`:

| Interface | Contract |
| --- | --- |
| effective_rules(business_id, category, scope, at) | Applicable prioritized immutable rule versions |
| evaluate_rule(rule, inputs) | MATCH / NO_MATCH / UNKNOWN / INSUFFICIENT_SAMPLE without writes |
| effective_policies(business_id, scope, at, for_ai) | Published applicable policies, optionally approved for AI |
| ai_configuration(business_id, workflow) | Current effective guardrails, model, workflow and context restrictions |
| action_policy(business_id, action) | Proposal permission and mandatory approval |
| knowledge_configuration(business_id, workflow, historical) | Retrieval/ingestion settings with effective scope |
| approved_sources(business_id, workflow, at, historical) | Owned approved source versions |

Consumers remain responsible for runtime authorization, their own processing, and
recording applied version references. ConfigurationEvent is a durable change notice
with business, section/key, version, actor, and time. It contains no secret values
or runtime conclusions. Polling changes/ or reading versioned contracts is supported;
there is no claim of delivered external events or a background event dispatcher.

## Verification and local setup

Use Python 3.12 and the unchanged pinned requirements. Apply the additive migration:

```bash
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Run the acceptance command in a disposable database:

```bash
export BIZORA_DB_PATH="$(mktemp /tmp/bizora-configuration.XXXXXX.sqlite3)"
python manage.py migrate --noinput
python manage.py simulate_configuration --seed 77001 --at 2026-10-25T12:00:00+00:00
```

It owns only its config-demo-* namespace, exercises real authorized views, and
validates 21 outcomes spanning all eight groups. Inputs and expectations use the
existing MockScenario/Event/ExpectedResult models. Reruns validate current settings
without extra revisions; tampering causes a failing exit status. It never clears
existing business data or requires real secrets/provider network access.

PostgreSQL uses BIZORA_DATABASE=postgresql and the standard POSTGRES_* variables.
The original KnowledgeEmbedding field requires pgvector in the target database
and disposable test template, as documented in the
[database setup notes](integration-data-observability.md#local-setup-and-verification).
PostgreSQL tests cover serialized first writes, version conflicts, idempotent queued
requests, and concurrent integration configuration/runtime operations. Business-row
NO KEY UPDATE locks serialize configuration writes while allowing unrelated runtime
foreign-key references to progress. SQLite explicitly skips row-lock-specific tests.

Final counts and fresh-install demo results are in the
[delivery traceability document](business-configuration-progress.md).
