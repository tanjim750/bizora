# API Request/Response Schema v3

This document describes the current Dialyra v3 API surface.

v3 is currently focused on:

- softphone-like SIP trunk creation and runtime status
- v3 runtime call originate using access-token auth
- business-scoped v3 rollout controls

All other modules continue to use v2 unless explicitly listed here.

## Version Scope

Current v3 endpoints:

- `POST /api/v3/sip-trunks`
- `GET /api/v3/sip-trunks`
- `GET /api/v3/sip-trunks/profiles`
- `GET /api/v3/sip-trunks/:id`
- `PUT /api/v3/sip-trunks/:id`
- `DELETE /api/v3/sip-trunks/:id`
- `POST /api/v3/sip-trunks/:id/test`
- `GET /api/v3/sip-trunks/:id/status`
- `POST /api/v3/sip-trunks/:id/reload`
- `POST /api/v3/sip-trunks/:id/apply`
- `POST /api/v3/sip-trunks/:id/rollback`
- `PUT /api/v3/sip-trunks/:id/global-access`
- `GET /api/v3/sip-trunks/realtime/health`
- `GET /api/v3/sip-trunks/drift`
- `GET /api/v3/businesses?user_id=:user_id`
- `POST /api/v3/runtime/calls/originate`

v3 SIP trunk behavior is gated by rollout flags:

- `SIP_TRUNK_V3_ENABLED=true`
- `SIP_TRUNK_V3_ALLOWED_BUSINESS_IDS=` optional comma-separated business allowlist. Empty means all businesses are allowed when v3 is enabled.

When v3 is disabled for the business, v3 endpoints return:

```json
{
  "error": "SIP trunk v3 is not enabled for this business/environment",
  "code": "V3_ROLLOUT_DISABLED"
}
```

## Authentication

### Management Endpoints

SIP trunk v3 management endpoints use JWT auth.

- `POST /api/v3/sip-trunks` requires `businesses.manage`.
- `GET /api/v3/sip-trunks` requires `businesses.read`.
- `GET /api/v3/sip-trunks/profiles` requires `businesses.read`.
- `GET /api/v3/sip-trunks/:id` requires `businesses.read`.
- `PUT /api/v3/sip-trunks/:id` requires `businesses.manage`.
- `DELETE /api/v3/sip-trunks/:id` requires `businesses.manage`.
- `POST /api/v3/sip-trunks/:id/test` requires `businesses.manage`.
- `GET /api/v3/sip-trunks/:id/status` requires `businesses.read`.
- `POST /api/v3/sip-trunks/:id/reload` requires `businesses.manage`.
- `POST /api/v3/sip-trunks/:id/apply` requires `businesses.manage`.
- `POST /api/v3/sip-trunks/:id/rollback` requires `businesses.manage`.
- `PUT /api/v3/sip-trunks/:id/global-access` requires superuser.
- `GET /api/v3/sip-trunks/realtime/health` requires superuser.
- `GET /api/v3/sip-trunks/drift` requires `businesses.read`.
- `GET /api/v3/businesses?user_id=:user_id` requires `businesses.read`; superuser can query any user, non-superuser can only query self.

### Runtime Originate Endpoint

`POST /api/v3/runtime/calls/originate` uses business access-token auth with scope:

```text
calls:originate
```

Send the access token as either:

```http
X-Dialyra-Access-Token: <token>
```

or:

```http
Authorization: Bearer <token>
```

JWT bearer tokens are not accepted on access-token endpoints.

## Businesses v3

### List Businesses For User

`GET /api/v3/businesses?user_id=:user_id`

Returns businesses bound to the requested user through active workspace membership or direct ownership.

Access rules:

- Superuser can query any `user_id`.
- Non-superuser can only query their own `user_id`.
- If `user_id` is omitted, this endpoint follows the normal business list behavior for the authenticated actor.

Response `200`:

```json
{
  "items": [
    {
      "id": 1,
      "uuid": "string",
      "name": "string",
      "slug": "string",
      "owner_user_id": 1,
      "email": "string",
      "phone": "string|null",
      "timezone": "Asia/Dhaka",
      "country": "string|null",
      "logo_path": "string|null",
      "status": "active",
      "settings": {},
      "allow_global_sip_fallback": false,
      "sip_login_prefix": "string|null",
      "deleted_at": "ISO_DATETIME|null",
      "created_at": "ISO_DATETIME",
      "updated_at": "ISO_DATETIME"
    }
  ]
}
```

Error examples:

```json
{
  "error": "Insufficient permission for this user"
}
```

```json
{
  "error": "User not found"
}
```

## SIP Trunks v3

v3 SIP trunks use a softphone-like contract:

- no `provider_profile`
- user supplies normal SIP account/provider fields
- backend applies generic SIP defaults
- advanced SIP fields are optional overrides
- supports `registration` and `ip_auth`
- supports optional inbound setup through `enable_inbound`
- realtime PJSIP tables are synced by the backend

### Create SIP Trunk

`POST /api/v3/sip-trunks`

Creates a business SIP trunk or a global SIP trunk and syncs it to PJSIP realtime tables.

Scope behavior:

- Business trunk: provide `business_id`; caller must be allowed to manage that business.
- Global trunk: superuser omits `business_id`; backend stores `scope="global"` and `business_id=null`.
- Optional `scope`, when provided, must match the inferred scope.
- Global SIP is outbound/fallback only; `enable_inbound=true` is rejected for global trunks.

Request for registration trunk:

```json
{
  "business_id": 1,
  "name": "Trizync Main",
  "provider_name": "Trizync",
  "trunk_mode": "registration",
  "host": "202.40.176.2",
  "port": 5060,
  "username": "09617179124",
  "password": "secret",
  "max_concurrent_calls": 50,
  "is_active": true,
  "enable_inbound": false,
  "advanced": {
    "transport": "udp",
    "dtmf_mode": "rfc4733",
    "from_user": "09617179124",
    "from_domain": "202.40.176.2",
    "auth_username": "09617179124",
    "outbound_proxy": null,
    "codecs": ["ulaw", "alaw"],
    "context": "outbound",
    "rtp_symmetric": true,
    "force_rport": true,
    "rewrite_contact": true,
    "qualify_frequency": 60
  }
}
```

Request for IP-auth/static trunk:

```json
{
  "business_id": 1,
  "name": "IP Auth Trunk",
  "provider_name": "Provider",
  "trunk_mode": "ip_auth",
  "host": "202.40.176.2",
  "port": 5060,
  "max_concurrent_calls": 50,
  "is_active": true,
  "enable_inbound": false,
  "advanced": {
    "transport": "udp",
    "dtmf_mode": "rfc4733",
    "from_user": "09617179124",
    "from_domain": "202.40.176.2",
    "context": "outbound",
    "codecs": ["ulaw", "alaw"]
  }
}
```

Request for global registration trunk:

```json
{
  "scope": "global",
  "name": "Global Provider",
  "provider_name": "Provider",
  "trunk_mode": "registration",
  "host": "202.40.176.2",
  "port": 5060,
  "username": "09617179124",
  "password": "secret",
  "max_concurrent_calls": 50,
  "is_active": true,
  "enable_inbound": false,
  "settings": {
    "global_access": {
      "version": "v2",
      "mode": "allocated",
      "default_max_concurrent_calls": 0,
      "businesses": [
        {"business_id": 1, "max_concurrent_calls": 1},
        {"business_id": 5, "max_concurrent_calls": 1}
      ],
      "stuff_users": []
    }
  },
  "advanced": {
    "transport": "udp",
    "dtmf_mode": "rfc4733",
    "from_user": "09617179124",
    "from_domain": "202.40.176.2",
    "auth_username": "09617179124",
    "context": "outbound",
    "codecs": ["ulaw", "alaw"]
  }
}
```

Request for global trunk with v2 allocation contract:

```json
{
  "scope": "global",
  "name": "Allocated Global Provider",
  "provider_name": "Provider",
  "trunk_mode": "registration",
  "host": "202.40.176.2",
  "port": 5060,
  "username": "09617179124",
  "password": "secret",
  "max_concurrent_calls": 5,
  "is_active": true,
  "enable_inbound": false,
  "settings": {
    "global_access": {
      "version": "v2",
      "mode": "allocated",
      "default_max_concurrent_calls": 0,
      "businesses": [
        {"business_id": 1, "max_concurrent_calls": 1},
        {"business_id": 5, "max_concurrent_calls": 1}
      ],
      "stuff_users": [
        {"stuff_user_id": 9, "max_concurrent_calls": 1},
        {"stuff_user_id": 10, "max_concurrent_calls": 1},
        {"stuff_user_id": 11, "max_concurrent_calls": 1}
      ]
    }
  }
}
```

Required fields:

- `business_id` for business trunks; omit only for superuser global trunk creation
- `name`
- `provider_name`
- `trunk_mode`: `registration` or `ip_auth`
- `host`
- `max_concurrent_calls`
- `is_active`

Registration mode also requires:

- `username`
- `password`

Defaults:

- `port`: `5060`
- `is_active`: `true`
- `enable_inbound`: `false`
- `advanced.transport`: `udp`
- `advanced.dtmf_mode`: `rfc4733`
- `advanced.codecs`: `['ulaw', 'alaw']`
- `advanced.from_user`: defaults to `username`
- `advanced.auth_username`: defaults to `username`
- `advanced.from_domain`: defaults to `host`
- `advanced.context`: `outbound`

Validation:

- `port` must be an integer between `1` and `65535`.
- `max_concurrent_calls` must be greater than `0`.
- `advanced.transport` must be one of `udp`, `tcp`, `tls`.
- `advanced.codecs` currently supports only `ulaw` and `alaw`.

`enable_inbound` behavior:

- Defaults to `false`.
- When `true`, backend sets the trunk endpoint context to `dialyra-inbound-trunk`.
- Backend creates default business inbound-call config if missing.
- Backend syncs realtime identify rows so inbound INVITEs can map to the generated endpoint.
- `enable_inbound=true` is valid only for business-scoped trunks.

Global access behavior:

- Applies only to global trunks.
- Config can be provided at create time via `settings.global_access`.
- v3 global SIP writes require `global_access.version="v2"`.
- v1 or implicit-v1 access such as `{"mode":"all"}` is rejected by v3 write endpoints to prevent broad accidental access.
- v2 is the allocation contract: request with `mode=allocated`, `default_max_concurrent_calls`, `businesses[]`, and `stuff_users[]`.
- A v2 write must define at least one allocation through `default_max_concurrent_calls > 0`, `businesses[]`, or `stuff_users[]`.
- `businesses[].max_concurrent_calls` and `stuff_users[].max_concurrent_calls` default to `default_max_concurrent_calls` when omitted.
- v2 responses include `allocation_mode=allocated` and a v1-compatible `mode|business_ids|stuff_user_ids` projection so old runtime readers do not accidentally treat v2 access as unrestricted.
- If `settings.global_access` is omitted while creating a global trunk, the request fails with a clear validation error.
- Access can be updated later through `PUT /api/v3/sip-trunks/:id/global-access`.
- Non-superuser usage still requires the business to have `allow_global_sip_fallback=true`.
- v2 allocation capacity enforcement is stored by this endpoint and should be enforced by the global SIP selection layer when v2 runtime support is enabled.

Response `201`:

```json
{
  "success": true,
  "trunk_id": 20,
  "business_id": 1,
  "scope": "business",
  "status": "testing",
  "enable_inbound": false,
  "inbound": {
    "enabled": false,
    "context": null,
    "config_created": false
  },
  "message": "SIP trunk saved and synced to realtime tables. Phase 4 status probing is pending."
}
```

Global allocation response `201`:

```json
{
  "success": true,
  "trunk_id": 22,
  "business_id": null,
  "scope": "global",
  "status": "testing",
  "enable_inbound": false,
  "inbound": {
    "enabled": false,
    "context": null,
    "config_created": false
  },
  "global_access": {
    "version": "v2",
    "allocation_mode": "allocated",
    "mode": "business",
    "business_ids": [1, 5],
    "stuff_user_ids": [],
    "default_max_concurrent_calls": 0,
    "businesses": [
      {"business_id": 1, "max_concurrent_calls": 1},
      {"business_id": 5, "max_concurrent_calls": 1}
    ],
    "stuff_users": [
      {"stuff_user_id": 9, "max_concurrent_calls": 1},
      {"stuff_user_id": 10, "max_concurrent_calls": 1},
      {"stuff_user_id": 11, "max_concurrent_calls": 1}
    ]
  },
  "message": "SIP trunk saved and synced to realtime tables. Phase 4 status probing is pending."
}
```

Note:
- The backend currently probes the trunk before returning, so persisted `status`, `apply_status`, `registration_status`, `contact_status`, and `originate_eligible` may already be updated by the time this response is returned. Use `GET /api/v3/sip-trunks/:id/status` for the authoritative post-create diagnostics.

Error examples:

```json
{
  "error": "business_id is required"
}
```

```json
{
  "error": "Inbound enablement requires a business-scoped SIP trunk"
}
```

```json
{
  "error": "Invalid global_access: global_access is required and must use version=v2 with mode=allocated"
}
```

```json
{
  "error": "Invalid global_access: global_access.version must be v2 for v3 global SIP access; v1/implicit access modes are not allowed in v3 writes"
}
```

```json
{
  "error": "Invalid global_access: global_access.mode must be allocated when version=v2"
}
```

```json
{
  "error": "Invalid global_access: global_access must define at least one allocation: default_max_concurrent_calls > 0, businesses[], or stuff_users[]"
}
```

```json
{
  "error": "Invalid global_access: businesses.max_concurrent_calls must be greater than 0 or default_max_concurrent_calls must be greater than 0 when omitted"
}
```

```json
{
  "error": "Invalid global_access: stuff_users.max_concurrent_calls must be greater than 0 or default_max_concurrent_calls must be greater than 0 when omitted"
}
```

```json
{
  "error": "trunk_mode must be registration or ip_auth"
}
```

```json
{
  "error": "username and password are required for registration trunk_mode"
}
```

```json
{
  "error": "SIP trunk name already exists in this business"
}
```

### V3-Prefixed SIP Trunk Management Endpoints

These endpoints mirror the stable v2 SIP trunk management behavior under the v3 prefix.

```text
GET    /api/v3/sip-trunks
GET    /api/v3/sip-trunks/profiles
GET    /api/v3/sip-trunks/:id
PUT    /api/v3/sip-trunks/:id
DELETE /api/v3/sip-trunks/:id
POST   /api/v3/sip-trunks/:id/test
POST   /api/v3/sip-trunks/:id/apply
POST   /api/v3/sip-trunks/:id/rollback
GET    /api/v3/sip-trunks/realtime/health
GET    /api/v3/sip-trunks/drift
```

Notes:

- Business-scoped endpoints are gated by the v3 SIP trunk rollout for the target business when the target business can be determined.
- Global trunk endpoints require `SIP_TRUNK_V3_ENABLED=true`.
- `PUT /api/v3/sip-trunks/:id` does not accept `global_access` changes.
- `PUT /api/v3/sip-trunks/:id` does not require or use `provider_profile`; the backend applies the stored/default SIP profile internally.
- Use `PUT /api/v3/sip-trunks/:id/global-access` for global access changes.
- v3 global access writes must use `version="v2"` and `mode="allocated"`.

If `global_access` is sent to the generic update endpoint, response is `400`:

```json
{
  "error": "global_access cannot be updated through this endpoint",
  "code": "GLOBAL_ACCESS_ENDPOINT_REQUIRED",
  "recommended_endpoint": "/api/v3/sip-trunks/:trunk_id/global-access",
  "recommendation": "Use the v3 global-access endpoint with version=v2 and mode=allocated."
}
```

### Get SIP Trunk Status

`GET /api/v3/sip-trunks/:id/status`

Returns database state, realtime row presence, registration/contact readiness, originate eligibility, active call count, and suggested fixes.

Authorization:

- business-scoped trunks require `businesses.read` for that business
- global trunks are visible only to superuser

Response `200`:

```json
{
  "trunk_id": 20,
  "sip_trunk_id": 20,
  "scope": "business",
  "business_id": 1,
  "trunk_mode": "registration",
  "enable_inbound": true,
  "status": "active",
  "apply_status": "active",
  "registration_status": "registered",
  "contact_status": "not_required",
  "originate_eligible": true,
  "last_error": null,
  "sip_endpoint": "dialyra_b1_t20_trizync_ep",
  "active_calls": 0,
  "max_concurrent_calls": 50,
  "count_source": "ami_live",
  "matched_channels": [],
  "runtime_details": "Response: Success...",
  "checks": {
    "is_active": true,
    "status_active": true,
    "originate_eligible": true,
    "inbound_identify_ready": true,
    "registration_ready": true,
    "contact_ready": true
  },
  "realtime": {
    "ids": {
      "base": "dialyra_b1_t20_trizync",
      "endpoint": "dialyra_b1_t20_trizync_ep",
      "aor": "dialyra_b1_t20_trizync_aor",
      "auth": "dialyra_b1_t20_trizync_auth",
      "registration": "dialyra_b1_t20_trizync_reg",
      "identify": "dialyra_b1_t20_trizync_ident"
    },
    "rows": {
      "ps_endpoints": true,
      "ps_aors": true,
      "ps_auths": true,
      "ps_registrations": true,
      "ps_endpoint_id_ips": true
    }
  },
  "suggested_fixes": []
}
```

Global status responses include:

```json
{
  "scope": "global",
  "business_id": null,
  "global_access": {
    "version": "v1",
    "mode": "all",
    "business_ids": [],
    "stuff_user_ids": []
  }
}
```

Notes:

- `registration_status` can be `registered`, `rejected`, `unregistered`, `unreachable`, `unknown`, or `not_required` depending on trunk mode/runtime output.
- `contact_status` is `not_required` for registration trunks and `static_contact_configured` for healthy `ip_auth` trunks.
- `originate_eligible=true` means the trunk is eligible for outbound call selection.
- `inbound_identify_ready=true` is required when `enable_inbound=true`.

### Reload SIP Trunk

`POST /api/v3/sip-trunks/:id/reload`

Reloads/syncs a business or global trunk and optionally enables inbound mapping for business trunks.

Request:

```json
{
  "enable_inbound": true
}
```

`enable_inbound` defaults to `false` for reload requests.

When `enable_inbound=true`:

- backend enables inbound context for the trunk
- creates default business inbound-call config if missing
- syncs realtime rows
- reloads PJSIP
- probes status again

Global reload behavior:

- Superuser can reload global trunks.
- `enable_inbound=true` is rejected for global trunks.

Response `200`:

```json
{
  "trunk_id": 20,
  "sip_trunk_id": 20,
  "business_id": 1,
  "trunk_mode": "registration",
  "enable_inbound": true,
  "status": "active",
  "apply_status": "active",
  "registration_status": "registered",
  "contact_status": "not_required",
  "originate_eligible": true,
  "checks": {
    "is_active": true,
    "status_active": true,
    "originate_eligible": true,
    "inbound_identify_ready": true,
    "registration_ready": true,
    "contact_ready": true
  },
  "realtime": {
    "ids": {
      "base": "dialyra_b1_t20_trizync",
      "endpoint": "dialyra_b1_t20_trizync_ep",
      "aor": "dialyra_b1_t20_trizync_aor",
      "auth": "dialyra_b1_t20_trizync_auth",
      "registration": "dialyra_b1_t20_trizync_reg",
      "identify": "dialyra_b1_t20_trizync_ident"
    },
    "rows": {
      "ps_endpoints": true,
      "ps_aors": true,
      "ps_auths": true,
      "ps_registrations": true,
      "ps_endpoint_id_ips": true
    }
  },
  "suggested_fixes": [],
  "reload": {
    "status": "reloaded",
    "enable_inbound": true
  }
}
```

### Update Global SIP Access

`PUT /api/v3/sip-trunks/:id/global-access`

Updates who can use a global SIP trunk for outbound fallback/origination.

Authorization:

- superuser only
- trunk must have `scope="global"`
- v3 writes require `version="v2"` and `mode="allocated"`.
- v1/implicit access modes are rejected by this endpoint.
- non-superuser usage still requires the business to have `allow_global_sip_fallback=true`

Request:

```json
{
  "version": "v2",
  "mode": "allocated",
  "default_max_concurrent_calls": 0,
  "businesses": [
    {"business_id": 1, "max_concurrent_calls": 1},
    {"business_id": 5, "max_concurrent_calls": 1}
  ],
  "stuff_users": [
    {"stuff_user_id": 9, "max_concurrent_calls": 1},
    {"stuff_user_id": 10, "max_concurrent_calls": 1}
  ]
}
```

Response `200`:

```json
{
  "sip_trunk_id": 20,
  "scope": "global",
  "global_access": {
    "version": "v2",
    "allocation_mode": "allocated",
    "mode": "business",
    "business_ids": [1, 5],
    "stuff_user_ids": [],
    "default_max_concurrent_calls": 0,
    "businesses": [
      {"business_id": 1, "max_concurrent_calls": 1},
      {"business_id": 5, "max_concurrent_calls": 1}
    ],
    "stuff_users": [
      {"stuff_user_id": 9, "max_concurrent_calls": 1},
      {"stuff_user_id": 10, "max_concurrent_calls": 1}
    ]
  }
}
```

Error examples:

```json
{
  "error": "global access can only be configured for global SIP trunks"
}
```

```json
{
  "error": "global_access.version must be v2 for v3 global SIP access; v1/implicit access modes are not allowed in v3 writes"
}
```

```json
{
  "error": "global_access.mode must be allocated when version=v2"
}
```

```json
{
  "error": "global_access must define at least one allocation: default_max_concurrent_calls > 0, businesses[], or stuff_users[]"
}
```

```json
{
  "error": "businesses.max_concurrent_calls must be greater than 0 or default_max_concurrent_calls must be greater than 0 when omitted"
}
```

```json
{
  "error": "stuff_users.max_concurrent_calls must be greater than 0 or default_max_concurrent_calls must be greater than 0 when omitted"
}
```

## Runtime Calls v3

### Originate Runtime Call

`POST /api/v3/runtime/calls/originate`

Starts an outbound call for the authenticated access-token business.

Required access-token scope:

```text
calls:originate
```

Request:

```json
{
  "phone": "01631596697",
  "sip_trunk_id": 20,
  "flow_id": 7,
  "campaign_id": null,
  "campaign_flow_id": null,
  "webhook_variables": {
    "customer_name": "Rahim",
    "invoice_id": "INV-1001"
  }
}
```

Fields:

- `phone` required.
- `sip_trunk_id` optional. If omitted, backend picks a ready business trunk with available capacity.
- `flow_id` optional. If omitted, backend may use the business/default flow selection logic.
- `campaign_id` optional.
- `campaign_flow_id` optional.
- `webhook_variables` optional object for flow/webhook template variables.

`webhook_variables` validation:

- must be an object
- max `100` keys
- key max length `64`
- keys must match `A-Za-z0-9_`
- cannot override reserved system variables
- JSON payload max size `16 KB`
- `template_variables` is not supported; use `webhook_variables`

Trunk selection behavior:

- If `sip_trunk_id` is provided, that trunk must belong to the business or be a global trunk allowed by the business.
- If validation bypass is disabled, the selected trunk must be originate-ready.
- If `sip_trunk_id` is omitted, backend selects the least-busy ready business trunk.
- If no ready business trunk exists and business global fallback is allowed, backend selects a ready global trunk.
- Capacity checks are enforced by trunk/business/system call limits.
- For global trunks with `global_access.version="v2"`, backend also enforces the matched allocation limit.
- v2 allocation matching prefers `stuff_users[]` for a stuff actor, then `businesses[]`, then `default_max_concurrent_calls`.
- `selected_by` can be `requested`, `auto_business`, or `auto_global_fallback`.

Billing behavior:

- If billing enforcement blocks the call, response is `402`.
- Blocked billing responses include insufficient-credit details.

Response `200`:

```json
{
  "status": "initiated",
  "phone": "01631596697",
  "business_id": 1,
  "call_log_uuid": "3abaf575-5980-4db2-a2c3-1338ec44a4ee",
  "call_session_id": 170,
  "action_id": "102bae32-7661-4161-95e0-bd0b9d535af4",
  "sip_trunk_id": 20,
  "sip_endpoint": "dialyra_b1_t20_trizync_ep",
  "selected_by": "requested",
  "selected_flow_id": 7,
  "selected_flow_version_id": 12,
  "flow_selected_by": "explicit_flow_id",
  "active_calls_before": 0,
  "max_concurrent_calls": 50,
  "business_active_calls_before": 0,
  "business_max_concurrent_calls": 0,
  "system_active_calls_before": 0,
  "system_max_concurrent_calls": 0,
  "billing": {
    "status": "reserved",
    "reservation_key": "call-session-170",
    "reserved_amount": "2.000000"
  },
  "auth_type": "access_token",
  "response": "Response: Success...",
  "api_version_used": "v3",
  "validation_bypassed": false,
  "validation_mode": "strict"
}
```

When a v2 global allocation is used, the response also includes allocation metadata:

```json
{
  "global_access_version": "v2",
  "global_allocation_scope": "business",
  "global_allocation_owner_id": 1,
  "global_allocation_active_calls_before": 0,
  "global_allocation_max_concurrent_calls": 1,
  "global_allocation_remaining_calls": 1
}
```

Common error responses:

Validation error `400`:

```json
{
  "error": "Missing required field: phone"
}
```

Trunk not ready `409`:

```json
{
  "status": "warning",
  "code": "TRUNK_NOT_READY",
  "message": "registration_not_ready",
  "trunk_diagnostics": {
    "trunk_id": 20,
    "trunk_mode": "registration",
    "registration_status": "rejected",
    "contact_status": "not_required",
    "originate_eligible": false,
    "checks": {
      "is_active": true,
      "status_active": false,
      "originate_eligible": false,
      "inbound_identify_ready": true,
      "registration_ready": false,
      "contact_ready": true
    },
    "last_error": "Registration status is rejected",
    "suggested_fixes": [
      "Check SIP username and password",
      "Set advanced.auth_username same as username",
      "Set advanced.from_user same as username",
      "Set advanced.from_domain to provider domain/host"
    ]
  }
}
```

No SIP available `409`:

```json
{
  "status": "warning",
  "code": "NO_SIP_AVAILABLE",
  "message": "No ready business SIP trunk and global fallback is disabled",
  "suggested_fixes": [
    "Activate at least one business SIP trunk",
    "Ensure trunk status is active and originate_eligible is true",
    "Enable business global SIP fallback if global trunks should be used"
  ]
}
```

Billing blocked `402`:

```json
{
  "error": "insufficient credits",
  "code": "INSUFFICIENT_CREDIT",
  "reason_code": "insufficient_credit",
  "required_credit": "2.000000",
  "available_credit": "1.000000",
  "billing_owner_user_id": 2
}
```

AMI connectivity errors `502`:

```json
{
  "error": "Failed to connect to AMI",
  "details": "timed out"
}
```

## Operational Notes

### Verify Realtime SIP Rows

For a v3 trunk status response, check:

```json
{
  "realtime": {
    "rows": {
      "ps_endpoints": true,
      "ps_aors": true,
      "ps_auths": true,
      "ps_registrations": true,
      "ps_endpoint_id_ips": true
    }
  }
}
```

For registration trunks, `ps_registrations=true` is expected.

For IP-auth trunks, static contact and identify readiness are more important than registration.

### Verify Asterisk Runtime

Useful Asterisk CLI commands:

```text
pjsip show endpoints
pjsip show registrations
pjsip show contacts
pjsip show endpoint <endpoint_name>
pjsip show identifies
```

### Inbound Enablement

`enable_inbound=true` is intentionally explicit.

Do not automatically enable provider SIP trunks for inbound unless the create/reload payload requests it.

When enabled, status should show:

```json
{
  "enable_inbound": true,
  "checks": {
    "inbound_identify_ready": true
  },
  "realtime": {
    "rows": {
      "ps_endpoint_id_ips": true
    }
  }
}
```
