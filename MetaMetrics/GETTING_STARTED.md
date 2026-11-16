# Getting Started with MetaMetrics (Python)

MetaMetrics is a framework-independent, type-safe Python client library for the Meta Marketing API. It is designed for production data pipelines, analytics reporting, and reporting parity.

---

## 1. Requirements & Installation

- **Python 3.11+**
- **HTTP Transport:** `httpx` (only core dependency)

### Install via pip

```bash
pip install .
```

Or with development tooling:

```bash
pip install -e ".[models]"
```

---

## 2. Configuration

MetaMetrics accepts an existing access token. It does not perform OAuth flows or token generation.

```python
from metametrics import MetaConfig

config = MetaConfig(
    access_token="YOUR_ACCESS_TOKEN",
    ad_account_id="act_123456789",  # Numeric IDs (e.g. '123456789') are normalized to 'act_123456789'
    api_version="v26.0",
)
```

### Security & Redaction

`MetaConfig` is an immutable, frozen dataclass. The access token is automatically redacted in `repr(config)` and string formatting. Pickling `MetaConfig` is explicitly blocked to prevent token exposure in serialization queues.

---

## 3. The `MetaAds` Entry Point

`MetaAds` is the primary facade that composes all services around a single shared HTTP client:

```python
from metametrics import MetaAds, MetaConfig

config = MetaConfig(
    access_token="YOUR_ACCESS_TOKEN",
    ad_account_id="act_123456789",
    api_version="v26.0",
)

with MetaAds(config) as meta:
    # 1. Validate authentication
    auth = meta.authentication().validate()
    print(f"Authenticated: {auth.authenticated}, Account: {auth.account_id}")

    # 2. Fetch Account Details
    account = meta.account().get()
    print(f"Account: {account.name} (Currency: {account.currency})")
```

---

## 4. Entity Services

Query Campaigns, Ad Sets, and Ads with typed filters and field selection:

```python
from metametrics import DateRange, Fields, Filter, FilterOperator
from metametrics.campaign import CampaignQuery

with MetaAds(config) as meta:
    # List all campaigns
    campaigns = meta.campaigns().all()
    for campaign in campaigns:
        print(f"[{campaign.id}] {campaign.name} - Status: {campaign.status}")

    # Query with field selection and filters
    query = CampaignQuery(
        fields=Fields(["id", "name", "status", "objective"]),
        filters=[Filter("effective_status", FilterOperator.IN, ("ACTIVE", "PAUSED"))],
        limit=25,
    )
    filtered = meta.campaigns().all(query)
```

---

## 5. Insights & Metrics Engine

Query performance across 4 entity levels (`account`, `campaign`, `adset`, `ad`) with automatic derived metric calculation and currency resolution:

```python
from metametrics import DateRange, InsightsLevel, InsightsQuery, Metric

with MetaAds(config) as meta:
    query = InsightsQuery(
        level=InsightsLevel.CAMPAIGN,
        date_range=DateRange("2026-09-01", "2026-09-24"),
        metrics=[Metric.SPEND, Metric.IMPRESSIONS, Metric.CLICKS, Metric.ROAS, Metric.CTR],
    )
    response = meta.insights().get_response(query)
    print(f"Insights Level: {response.level}, Currency: {response.currency}")

    for row in response.data:
        print(f"Campaign: {row.entity_name} | Spend: {row.spend} | ROAS: {row.roas} | CTR: {row.ctr}%")
```

---

## 6. Historical & Hierarchy Analysis

Analyze delivery history with positive evidence validation and reconstruct connected entity hierarchy trees:

```python
from metametrics import DateRange, HistoricalLevel, HistoricalQuery

with MetaAds(config) as meta:
    period = DateRange("2026-09-01", "2026-09-24")

    # Historical delivery check
    historical_campaigns = meta.historical().campaigns(period)
    for result in historical_campaigns:
        print(f"Delivered: {result.entity_id} | Evidence: {result.delivery_evidence.indicators()}")

    # Hierarchy tree reconstruction
    tree = meta.hierarchy().historical(period)
    for campaign_node in tree.campaigns:
        print(f"Campaign: {campaign_node.entity_id}")
        for ad_set_node in campaign_node.children:
            print(f"  └── AdSet: {ad_set_node.entity_id}")
            for ad_node in ad_set_node.children:
                print(f"        └── Ad: {ad_node.entity_id}")
```

---

## 7. Tracking URL Parser

Parse UTM tags and Meta click parameters according to standard tracking conventions:

```python
from metametrics import TrackingUrlParser

parser = TrackingUrlParser()
result = parser.parse("https://example.com/product?utm_id=111&utm_term=222&utm_content=333&utm_source=fb")

print(f"Campaign ID: {result.campaign_id}")
print(f"Ad Set ID: {result.ad_set_id}")
print(f"Ad ID: {result.ad_id}")
print(f"Source: {result.source}")
```

---

## 8. Error Handling

MetaMetrics uses a safe, typed exception hierarchy rooted at `MetaAdsError`:

```python
from metametrics.exceptions import (
    AuthenticationError,
    MetaAdsError,
    PermissionDeniedError,
    RateLimitError,
)

try:
    with MetaAds(config) as meta:
        meta.account().get()
except AuthenticationError:
    print("Token invalid or expired.")
except RateLimitError as exc:
    print(f"Rate limited. Retry after {exc.retry_after_seconds}s.")
except PermissionDeniedError:
    print("Insufficient permissions for this ad account.")
except MetaAdsError as exc:
    # Safe diagnostic context without leaked credentials
    print(f"Meta Error: {exc} | Diagnostic Context: {exc.context()}")
```
