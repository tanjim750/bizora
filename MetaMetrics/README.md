# MetaMetrics

**MetaMetrics** is a framework-independent Python library for fetching, normalizing, and analyzing
Meta Ads data through the Meta Marketing API.

It provides a reusable abstraction for working with **Ad Accounts, Campaigns, Ad Sets, Ads, and
performance insights** without requiring applications to handle Meta's raw API structure, pagination,
or metric parsing.

> This is the Python port of the original PHP library. The public API, validation rules, and error
> semantics are kept deliberately close to the PHP original so that migration stays low-risk.

## Installation

```bash
pip install metametrics
```

From a checkout:

```bash
pip install -e ".[dev]"
```

Requires Python 3.11 or newer. The only runtime dependency is `httpx`.

## Quick Start

The consumer application owns credential loading. Pass the resulting strings into `MetaConfig`; the
library never reads environment variables or framework configuration.

```python
from metametrics import MetaAds, MetaConfig

meta = MetaAds(
    MetaConfig(
        access_token=access_token,
        ad_account_id="act_123456789",
        api_version="v26.0",
    )
)

connection = meta.authentication().validate()
account = meta.account().get()
campaigns = meta.campaigns().all()
ad_sets = meta.ad_sets().for_campaign("1200000000000001")
ads = meta.ads().for_ad_set("1200000000000002")
```

`MetaAds` composes every service around a single shared client:

| Accessor | Purpose |
|---|---|
| `meta.authentication()` | Validate the token against the configured Ad Account |
| `meta.account()` | Ad Account metadata and currency |
| `meta.campaigns()` | Campaign listing and lookup |
| `meta.ad_sets()` | Ad Set listing and lookup |
| `meta.ads()` | Ad listing and lookup |
| `meta.insights()` | Account / Campaign / Ad Set / Ad analytics |
| `meta.historical()` | Delivery-aware historical analytics |
| `meta.hierarchy()` | Campaign → Ad Set → Ad reconstruction |
| `meta.client()` | Raw low-level access to the Meta API |

## Error handling

Every failure raised by the library derives from `MetaAdsError`, which carries a log-safe diagnostic
context.

```python
from metametrics.exceptions import MetaAdsError, RateLimitError

try:
    campaigns = meta.campaigns().all()
except RateLimitError as error:
    retry_after = error.retry_after_seconds
except MetaAdsError as error:
    context = error.context()
```

| Exception | Raised when |
|---|---|
| `AuthenticationError` | Meta rejected the access token |
| `InvalidConfigurationError` | The client configuration is invalid |
| `InvalidInputError` | A caller supplied an invalid argument |
| `NetworkError` | The request could not be delivered (retryable) |
| `PermissionDeniedError` | The token lacks permission for the operation |
| `RateLimitError` | The Meta API rate limit was exceeded |
| `ResourceNotFoundError` | A Meta resource could not be found or accessed |
| `UnexpectedResponseError` | Meta returned a malformed payload |
| `UnsupportedMetricError` | A metric is unknown or misconfigured |

`PermissionDeniedError` intentionally does **not** shadow the builtin `PermissionError`.

## Raw responses

Normalized services are the default workflow. When direct response inspection is required, use the
shared low-level client:

```python
from metametrics import Request

response = meta.client().send(
    Request(method="GET", path="/v26.0/act_123456789", query={"fields": "id,name,currency"})
)

if response.is_successful():
    decoded = response.body
    raw = response.raw_body
else:
    status = response.status_code
```

Unlike the normalized services, direct client calls return unsuccessful responses instead of mapping
them to typed exceptions.

## Security

- The access token is sent in the `Authorization` header and never in the URL.
- `MetaConfig` redacts the token from `repr()` and from any serialised snapshot, and refuses to be
  restored from one.
- `MetaAdsError.context()` only ever exposes an allow-listed set of diagnostic keys.

## Testing

```bash
pytest                    # unit suite
pytest -m integration     # live tests, requires real credentials
```

The unit suite uses fake Meta clients and does not require credentials.

## Status

🚧 **Under Development** — the migration is in progress. Phases 0–2 (foundation, entity
services, pagination) are complete; insights, historical analysis, hierarchy, and the tracking
URL parser follow.

## License

Open-source. See the `LICENSE` file for details.
