# API v2 Request/Response Schema

Base URL prefix: `/api/v2`

## Common Headers

- JWT endpoints: `Authorization: Bearer <jwt_token>`
- Access-token runtime endpoints:  
  `X-Dialyra-Access-Token: <token>` or `Authorization: Bearer <access_token>`

## Common Error Response

```json
{
  "error": "string"
}
```

---

## Health

### `GET /api/v2/health`

Response `200`:

```json
{
  "status": "ok"
}
```

---

## Auth

### `POST /api/v2/auth/register`

Request:

```json
{
  "full_name": "string",
  "email": "string",
  "password": "string",
  "role": "stuff|general (default: general)"
}
```

Note:
- Only these four fields are accepted for register flow.

Response `201`:

```json
{
  "message": "Registration successful",
  "business": null,
  "user": {
    "id": 1,
    "full_name": "string",
    "email": "string",
    "role": "superuser|stuff|general",
    "status": "active|inactive|suspended",
    "last_login_at": "ISO_DATETIME|null",
    "created_at": "ISO_DATETIME",
    "updated_at": "ISO_DATETIME"
  },
  "access_token": "jwt",
  "refresh_token": "string"
}
```

### `POST /api/v2/auth/bootstrap-superuser`

Headers:
- `X-Bootstrap-Secret: <secret>`

Request:

```json
{
  "full_name": "string",
  "email": "string",
  "password": "string"
}
```

Response `201`:

```json
{
  "message": "Superuser created successfully",
  "user": {
    "id": 1,
    "full_name": "string",
    "email": "string",
    "role": "superuser",
    "status": "active",
    "last_login_at": null,
    "created_at": "ISO_DATETIME",
    "updated_at": "ISO_DATETIME"
  },
  "access_token": "jwt",
  "refresh_token": "string"
}
```

### `POST /api/v2/auth/login`

Request:

```json
{
  "email": "string",
  "password": "string"
}
```

Response `200`:

```json
{
  "access_token": "jwt",
  "refresh_token": "string",
  "user": {
    "id": 1,
    "full_name": "string",
    "email": "string",
    "role": "superuser|stuff|general",
    "status": "active|inactive|suspended",
    "last_login_at": "ISO_DATETIME|null",
    "created_at": "ISO_DATETIME",
    "updated_at": "ISO_DATETIME"
  },
  "business": {
    "id": 1,
    "name": "string",
    "slug": "string",
    "owner_user_id": 1,
    "phone": "string",
    "email": "string",
    "status": "active",
    "created_at": "ISO_DATETIME",
    "updated_at": "ISO_DATETIME"
  }
}
```

### `POST /api/v2/auth/refresh`

Request:

```json
{
  "refresh_token": "string"
}
```

Response `200`:

```json
{
  "access_token": "jwt",
  "refresh_token": "string",
  "user": {
    "id": 1,
    "full_name": "string",
    "email": "string",
    "role": "superuser|stuff|general",
    "status": "active|inactive|suspended",
    "last_login_at": "ISO_DATETIME|null",
    "created_at": "ISO_DATETIME",
    "updated_at": "ISO_DATETIME"
  }
}
```

### `POST /api/v2/auth/logout`

Request:

```json
{
  "refresh_token": "string"
}
```

Response `200`:

```json
{
  "message": "Logout successful"
}
```

### `GET /api/v2/auth/me`

Response `200`:

```json
{
  "user": {
    "id": 1,
    "full_name": "string",
    "email": "string",
    "role": "superuser|stuff|general",
    "status": "active|inactive|suspended",
    "last_login_at": "ISO_DATETIME|null",
    "created_at": "ISO_DATETIME",
    "updated_at": "ISO_DATETIME"
  },
  "business": {
    "id": 1,
    "name": "string",
    "slug": "string",
    "owner_user_id": 1,
    "phone": "string",
    "email": "string",
    "status": "active",
    "created_at": "ISO_DATETIME",
    "updated_at": "ISO_DATETIME"
  }
}
```

### `POST /api/v2/auth/users`

Request:

```json
{
  "full_name": "string",
  "email": "string",
  "password": "string",
  "role": "superuser|stuff|general",
  "business_id": 1,
  "membership_role": "admin|manager|agent|viewer"
}
```

### `GET /api/v2/auth/users`

Access:
- `superuser|stuff`

Response `200` for superuser:

```json
{
  "items": [
    {
      "id": 1,
      "full_name": "string",
      "email": "string",
      "role": "superuser|stuff|general",
      "status": "active|inactive|suspended",
      "last_login_at": "ISO_DATETIME|null",
      "created_at": "ISO_DATETIME",
      "updated_at": "ISO_DATETIME"
    }
  ]
}
```

Response `200` for stuff (members of owned businesses):

```json
{
  "items": [
    {
      "user": {
        "id": 2,
        "full ready._name": "string",
        "email": "string",
        "role": "general",
        "status": "active",
        "last_login_at": null,
        "created_at": "ISO_DATETIME",
        "updated_at": "ISO_DATETIME"
      },
      "memberships": [
        {
          "membership_id": 5,
          "business_id": 1,
          "membership_role": "viewer",
          "membership_status": "active",
          "joined_at": "ISO_DATETIME"
        }
      ]
    }
  ]
}
```

Note:
- `stuff` can create only `general`.
- `superuser` can create `superuser|stuff|general`.
- For `general`, `business_id` and `membership_role` are required.
- Stuff user can only pass a `business_id` they own.
- Superuser can pass any valid business id when creating `general`.
- Membership is auto-created only when `role=general`.

Response `201`:

```json
{
  "message": "User created successfully",
  "user": {
    "id": 1,
    "full_name": "string",
    "email": "string",
    "role": "superuser|stuff|general",
    "status": "active|inactive|suspended",
    "last_login_at": null,
    "created_at": "ISO_DATETIME",
    "updated_at": "ISO_DATETIME"
  }
}
```

### `PUT /api/v2/auth/users`

Updates the authenticated user's own profile.

Access:
- Any authenticated active user.

Request:

```json
{
  "full_name": "Updated Name",
  "email": "updated@example.com"
}
```

Notes:
- Self update supports only `full_name` and `email`.
- `status` and `role` are not self-managed fields.
- Duplicate email returns `409`.
- Invalid email format returns `400`.

Response `200`:

```json
{
  "message": "User updated successfully",
  "user": {
    "id": 1,
    "full_name": "Updated Name",
    "email": "updated@example.com",
    "role": "superuser|stuff|general",
    "status": "active|inactive|suspended",
    "last_login_at": "ISO_DATETIME|null",
    "created_at": "ISO_DATETIME",
    "updated_at": "ISO_DATETIME"
  }
}
```

### `PUT /api/v2/auth/users/:user_id`

Updates a user's account-level details and status.

Access:
- `superuser`

Request:

```json
{
  "full_name": "Updated Name",
  "email": "updated@example.com",
  "status": "active|inactive|suspended"
}
```

Notes:
- Any subset of `full_name`, `email`, and `status` can be sent.
- `role` is not editable from this endpoint.
- This updates `users.status`, not workspace membership status.
- Duplicate email returns `409`.
- Invalid email format returns `400`.
- The last active superuser cannot be changed to `inactive` or `suspended`.

Response `200`:

```json
{
  "message": "User updated successfully",
  "user": {
    "id": 2,
    "full_name": "Updated Name",
    "email": "updated@example.com",
    "role": "superuser|stuff|general",
    "status": "active|inactive|suspended",
    "last_login_at": "ISO_DATETIME|null",
    "created_at": "ISO_DATETIME",
    "updated_at": "ISO_DATETIME"
  }
}
```

### `PUT /api/v2/auth/users/password`

Changes the authenticated user's own password.

Access:
- Any authenticated active user.

Request:

```json
{
  "current_password": "old-password",
  "new_password": "new-password",
  "idempotency_key": "change-password-2026-08-13-0001"
}
```

Rules:
- `idempotency_key` is required and must be provided by the client.
- `new_password` must be 8-128 characters and cannot be whitespace only.
- `new_password` must include at least one letter and one number.
- `new_password` must be different from the current password.
- Existing refresh tokens for the user are revoked after a successful change.
- Raw passwords are never returned or stored in idempotency/audit records.

Response `200`:

```json
{
  "message": "Password changed successfully",
  "idempotent_replay": false,
  "sessions_revoked": true,
  "revoked_refresh_tokens": 2
}
```

Idempotent replay response `200`:

```json
{
  "message": "Password changed successfully",
  "idempotent_replay": true,
  "sessions_revoked": true,
  "revoked_refresh_tokens": 2
}
```

Conflict response `409` when the same key is reused with a different request:

```json
{
  "error": "IDEMPOTENCY_KEY_CONFLICT",
  "message": "idempotency_key was already used with a different request. Use a new idempotency_key."
}
```

### `PUT /api/v2/auth/users/:user_id/password`

Resets a user's password.

Access:
- `superuser`

Request:

```json
{
  "new_password": "new-password",
  "revoke_sessions": true,
  "idempotency_key": "reset-user-2-password-2026-08-13-0001"
}
```

Rules:
- `idempotency_key` is required and must be provided by the client.
- `revoke_sessions` defaults to `true`.
- `revoke_sessions` must be a JSON boolean when provided.
- `new_password` must be 8-128 characters and cannot be whitespace only.
- `new_password` must include at least one letter and one number.
- Raw passwords are never returned or stored in idempotency/audit records.

Response `200`:

```json
{
  "message": "Password reset successfully",
  "idempotent_replay": false,
  "user_id": 2,
  "sessions_revoked": true,
  "revoked_refresh_tokens": 2
}
```

Idempotent replay response `200`:

```json
{
  "message": "Password reset successfully",
  "idempotent_replay": true,
  "user_id": 2,
  "sessions_revoked": true,
  "revoked_refresh_tokens": 2
}
```

Conflict response `409` when the same key is reused with a different request:

```json
{
  "error": "IDEMPOTENCY_KEY_CONFLICT",
  "message": "idempotency_key was already used with a different request. Use a new idempotency_key."
}
```

### `POST /api/v2/auth/users/:user_id/forgot-password-link`

Generates a backend-created forgot-password reset link for a user.

Access:
- `superuser`

Request:

```json
{
  "expires_in_minutes": 30,
  "revoke_existing": true,
  "redirect_url": "https://app.example.com/reset-password"
}
```

Rules:
- Client does not provide `idempotency_key`; backend generates it using actor, target user, normalized request, and a short time bucket.
- Same actor/user/payload within the idempotency bucket returns the same reset link with `idempotent_replay=true`.
- Target user must have `status=active`; inactive or suspended users cannot receive reset links.
- `expires_in_minutes` defaults to `AUTH_FORGOT_PASSWORD_LINK_TTL_MINUTES`.
- `expires_in_minutes` must be between `AUTH_FORGOT_PASSWORD_LINK_MIN_TTL_MINUTES` and `AUTH_FORGOT_PASSWORD_LINK_MAX_TTL_MINUTES`.
- `revoke_existing` defaults to `true` and revokes active unused reset links for the target user before creating the new link.
- `redirect_url` defaults to `AUTH_FORGOT_PASSWORD_RESET_BASE_URL` when omitted.
- `redirect_url` must be an absolute `http` or `https` URL. Existing `token` query params are removed before appending the generated token.
- Reset URL is encrypted at rest; raw token is never stored in plaintext.
- `reset_url` is returned only by this generation/replay endpoint and should not be stored by clients longer than needed.

Response `201`:

```json
{
  "message": "Forgot password link generated successfully",
  "idempotent_replay": false,
  "link_id": 1,
  "user_id": 2,
  "expires_at": "2026-08-13T12:30:00",
  "status": "active",
  "reset_url": "https://app.example.com/reset-password?token=RAW_TOKEN",
  "revoked_existing_count": 1
}
```

Idempotent replay response `200`:

```json
{
  "message": "Forgot password link generated successfully",
  "idempotent_replay": true,
  "link_id": 1,
  "user_id": 2,
  "expires_at": "2026-08-13T12:30:00",
  "status": "active",
  "reset_url": "https://app.example.com/reset-password?token=SAME_RAW_TOKEN"
}
```

Inactive/suspended target response `400`:

```json
{
  "error": "forgot_password_target_user_not_active"
}
```

Replay conflict response `409`:

```json
{
  "error": "forgot_password_link_not_replayable"
}
```

### `POST /api/v2/auth/forgot-password?token=RAW_TOKEN`

Public reset endpoint that consumes a backend-generated forgot-password token.

Access:
- Public; no JWT required.

Request:

```json
{
  "new_password": "NewPassword123",
  "confirm_password": "NewPassword123"
}
```

Rules:
- `token` query parameter is required. Because query strings can appear in access logs/browser history, deployment logging should avoid storing raw query strings for this endpoint.
- Token is hashed server-side before lookup; raw token is never stored in plaintext.
- Token must be active, unused, unrevoked, and unexpired.
- Target user must still exist and have `status=active`.
- `new_password` and `confirm_password` must match.
- `new_password` must pass the same password policy as other password reset endpoints: 8-128 characters, not whitespace-only, at least one letter, and at least one number.
- New password must differ from the current password.
- On success, the reset link is marked `used` and existing refresh tokens are revoked.
- Repeated failed attempts for the same token hash are rate-limited using `AUTH_FORGOT_PASSWORD_CONFIRM_MAX_ATTEMPTS` and `AUTH_FORGOT_PASSWORD_CONFIRM_WINDOW_MINUTES`.

Response `200`:

```json
{
  "message": "Password reset successfully",
  "sessions_revoked": true,
  "revoked_refresh_tokens": 2
}
```

Invalid or expired token response `400`:

```json
{
  "error": "forgot_password_link_invalid_or_expired",
  "message": "Password reset link is invalid or expired."
}
```

Rate limit response `429`:

```json
{
  "error": "forgot_password_rate_limited",
  "message": "Too many password reset attempts. Try again later."
}
```

Password mismatch response `400`:

```json
{
  "error": "confirm_password must match new_password"
}
```

Forgot-password configuration:

| Env var | Default | Purpose |
| --- | --- | --- |
| `AUTH_FORGOT_PASSWORD_LINK_TTL_MINUTES` | `30` | Default reset-link lifetime. |
| `AUTH_FORGOT_PASSWORD_LINK_MIN_TTL_MINUTES` | `5` | Minimum accepted `expires_in_minutes`. |
| `AUTH_FORGOT_PASSWORD_LINK_MAX_TTL_MINUTES` | `1440` | Maximum accepted `expires_in_minutes`. |
| `AUTH_FORGOT_PASSWORD_LINK_IDEMPOTENCY_BUCKET_SECONDS` | `300` | Backend idempotency replay window for generated links. |
| `AUTH_FORGOT_PASSWORD_RESET_BASE_URL` | `http://localhost:3000/reset-password` | Default public reset page URL used when `redirect_url` is omitted. |
| `AUTH_FORGOT_PASSWORD_CONFIRM_MAX_ATTEMPTS` | `10` | Failed confirm attempts allowed per token hash. |
| `AUTH_FORGOT_PASSWORD_CONFIRM_WINDOW_MINUTES` | `15` | Rate-limit window for public confirm attempts. |

### `POST /api/v2/auth/users/:user_id/membership`
### `PUT /api/v2/auth/users/:user_id/membership`

Request:

```json
{
  "business_id": 1,
  "membership_role": "admin|manager|agent|viewer",
  "status": "active|inactive|suspended"
}
```

Note:
- `role` can be used as fallback alias for `membership_role`.
- Only `general` users can be assigned/updated by this endpoint.

Response `200`:

```json
{
  "message": "Membership created successfully",
  "membership": {
    "id": 1,
    "business_id": 1,
    "user_id": 2,
    "membership_role": "viewer",
    "status": "active",
    "joined_at": "ISO_DATETIME"
  }
}
```

### `DELETE /api/v2/auth/users/:user_id/membership`

Request:

```json
{
  "business_id": 1
}
```

Response `200`:

```json
{
  "message": "Membership removed successfully"
}
```

### `GET /api/v2/auth/authz-diffs`

Query params:
- `limit` (optional, default `100`, max `500`)
- `actor_user_id` (optional)
- `business_id` (optional)

Response `200`:

```json
{
  "items": [
    {
      "id": 1,
      "created_at": "ISO_DATETIME",
      "actor_user_id": 1,
      "business_id": 1,
      "action": "authz.decision_diff",
      "metadata": {}
    }
  ],
  "count": 1
}
```

---

## Businesses

### `POST /api/v2/businesses`

Request:

```json
{
  "name": "string",
  "slug": "string",
  "email": "string",
  "phone": "string",
  "timezone": "Asia/Dhaka",
  "country": "Bangladesh"
}
```

Response `201`:

```json
{
  "id": 1,
  "uuid": "string",
  "name": "string",
  "slug": "string",
  "owner_user_id": 1,
  "email": "string",
  "phone": "string",
  "timezone": "string",
  "country": "string|null",
  "logo_path": "string|null",
  "status": "active|inactive|suspended|deleted",
  "settings": {},
  "allow_global_sip_fallback": false,
  "sip_login_prefix": "string|null",
  "deleted_at": "ISO_DATETIME|null",
  "created_at": "ISO_DATETIME",
  "updated_at": "ISO_DATETIME"
}
```

### `GET /api/v2/businesses`

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
      "phone": "string",
      "timezone": "string",
      "country": "string|null",
      "logo_path": "string|null",
      "status": "active|inactive|suspended|deleted",
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

### `GET /api/v2/businesses/:business_id`

Response `200`: same business object as above.

### `PUT /api/v2/businesses/:business_id`

Request (all fields optional):

```json
{
  "name": "string",
  "email": "string",
  "phone": "string",
  "timezone": "string",
  "country": "string",
  "logo_path": "string",
  "status": "active|inactive|suspended|deleted"
}
```

Response `200`: same business object as above.

### `DELETE /api/v2/businesses/:business_id`

Behavior:
- Soft delete only.
- Sets business `status` to `deleted`.
- Sets `deleted_at` timestamp.

Response `200`:

```json
{
  "message": "Business deleted"
}
```

### `GET /api/v2/businesses/:business_id/settings`

Response `200`:

```json
{
  "business_id": 1,
  "settings": {}
}
```

### `PUT /api/v2/businesses/:business_id/settings`

Request:

```json
{
  "settings": {
    "max_users": 50,
    "max_concurrent_calls": 10,
    "max_campaigns": 5,
    "max_sip_trunks": 3,
    "max_storage": 1024
  }
}
```

Response `200`:

```json
{
  "business_id": 1,
  "settings": {}
}
```

### `GET /api/v2/businesses/:business_id/inbound-call-config`

Returns the saved inbound call config plus the effective flow that would be used for inbound calls.

If no config row exists, response returns an implicit default:

- `enabled=true`
- `flow_id=null`
- `fallback_mode=latest_published_flow`
- effective flow resolves to the latest published flow for the business

Response `200`:

```json
{
  "id": 1,
  "business_id": 1,
  "enabled": true,
  "flow_id": 12,
  "fallback_mode": "latest_published_flow",
  "metadata": {},
  "source": "saved_config",
  "effective_flow_id": 12,
  "effective_flow_version_id": 18,
  "effective_source": "configured_flow",
  "ready_for_inbound": true,
  "readiness_reason": null,
  "created_at": "ISO_DATETIME",
  "updated_at": "ISO_DATETIME"
}
```

Implicit default response example:

```json
{
  "id": null,
  "business_id": 1,
  "enabled": true,
  "flow_id": null,
  "fallback_mode": "latest_published_flow",
  "metadata": null,
  "source": "implicit_default",
  "effective_flow_id": 15,
  "effective_flow_version_id": 21,
  "effective_source": "latest_published_flow",
  "ready_for_inbound": true,
  "readiness_reason": null,
  "created_at": null,
  "updated_at": null
}
```

Possible `effective_source` values:

- `configured_flow`
- `latest_published_flow`
- `none`

Possible `readiness_reason` values:

- `inbound_disabled`
- `configured_flow_unpublished`
- `no_published_flow`
- `business_not_found`

### `POST /api/v2/businesses/:business_id/inbound-call-config`

Creates inbound call config for the business.

Request:

```json
{
  "enabled": true,
  "flow_id": 12,
  "fallback_mode": "latest_published_flow",
  "metadata": {
    "note": "Main inbound IVR"
  }
}
```

Fields:

- `enabled`: optional boolean, default `true`
- `flow_id`: optional published flow id from the same business
- `fallback_mode`: optional, `latest_published_flow|strict_configured_flow`
- `metadata`: optional object

Response `201`: same shape as `GET /api/v2/businesses/:business_id/inbound-call-config`.

Errors:

```json
{"error": "Inbound call config already exists for this business"}
```

```json
{"error": "flow_id must reference a published flow for this business"}
```

```json
{"error": "fallback_mode must be one of: latest_published_flow, strict_configured_flow"}
```

### `PUT /api/v2/businesses/:business_id/inbound-call-config`

Updates inbound call config for the business. If the config row does not exist, backend creates it with defaults and applies the provided fields.

Request (all fields optional):

```json
{
  "enabled": true,
  "flow_id": 15,
  "fallback_mode": "strict_configured_flow",
  "metadata": {
    "note": "Use support IVR only"
  }
}
```

Response `200`: same shape as `GET /api/v2/businesses/:business_id/inbound-call-config`.

Validation:

- `flow_id` must belong to the same business.
- `flow_id` must have an active published flow version.
- `fallback_mode=latest_published_flow` falls back to latest published business flow when configured flow is missing/unpublished.
- `fallback_mode=strict_configured_flow` requires the configured flow to be usable.
- `enabled=false` disables inbound flow execution for the business.

### `POST /api/v2/businesses/:business_id/members`

Request:

```json
{
  "user_id": 2,
  "role": "admin|manager|agent|viewer",
  "status": "active|inactive|suspended"
}
```

Response `201`:

```json
{
  "id": 1,
  "business_id": 1,
  "user_id": 2,
  "role": "viewer",
  "status": "active",
  "joined_at": "ISO_DATETIME"
}
```

### `GET /api/v2/businesses/:business_id/members`

Response `200`:

```json
{
  "items": [
    {
      "id": 1,
      "business_id": 1,
      "user_id": 2,
      "role": "viewer",
      "status": "active",
      "joined_at": "ISO_DATETIME"
    }
  ]
}
```

### `PUT /api/v2/businesses/:business_id/members/:member_id`

Request (any of):

```json
{
  "role": "admin|manager|agent|viewer",
  "status": "active|inactive|suspended"
}
```

Response `200`:

```json
{
  "id": 1,
  "business_id": 1,
  "user_id": 2,
  "role": "manager",
  "status": "active",
  "joined_at": "ISO_DATETIME"
}
```

### `DELETE /api/v2/businesses/:business_id/members/:member_id`

Response `200`:

```json
{
  "message": "Member removed"
}
```

### `POST /api/v2/businesses/:business_id/transfer-ownership`

Request:

```json
{
  "target_user_id": 2
}
```

Response `200`:

```json
{
  "message": "Ownership transferred successfully",
  "business_id": 1,
  "owner_user_id": 2
}
```

### `POST /api/v2/businesses/:business_id/global-sip/enable`

Enables global SIP trunk fallback for the business. Superuser only.

Response `200`:

```json
{
  "business_id": 1,
  "allow_global_sip_fallback": true
}
```

### `POST /api/v2/businesses/:business_id/global-sip/disable`

Disables global SIP trunk fallback for the business. Superuser only.

Response `200`:

```json
{
  "business_id": 1,
  "allow_global_sip_fallback": false
}
```

---

## Access Tokens

### `POST /api/v2/access-tokens`

Request:

```json
{
  "name": "Production Runtime",
  "business_id": 1,
  "expires_days": 365,
  "scopes": ["calls:originate", "calls:read"]
}
```

Response `201`:

```json
{
  "token": "dialyra_live_xxx",
  "message": "Save this token now. It will not be shown again.",
  "access_token": {
    "id": 1,
    "business_id": 1,
    "name": "Production Runtime",
    "token_prefix": "dialyra_live_xxx",
    "scopes": ["calls:originate"],
    "is_active": true,
    "last_used_at": null,
    "expires_at": "ISO_DATETIME",
    "created_by": 1,
    "created_at": "ISO_DATETIME",
    "revoked_at": null
  }
}
```

### `GET /api/v2/access-tokens`

Query params:
- `business_id` (optional for privileged roles, required for some contexts)

Response `200`:

```json
{
  "items": [
    {
      "id": 1,
      "business_id": 1,
      "name": "string",
      "token_prefix": "string",
      "scopes": [],
      "is_active": true,
      "last_used_at": "ISO_DATETIME|null",
      "expires_at": "ISO_DATETIME|null",
      "created_by": 1,
      "created_at": "ISO_DATETIME",
      "revoked_at": "ISO_DATETIME|null"
    }
  ]
}
```

### `GET /api/v2/access-tokens/:token_id`

Response `200`: `access_token` object shape above (without wrapper).

### `POST /api/v2/access-tokens/:token_id/revoke`

Response `200`:

```json
{
  "message": "Access token revoked",
  "access_token": {
    "id": 1,
    "business_id": 1,
    "name": "string",
    "token_prefix": "string",
    "scopes": [],
    "is_active": false,
    "last_used_at": "ISO_DATETIME|null",
    "expires_at": "ISO_DATETIME|null",
    "created_by": 1,
    "created_at": "ISO_DATETIME",
    "revoked_at": "ISO_DATETIME"
  }
}
```

### `DELETE /api/v2/access-tokens/:token_id`

Response `200`:

```json
{
  "message": "Access token deleted"
}
```

### Access Token Scopes (Current)

- `calls:originate`
  - `POST /api/v2/runtime/calls/originate`
  - `POST /api/v2/runtime/calls/:call_id/retry`
- `calls:hangup`
  - `POST /api/v2/runtime/calls/:call_id/hangup`
- `calls:read`
  - `GET /api/v2/runtime/calls` (alias: `/api/v2/calls`)
  - `GET /api/v2/runtime/calls/:call_id` (alias: `/api/v2/calls/:call_id`)
  - `GET /api/v2/runtime/calls/events`
  - `GET /api/v2/runtime/calls/webhook-jobs`
  - `GET /api/v2/runtime/calls/:call_id/webhook-jobs`
  - `GET /api/v2/runtime/calls/webhook-worker/health`
  - `GET /api/v2/runtime/calls/webhook-jobs/:job_id`
  - `POST /api/v2/runtime/calls/webhook-jobs/:job_id/retry`
  - `POST /api/v2/runtime/calls/webhook-jobs/retry`
  - `GET /api/v2/runtime/calls/webhook-jobs/summary`

Internal runtime scopes (used by internal/call-token compatible endpoints):

- `flow:resolve`
  - `POST /api/v2/internal/flow/resolve-next`
- `fastagi:runtime`
  - `GET /api/v2/internal/flows/:flow_id/runtime`
  - `POST /api/v2/internal/calls/:call_id/node-entered`
  - `POST /api/v2/internal/calls/:call_id/node-completed`
  - `GET /api/v2/internal/audio-assets/:asset_id/playback-target`
- `events:write`
  - `POST /api/v2/internal/calls/:call_id/dtmf`
  - `POST /api/v2/internal/calls/:call_id/playback-event`
  - `POST /api/v2/internal/calls/:call_id/runtime-error`
  - `POST /api/v2/internal/calls/:call_id/transfer-event`
  - `POST /api/v2/internal/calls/:call_id/wait-event`
  - `POST /api/v2/internal/calls/:call_id/record-event`
  - `POST /api/v2/internal/call-events`
  - `GET /api/v2/internal/call-events`
  - `POST /api/v2/internal/call-events/:event_id/reprocess`

---

## Flows (Draft CRUD)

These endpoints are JWT-protected and currently support draft lifecycle operations.

### `POST /api/v2/flows`

Request:

```json
{
  "business_id": 11,
  "name": "Order Confirmation Flow",
  "description": "Draft flow for outbound confirmation calls"
}
```

Response `201`:

```json
{
  "id": 1,
  "business_id": 11,
  "name": "Order Confirmation Flow",
  "description": "Draft flow for outbound confirmation calls",
  "status": "draft",
  "version": 1,
  "start_node_id": null,
  "published_at": null,
  "created_by": 7,
  "created_at": "ISO_DATETIME",
  "updated_at": "ISO_DATETIME"
}
```

### `POST /api/v2/flows/create-and-publish`

Creates flow + nodes + edges and publishes in one request.

Validation highlights for audio nodes:
- `play_audio` requires `config.audio_asset_id` and it must be a **positive integer**.
- `say_text` / `tts` may include optional `config.audio_asset_id`; if provided it must be a **positive integer**.
- When `audio_asset_id` is provided, it must exist under the same `business_id` and must not be deleted.
- Invalid values return validation errors such as:
  - `MISSING_PLAY_AUDIO_ASSET_ID`
  - `INVALID_AUDIO_ASSET_ID`

Request:

```json
{
  "flow": {
    "business_id": 11,
    "name": "Welcome SayText Flow",
    "description": "Create and publish in one request"
  },
  "start_node_key": "start",
  "nodes": [
    {
      "node_key": "start",
      "node_type": "say_text",
      "name": "Welcome",
      "config": {
        "text": "Hello {{customer_name}}, press 1 or 2",
        "provider": "google",
        "provider_variant": "gtts",
        "language": "en",
        "voice": "gtts:free",
        "variables": {
          "customer_name": "Tanjim"
        }
      }
    },
    {
      "node_key": "menu",
      "node_type": "gather_input",
      "name": "Menu",
      "config": {
        "max_digits": 1,
        "timeout_seconds": 5,
        "allowed_inputs": ["1", "2"]
      }
    },
    {
      "node_key": "end",
      "node_type": "hangup",
      "name": "End",
      "config": {
        "reason": "done"
      }
    }
  ],
  "edges": [
    {
      "source_node_key": "start",
      "target_node_key": "menu",
      "condition_type": "always",
      "priority": 1
    },
    {
      "source_node_key": "menu",
      "target_node_key": "end",
      "condition_type": "dtmf",
      "condition_value": "1",
      "priority": 1
    },
    {
      "source_node_key": "menu",
      "target_node_key": "end",
      "condition_type": "dtmf",
      "condition_value": "2",
      "priority": 2
    },
    {
      "source_node_key": "menu",
      "target_node_key": "end",
      "condition_type": "timeout",
      "priority": 3
    }
  ]
}
```

Response `201`:

```json
{
  "message": "Flow created and published successfully",
  "flow": {
    "id": 27,
    "business_id": 11,
    "name": "Welcome SayText Flow",
    "description": "Create and publish in one request",
    "status": "published",
    "version": 1,
    "start_node_id": 301,
    "published_at": "ISO_DATETIME",
    "created_by": 7,
    "created_at": "ISO_DATETIME",
    "updated_at": "ISO_DATETIME"
  },
  "flow_version": {
    "id": 99,
    "flow_id": 27,
    "business_id": 11,
    "version_number": 1,
    "published_by": 7,
    "published_at": "ISO_DATETIME",
    "is_active": true
  },
  "validation": {
    "valid": true
  },
  "counts": {
    "nodes": 3,
    "edges": 4
  }
}
```

Notes:
- `nodes` and `edges` arrays are dynamic size.
- Edges can reference nodes by `source_node_key`/`target_node_key` (recommended), or by IDs.
- Webhook nodes in deferred mode capture post-call intents; Redis settings:
  - `REDIS_URL`
  - `POSTCALL_INTENT_TTL_SEC` (default `86400`)
  - `POSTCALL_FLUSH_LOCK_TTL_SEC` (default `60`)

### `GET /api/v2/flows`

Query params:
- `business_id` (optional)
- `status` (optional: `draft|published|archived|disabled`)

Response `200`:

```json
{
  "items": [
    {
      "id": 1,
      "business_id": 11,
      "name": "Order Confirmation Flow",
      "description": "Draft flow for outbound confirmation calls",
      "status": "draft",
      "version": 1,
      "start_node_id": null,
      "published_at": null,
      "created_by": 7,
      "created_at": "ISO_DATETIME",
      "updated_at": "ISO_DATETIME"
    }
  ]
}
```

### `GET /api/v2/flows/:id`

Response `200`: same flow object as above.

### `PUT /api/v2/flows/:id`

Request (all fields optional):

```json
{
  "name": "Order Confirmation Flow v2",
  "description": "Updated draft description",
  "status": "draft"
}
```

Response `200`: same flow object as above.

### `DELETE /api/v2/flows/:id`

Behavior:
- Soft lifecycle delete by setting status to `archived`.

Response `200`:

```json
{
  "message": "Flow archived",
  "id": 1
}
```

### `POST /api/v2/flows/:id/validate`

Response `200`:

```json
{
  "flow_id": 1,
  "status": "draft",
  "valid": true,
  "errors": [],
  "warnings": [],
  "stats": {
    "node_count": 4,
    "edge_count": 5
  }
}
```

Validation checks include:
- start node exists and is valid
- node config sanity for runtime-critical node types
- edge source/target integrity
- orphan node detection (warning)

### `POST /api/v2/flows/:id/publish`

Response `200`:

```json
{
  "message": "Flow published successfully",
  "flow": {
    "id": 1,
    "business_id": 11,
    "name": "Order Confirmation Flow",
    "description": "Draft flow for outbound confirmation calls",
    "status": "published",
    "version": 1,
    "start_node_id": 10,
    "published_at": "ISO_DATETIME",
    "created_by": 7,
    "created_at": "ISO_DATETIME",
    "updated_at": "ISO_DATETIME"
  },
  "flow_version": {
    "id": 3,
    "flow_id": 1,
    "business_id": 11,
    "version_number": 1,
    "published_by": 7,
    "published_at": "ISO_DATETIME",
    "is_active": true
  },
  "validation": {
    "flow_id": 1,
    "valid": true,
    "errors": [],
    "warnings": []
  }
}
```

Error `422` (example):

```json
{
  "error": "Flow validation failed",
  "validation": {
    "valid": false,
    "errors": [
      {
        "code": "START_NODE_MISSING",
        "message": "Start node is not configured"
      }
    ]
  }
}
```

### `POST /api/v2/flows/:id/duplicate`

Request (optional fields):

```json
{
  "name": "Order Confirmation Flow (Copy)",
  "description": "Draft copy for experiments"
}
```

Response `201`:

```json
{
  "message": "Flow duplicated successfully",
  "source_flow_id": 1,
  "flow": {
    "id": 2,
    "business_id": 11,
    "name": "Order Confirmation Flow (Copy)",
    "description": "Draft copy for experiments",
    "status": "draft",
    "version": 1,
    "start_node_id": 31,
    "published_at": null,
    "created_by": 7,
    "created_at": "ISO_DATETIME",
    "updated_at": "ISO_DATETIME"
  },
  "stats": {
    "copied_nodes": 6,
    "copied_edges": 7
  }
}
```

### `POST /api/v2/flows/:flow_id/nodes`

Request:

```json
{
  "node_key": "welcome_node",
  "node_type": "say_text",
  "name": "Welcome Prompt",
  "config": {
    "text": "Hello {{customer_name}}, welcome to Dialyra",
    "provider": "google",
    "provider_variant": "gemini-tts",
    "language": "en",
    "voice": "gemini-tts:Kore"
  },
  "position_x": 100,
  "position_y": 200,
  "is_start": true
}
```

Response `201`:

```json
{
  "id": 10,
  "flow_id": 1,
  "business_id": 11,
  "node_key": "welcome_node",
  "node_type": "say_text",
  "name": "Welcome Prompt",
  "config": {},
  "position_x": 100.0,
  "position_y": 200.0,
  "is_start": true,
  "created_at": "ISO_DATETIME",
  "updated_at": "ISO_DATETIME"
}
```

### `GET /api/v2/flows/:flow_id/nodes`

Response `200`:

```json
{
  "items": []
}
```

### `GET /api/v2/flow-nodes/:id`

Response `200`: same flow node object as above.

### `PUT /api/v2/flow-nodes/:id`

Request (all fields optional):

```json
{
  "name": "Welcome Prompt Updated",
  "config": {
    "text": "Hello {{customer_name}}, this is an updated message"
  },
  "is_start": true
}
```

Response `200`: same flow node object as above.

### `DELETE /api/v2/flow-nodes/:id`

Response `200`:

```json
{
  "message": "Flow node deleted",
  "id": 10
}
```

### `POST /api/v2/flows/:flow_id/edges`

Request:

```json
{
  "source_node_id": 10,
  "target_node_id": 11,
  "condition_type": "always",
  "condition_value": "",
  "priority": 100,
  "label": "default path"
}
```

Response `201`:

```json
{
  "id": 21,
  "flow_id": 1,
  "business_id": 11,
  "source_node_id": 10,
  "target_node_id": 11,
  "condition_type": "always",
  "condition_value": null,
  "priority": 100,
  "label": "default path",
  "created_at": "ISO_DATETIME",
  "updated_at": "ISO_DATETIME"
}
```

### `GET /api/v2/flows/:flow_id/edges`

Response `200`:

```json
{
  "items": []
}
```

### `PUT /api/v2/flow-edges/:id`

Request (all fields optional):

```json
{
  "condition_type": "dtmf",
  "condition_value": "1",
  "priority": 10,
  "label": "press 1 path"
}
```

Response `200`: same flow edge object as above.

### `DELETE /api/v2/flow-edges/:id`

Response `200`:

```json
{
  "message": "Flow edge deleted",
  "id": 21
}
```

Notes:
- Only `draft` flows are editable for node/edge operations.
- Valid `node_type` values:
  - `play_audio`, `say_text`, `tts`, `gather_input`, `condition`, `goto`, `webhook`, `transfer_call`, `hangup`, `wait`, `set_variable`, `record_control`
- Node config constraints:
  - `play_audio.config.audio_asset_id` is required and must be a positive integer.
  - `say_text.config.audio_asset_id` / `tts.config.audio_asset_id` are optional but must be positive integers when present.
  - `webhook.config` accepted keys:
    - `enabled`, `description`, `method`, `url`, `timeout_seconds`, `auth`, `headers`, `payload`, `input_map`, `success_criteria`
  - `webhook.config.auth.type` must be one of: `none`, `header`, `basic`.
  - `webhook.config.auth.type=header` requires non-empty `webhook.config.headers` object.
  - `webhook.config.auth.type=basic` requires non-empty `webhook.config.auth.username` and `webhook.config.auth.password`.
  - `webhook.config.url` must be absolute `http://` or `https://`.
  - `webhook.config.timeout_seconds` must be integer in range `1..30`.
  - For `POST|PUT|PATCH`, `webhook.config.payload` is required.
  - `webhook.config.input_map` and `webhook.config.success_criteria` are optional objects.
  - If `success_criteria.status_codes` is provided, it must be a non-empty array of valid HTTP status codes (`100..599`).
- Valid `condition_type` values:
  - `always`, `dtmf`, `timeout`, `invalid_input`, `variable_match`, `condition_matched`, `condition_not_matched`, `webhook_success`, `webhook_failed`, `transfer_connected`, `transfer_failed`, `transfer_timeout`, `retry_exceeded`, `error`

---

## Calls (Public + Runtime)

### `POST /api/v2/call`

Request:

```json
{
  "phone": "string",
  "sip_trunk_id": 2,
  "flow_id": 10,
  "campaign_flow_id": 12,
  "campaign_id": 501
}
```

Flow selection priority:
1. `flow_id` (explicit)
2. `campaign_flow_id` (campaign-linked flow provided by caller integration)
3. `business.settings_json.default_flow_id`
4. latest active published flow for business
5. if none: warning `NO_FLOW_AVAILABLE`

Response `200`:

```json
{
  "status": "initiated",
  "phone": "string",
  "response": "string"
}
```

Error `502` example:

```json
{
  "error": "AMI host resolution failed",
  "ami_host": "string",
  "details": "string"
}
```

### `POST /api/v2/runtime/calls/originate`

Access token scope required: `calls:originate`

Request:

```json
{
  "phone": "string",
  "sip_trunk_id": 1,
  "flow_id": 42,
  "webhook_variables": {
    "customer_name": "Tanjim",
    "order_id": "ORD-1001",
    "price": "1399"
  }
}
```

`webhook_variables` rules:
- optional object
- max keys: `100`
- max serialized size: `16384` bytes
- key format: `a-zA-Z0-9_` only, max key length `64`
- values can be scalar, object, or list (JSON-serializable)
- reserved system keys are blocked (for example `call_action_id`, `call_session_id`, `business_id`, `flow_id`, `flow_version_id`, `sip_trunk_id`, `dialed_number`, `dtmf_value`, `dtmf_sequence`, `dtmf_history`, `retry_count`)
- `template_variables` is not accepted

Webhook template values:
- Runtime templates use `{{variable_name}}`.
- Exact full-placeholder values preserve objects/lists. Example: `"dtmf_history": "{{dtmf_history}}"` renders as a JSON array, not a string.
- Embedded placeholders always render as strings. Example: `"message": "Call {{call_session_id}}"`.

Common system template values:

```json
{
  "call_session_id": "{{call_session_id}}",
  "business_id": "{{business_id}}",
  "flow_id": "{{flow_id}}",
  "flow_version_id": "{{flow_version_id}}",
  "sip_trunk_id": "{{sip_trunk_id}}",
  "dialed_number": "{{dialed_number}}",
  "caller_number": "{{caller_number}}",
  "call_direction": "{{call_direction}}",
  "channel": "{{channel}}",
  "asterisk_uniqueid": "{{asterisk_uniqueid}}",
  "linkedid": "{{linkedid}}",
  "call_started_at": "{{call_started_at}}",
  "call_answered_at": "{{call_answered_at}}",
  "call_ended_at": "{{call_ended_at}}",
  "hangup_cause": "{{hangup_cause}}",
  "call_action_id": "{{call_action_id}}",
  "call_log_uuid": "{{call_log_uuid}}",
  "dtmf_value": "{{dtmf_value}}",
  "dtmf_sequence": "{{dtmf_sequence}}",
  "dtmf_history": "{{dtmf_history}}"
}
```

DTMF runtime variables:
- `dtmf_value`: latest pressed DTMF value.
- `dtmf_sequence`: ordered compact list of pressed DTMF values, for example `["2", "3", "5"]`.
- `dtmf_history`: ordered list of DTMF capture objects.
- valid DTMF, invalid input, and invalid input that becomes `retry_exceeded` are recorded.
- pure timeouts without a digit are not recorded.
- history is capped by `FLOW_DTMF_HISTORY_LIMIT` (default `50`).

`dtmf_history` item shape:

```json
{
  "node_id": 18,
  "node_key": "confirm_menu",
  "value": "5",
  "result_type": "retry_exceeded",
  "timestamp": "ISO_DATETIME"
}
```

Response `200`:

```json
{
  "status": "initiated",
  "phone": "string",
  "business_id": 1,
  "call_log_uuid": "string",
  "call_session_id": 123,
  "action_id": "string",
  "sip_trunk_id": 2,
  "sip_endpoint": "string",
  "selected_by": "auto_business",
  "selected_flow_id": 10,
  "selected_flow_version_id": 22,
  "flow_selected_by": "latest_published_flow",
  "active_calls_before": 2,
  "max_concurrent_calls": 50,
  "business_active_calls_before": 4,
  "business_max_concurrent_calls": 10,
  "system_active_calls_before": 25,
  "system_max_concurrent_calls": 100,
  "auth_type": "access_token",
  "response": "string"
}
```

### `POST /api/v2/runtime/calls/:call_id/hangup`

Access token scope required: `calls:hangup`

Request (optional body):

```json
{
  "reason": "manual_stop",
  "channel": "PJSIP/8801631596698-00000012"
}
```

Response `200` (accepted):

```json
{
  "status": "hangup_requested",
  "call_session_id": 123,
  "action_id": "0f4d9f84-3152-4a2f-9a4d-b53d24d9f7ce",
  "channel": "PJSIP/8801631596698-00000012",
  "response": "Response: Success"
}
```

Response `200` (idempotent already-ended):

```json
{
  "status": "already_ended",
  "call_session_id": 123,
  "ended_at": "2026-05-11T20:45:11.221000",
  "message": "Call already ended"
}
```

Safety notes:
- channel resolution order:
  1. request body `channel`
  2. `call_sessions.channel`
  3. live channel lookup by `call_sessions.uniqueid`
  4. early-call fallback by recent dialed number correlation
- number-fallback safety:
  - if multiple live channels match the same number, request is rejected with `409` and code `AMBIGUOUS_CHANNEL_MATCH`

### `POST /api/v2/runtime/calls/:call_id/retry`

Access token scope required: `calls:originate`

Behavior:
- only ended calls are retry-eligible
- retry-eligible statuses: `failed`, `busy`, `no_answer`, `cancelled`
- max retry attempts controlled by `CALL_RETRY_MAX_ATTEMPTS` (default `3`)
- creates a new call session and call log (does not mutate old one into active)

Response `200`:

```json
{
  "status": "retry_initiated",
  "source_call_session_id": 123,
  "retry_count": 1,
  "call_session_id": 124,
  "call_log_uuid": "string",
  "action_id": "string",
  "sip_trunk_id": 2,
  "sip_endpoint": "string",
  "selected_by": "requested",
  "response": "string"
}
```

### `GET /api/v2/runtime/calls/events`

Access token scope required: `calls:read`

Query params (optional):
- `status`: `pending|processed|failed`
- `page`: integer (default `1`)
- `page_size`: integer (default `20`, max `200`)

Response `200`:

```json
{
  "items": [
    {
      "id": 501,
      "business_id": 2,
      "call_log_id": 300,
      "call_session_id": 123,
      "event_name": "Hangup",
      "event_fingerprint": "string",
      "action_id": "string|null",
      "uniqueid": "string|null",
      "linkedid": "string|null",
      "processing_status": "processed",
      "process_attempts": 1,
      "last_error": null,
      "processed_at": "ISO_DATETIME|null",
      "created_at": "ISO_DATETIME",
      "updated_at": "ISO_DATETIME"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

### `GET /api/v2/runtime/calls/webhook-jobs`

Access token scope required: `calls:read`

Query params (optional):
- `call_session_id`: string
- `action_id`: string
- `status`: `pending|processing|retry_scheduled|completed|failed`
- `page`: integer (default `1`)
- `page_size`: integer (default `20`, max `200`)

Response `200`:

```json
{
  "items": [
    {
      "id": 1,
      "business_id": 2,
      "call_action_id": "string",
      "call_session_id": "151",
      "call_log_uuid": "string|null",
      "node_id": 77,
      "node_key": "confirm_webhook",
      "sequence_no": 1,
      "method": "POST",
      "url": "https://example.com/webhook",
      "status": "completed",
      "attempt_count": 1,
      "next_retry_at": null,
      "last_error": null,
      "last_response_code": 200,
      "last_attempt_at": "ISO_DATETIME|null",
      "completed_at": "ISO_DATETIME|null",
      "created_at": "ISO_DATETIME",
      "updated_at": "ISO_DATETIME"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

### `GET /api/v2/runtime/calls/:call_id/webhook-jobs`

Access token scope required: `calls:read`

Behavior:
- same response shape as `/runtime/calls/webhook-jobs`
- `:call_id` is matched to `call_session_id`

### `GET /api/v2/runtime/calls/webhook-worker/health`

Access token scope required: `calls:read`

Response `200`:

```json
{
  "enabled": true,
  "worker_alive": true,
  "wake_queue_depth": 0,
  "poll_sec": 1.5,
  "batch_size": 20,
  "max_attempts": 4,
  "retry_schedule_sec": "10,30,120"
}
```

### `GET /api/v2/runtime/calls/webhook-jobs/:job_id`

Access token scope required: `calls:read`

Response `200`:
- same job object shape used in `/runtime/calls/webhook-jobs` list.

### `POST /api/v2/runtime/calls/webhook-jobs/:job_id/retry`

Access token scope required: `calls:read`

Behavior:
- sets job status to `pending`
- clears previous response/error fields
- wakes webhook worker for immediate pickup

Response `200`:

```json
{
  "status": "retry_queued",
  "job": {
    "id": 1,
    "status": "pending",
    "attempt_count": 2
  }
}
```

### `POST /api/v2/runtime/calls/webhook-jobs/retry`

Access token scope required: `calls:read`

Request (all optional):

```json
{
  "status": "failed",
  "call_session_id": "151",
  "action_id": "uuid-string",
  "limit": 100
}
```

### `GET /api/v2/runtime/calls/webhook-jobs/summary`

Access token scope required: `calls:read`

Query params (optional):
- `action_id`
- `call_session_id`

Response `200`:

```json
{
  "business_id": 2,
  "action_id": "uuid-string-or-null",
  "call_session_id": "151-or-null",
  "total": 4,
  "counts": {
    "pending": 1,
    "processing": 0,
    "retry_scheduled": 1,
    "completed": 1,
    "failed": 1
  }
}
```

Behavior:
- bulk resets matching jobs to `pending`
- clears retry scheduling/error metadata
- wakes webhook worker once for immediate pickup
- `status` allowed values: `failed`, `retry_scheduled`
- `limit` max: `500`

Response `200`:

```json
{
  "status": "bulk_retry_queued",
  "retried_count": 2,
  "items": [
    { "id": 11, "status": "pending" },
    { "id": 12, "status": "pending" }
  ]
}
```


Capacity warning responses (`409`):
- `NO_TRUNK_CAPACITY`
- `NO_BUSINESS_CAPACITY`
- `NO_SYSTEM_CAPACITY`
- `NO_FLOW_AVAILABLE`

Observability + audit:
- audit events are written for originate/hangup/retry lifecycle:
  - `call.originate.validation_failed`
  - `call.originate.failed`
  - `call.originate.accepted`
  - `call.originate.ami_error`
  - `call.hangup.failed`
  - `call.hangup.accepted`
  - `call.hangup.ami_error`
  - `call.retry.failed`
  - `call.retry.accepted`
  - `call.retry.ami_error`
- metadata includes IDs (`call_session_id`, `call_log_uuid`, `action_id`), routing (`sip_trunk_id`, `selected_by`), and capacity snapshot fields where available.

### `GET /api/v2/calls`

Response `200`:

```json
{
  "items": [],
  "business_id": 1,
  "auth_type": "access_token"
}
```

### `GET /api/v2/calls/:call_id`

Response `200`:

```json
{
  "id": "string",
  "business_id": 1,
  "auth_type": "access_token",
  "status": "not_implemented"
}
```

### `GET /api/v2/calls/history`

JWT auth (`stuff` or `superuser`).

Query params:
- `business_id` (optional)
- `sip_trunk_id` (optional)
- `status` (optional)
- `number` (optional, matches from/to/dialed number)
- `date_from` (optional ISO datetime)
- `date_to` (optional ISO datetime)
- `page` (default `1`)
- `page_size` (default `20`, max `200`)
- Selector mode:
  - `action_id`
  - `call_session_id`
  - `call_id`

If selector mode is used, this endpoint returns the same single-call payload as `GET /api/v2/calls/history/:call_id`.

Response `200` without selector mode:

```json
{
  "items": [
    {
      "id": 170,
      "uuid": "string|null",
      "action_id": "102bae32-7661-4161-95e0-bd0b9d535af4|null",
      "asterisk_uniqueid": "1780833383.70|null",
      "linkedid": "string|null",
      "business_id": 1,
      "sip_trunk_id": 5,
      "actor_user_id": 2,
      "direction": "outbound|inbound|internal",
      "from_number": "1000|null",
      "to_number": "01631596697|null",
      "dialed_number": "01631596697|null",
      "status": "pending|initiated|ringing|answered|completed|failed|busy|no_answer|canceled",
      "call_status": "answer|no_answer",
      "started_at": "ISO_DATETIME|null",
      "answered_at": "ISO_DATETIME|null",
      "ended_at": "ISO_DATETIME|null",
      "duration_sec": 218,
      "billsec": 212,
      "hangup_cause": "ANSWERED|null",
      "hangup_cause_text": "ANSWERED|null",
      "billing_wallet_id": 1,
      "billing_owner_user_id": 2,
      "billing_reservation_key": "call-session-170|null",
      "billing_direction": "outbound|inbound|null",
      "billing_reserved_amount": "2.000000|null",
      "billing_charged_amount": "7.100000|null",
      "billing_released_amount": "0.000000|null",
      "billing_status": "reserved|charged|released|blocked|free|warning|null",
      "billing_error": "string|null",
      "billing_cleared": true,
      "billing_cleared_at": "ISO_DATETIME|null",
      "billing_clear_reason": "charged|released|blocked|free|warning|null",
      "billing_finalization_attempts": 1,
      "billing_last_attempt_at": "ISO_DATETIME|null",
      "created_at": "ISO_DATETIME",
      "updated_at": "ISO_DATETIME",
      "dtmf_events": [
        {
          "event_type": "dtmf.received",
          "digits": "1",
          "timestamp": "ISO_DATETIME",
          "source": "runtime",
          "node_id": 301,
          "attempt_number": 1,
          "trace_id": "string|null"
        }
      ],
      "template_values": {
        "call_session_id": "170",
        "business_id": "1",
        "flow_id": "12",
        "flow_version_id": "30",
        "sip_trunk_id": "5",
        "dialed_number": "01631596697",
        "caller_number": "1000",
        "call_direction": "outbound",
        "channel": "PJSIP/example-00000001",
        "asterisk_uniqueid": "1780833383.70",
        "linkedid": "1780833383.70",
        "call_started_at": "ISO_DATETIME|null",
        "call_answered_at": "ISO_DATETIME|null",
        "call_ended_at": "ISO_DATETIME|null",
        "hangup_cause": "ANSWERED",
        "call_action_id": "102bae32-7661-4161-95e0-bd0b9d535af4",
        "call_log_uuid": "string",
        "order_id": "ORD-1001",
        "order_action": "confirmed",
        "dtmf_value": "1",
        "dtmf_sequence": ["1"],
        "dtmf_history": []
      }
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

Notes:
- `dtmf_events` is included for each call item and is extracted from runtime DTMF lifecycle events.
- `template_values` merges stable system values, custom `webhook_variables`, and latest flow runtime variables such as `set_variable`, `dtmf_value`, `dtmf_sequence`, and `dtmf_history`.
- Internal runtime keys beginning with `__` are excluded from `template_values`.
- The list endpoint intentionally does not include full `timeline.actions`; use `GET /api/v2/calls/history/:call_id` for the full timeline.

### `GET /api/v2/calls/history/:call_id`

JWT auth (`stuff` or `superuser`).

Path behavior (legacy):
- if no selector query is provided, `:call_id` is resolved as `call_logs.id` (previous behavior).

Selector query mode (optional):
- `action_id`
- `call_session_id`
- `call_id` (query alias for call log id)

When selector query is provided on `/api/v2/calls/history`, precedence is:
1. `action_id`
2. `call_session_id`
3. `call_id` (query)

Equivalent examples:
- `/api/v2/calls/history/123` (legacy by path id)
- `/api/v2/calls/history?action_id=152824b0-013a-43f1-8d27-65cab1499ac6`
- `/api/v2/calls/history?call_session_id=162`
- `/api/v2/calls/history?call_id=123`

Response `200`:

```json
{
  "id": 170,
  "uuid": "string|null",
  "action_id": "102bae32-7661-4161-95e0-bd0b9d535af4|null",
  "asterisk_uniqueid": "1780833383.70|null",
  "linkedid": "string|null",
  "business_id": 1,
  "sip_trunk_id": 5,
  "actor_user_id": 2,
  "direction": "outbound|inbound|internal",
  "from_number": "1000|null",
  "to_number": "01631596697|null",
  "dialed_number": "01631596697|null",
  "status": "pending|initiated|ringing|answered|completed|failed|busy|no_answer|canceled",
  "call_status": "answer|no_answer",
  "started_at": "ISO_DATETIME|null",
  "answered_at": "ISO_DATETIME|null",
  "ended_at": "ISO_DATETIME|null",
  "duration_sec": 218,
  "billsec": 212,
  "hangup_cause": "ANSWERED|null",
  "hangup_cause_text": "ANSWERED|null",
  "billing_wallet_id": 1,
  "billing_owner_user_id": 2,
  "billing_reservation_key": "call-session-170|null",
  "billing_direction": "outbound|inbound|null",
  "billing_reserved_amount": "2.000000|null",
  "billing_charged_amount": "7.100000|null",
  "billing_released_amount": "0.000000|null",
  "billing_status": "reserved|charged|released|blocked|free|warning|null",
  "billing_error": "string|null",
  "billing_cleared": true,
  "billing_cleared_at": "ISO_DATETIME|null",
  "billing_clear_reason": "charged|released|blocked|free|warning|null",
  "billing_finalization_attempts": 1,
  "billing_last_attempt_at": "ISO_DATETIME|null",
  "created_at": "ISO_DATETIME",
  "updated_at": "ISO_DATETIME",
  "timeline": {
    "call_session_id": 170,
    "dtmf_events": [
      {
        "event_type": "dtmf.received",
        "digits": "1",
        "timestamp": "ISO_DATETIME",
        "source": "runtime",
        "node_id": 301,
        "attempt_number": 1,
        "trace_id": "string|null"
      }
    ],
    "actions": [
      {
        "source": "runtime|audit|ami",
        "event_type": "node.executed",
        "timestamp": "ISO_DATETIME",
        "node_id": 301,
        "processing_status": "processed|null",
        "payload": {}
      }
    ]
  },
  "template_values": {
    "call_session_id": "170",
    "business_id": "1",
    "flow_id": "12",
    "flow_version_id": "30",
    "sip_trunk_id": "5",
    "dialed_number": "01631596697",
    "caller_number": "1000",
    "call_direction": "outbound",
    "channel": "PJSIP/example-00000001",
    "asterisk_uniqueid": "1780833383.70",
    "linkedid": "1780833383.70",
    "call_started_at": "ISO_DATETIME|null",
    "call_answered_at": "ISO_DATETIME|null",
    "call_ended_at": "ISO_DATETIME|null",
    "hangup_cause": "ANSWERED",
    "call_action_id": "102bae32-7661-4161-95e0-bd0b9d535af4",
    "call_log_uuid": "string",
    "order_id": "ORD-1001",
    "order_action": "confirmed",
    "dtmf_value": "1",
    "dtmf_sequence": ["1"],
    "dtmf_history": []
  },
  "resolved_by": "action_id|call_session_id|call_log_id",
  "resolved_input": "string"
}
```

Notes:
- `call_status` is normalized for UI/reporting: `answer` when the call has answer/session/transfer evidence, otherwise `no_answer`.
- `status`, `answered_at`, `ended_at`, `duration_sec`, `billsec`, and unique IDs may be reconciled from CDR/call-session evidence during read when the original `call_logs` row is stale.
- `timeline.actions` is a merged ordered view from runtime events, audit rows, and AMI call events. Runtime items may include `node_id`; AMI items may include `processing_status`; audit items do not include either field.
- `timeline.dtmf_events` is extracted from runtime DTMF lifecycle events only.
- `template_values` has the same merge behavior as the list endpoint: system values, custom `webhook_variables`, and latest flow runtime variables with internal `__` keys excluded.
- Transfer-session details and post-call webhook job summaries are available through their dedicated endpoints; this history response only includes related transfer/webhook evidence when those events exist in `timeline.actions`.

### `GET /api/v2/calls/:call_id/events`

JWT auth (`stuff` or `superuser`).

Purpose:
- returns ordered events for one call
- unified-first read from `call_events`
- fallback to `timeline.actions` for older records

Optional query params:
- `action_id`
- `call_session_id`
- `page` (default `1`)
- `page_size` (default `50`, max `500`)

Selector resolution behavior:
- same as call history resolver
- `action_id` and `call_session_id` can override `:call_id` resolution

Response `200` (unified source):

```json
{
  "call_id": 151,
  "call_session_id": 149,
  "source": "call_events",
  "items": [
    {
      "id": 9012,
      "event_type": "dtmf.received",
      "event_source": "dtmf",
      "node_id": 275,
      "edge_id": null,
      "audio_asset_id": null,
      "dtmf_digits": "1",
      "timestamp": "2026-05-17T14:06:20.635676",
      "payload": {
        "digits": "1",
        "trace_id": "49076450-46c1-4180-9786-c4d7492e127d"
      },
      "processing_status": "processed"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 1
  }
}
```

Response `200` (fallback source):

```json
{
  "call_id": 151,
  "call_session_id": 149,
  "source": "timeline_fallback",
  "items": [],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 0
  }
}
```

### `GET /api/v2/calls/dtmf`

JWT auth (`stuff` or `superuser`).

Purpose:
- returns DTMF-focused event timeline for one call/session
- selector-based lookup for operational debugging and IVR analytics

Query params:
- `action_id` (optional)
- `call_session_id` (optional)
- `call_id` (optional, call log id)
- `page` (optional, default `1`)
- `page_size` (optional, default `50`, max `200`)

Selector requirement:
- at least one of `action_id | call_session_id | call_id` is required

Selector resolution behavior:
1. `action_id`
2. `call_session_id`
3. `call_id`

Response `200`:

```json
{
  "call_session_id": 149,
  "items": [
    {
      "id": 10931,
      "event_type": "dtmf.wait_started",
      "call_session_id": 149,
      "node_id": 275,
      "timestamp": "2026-05-17T14:06:20.213973",
      "payload": {
        "timeout_seconds": 5,
        "max_digits": 1,
        "allowed_inputs": ["1", "2"]
      }
    },
    {
      "id": 10932,
      "event_type": "dtmf.received",
      "call_session_id": 149,
      "node_id": 275,
      "timestamp": "2026-05-17T14:06:20.635676",
      "payload": {
        "digits": "1",
        "trace_id": "49076450-46c1-4180-9786-c4d7492e127d"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 2
  }
}
```

Canonical aliases (same behavior, no breaking changes):
- `GET /api/v2/call-sessions/:call_session_id`
  - equivalent to: `GET /api/v2/calls/history?call_session_id=:call_session_id`
- `GET /api/v2/call-sessions/:call_session_id/events`
  - equivalent to: `GET /api/v2/calls/:call_id/events?call_session_id=:call_session_id`
- `GET /api/v2/call-sessions/:call_session_id/dtmf`
  - equivalent to: `GET /api/v2/calls/dtmf?call_session_id=:call_session_id`

### `GET /api/v2/calls/audit`

JWT auth (`stuff` or `superuser`).

Query params:
- `call_session_id` required
- `action` optional (for example `call.retry.failed`)
- `date_from` optional ISO datetime
- `date_to` optional ISO datetime
- `page` optional (default `1`)
- `page_size` optional (default `20`, max `200`)

Response `200`:

```json
{
  "items": [
    {
      "id": 1901,
      "business_id": 11,
      "actor_user_id": 5,
      "action": "call.originate.accepted",
      "metadata": {
        "call_session_id": 333,
        "call_log_uuid": "d66a...",
        "action_id": "ami-action-id",
        "sip_trunk_id": 2
      },
      "created_at": "2026-05-11T12:31:11.002000"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

---

## TTS

### `POST /api/v2/tts/generate`

Request:

```json
{
  "business_id": 11,
  "text": "Hello {{customer_name}}, welcome to Dialyra",
  "provider": "google",
  "provider_variant": "gemini-tts",
  "language": "en",
  "voice": "gemini-tts:Kore"
}
```

Notes:
- Required fields: `business_id`, `text`
- Optional fields: `provider`, `provider_variant`, `language`, `voice`
- `provider_variant` is currently used for Google (`gemini-tts` or `gtts`)
- Sync mode returns `201`; async mode (`TTS_ASYNC_ENABLED=true`) may return `202`

Response `201` (sync completed):

```json
{
  "id": 41,
  "uuid": "5cf6f7ad-cd3a-4988-a4fd-bebf1b5c8d70",
  "business_id": 11,
  "text": "Hello Tanjim, welcome to Dialyra",
  "language": "en",
  "voice": "gemini-tts:Kore",
  "provider": "google",
  "status": "completed",
  "audio_asset_id": 123,
  "duration": null,
  "generation_time_ms": 620,
  "cache_key": "sha256...",
  "error_message": null,
  "created_by": 7,
  "created_at": "ISO_DATETIME",
  "updated_at": "ISO_DATETIME"
}
```

Response `202` (async queued):

```json
{
  "id": 42,
  "uuid": "5d52ac90-2f68-4de1-a7cb-d2f7d7f8f5fd",
  "status": "queued"
}
```

### `GET /api/v2/tts`

Query params:
- `business_id` (optional)

Response `200`:

```json
{
  "items": [
    {
      "id": 41,
      "uuid": "5cf6f7ad-cd3a-4988-a4fd-bebf1b5c8d70",
      "business_id": 11,
      "text": "Hello Tanjim, welcome to Dialyra",
      "language": "en",
      "voice": "gemini-tts:Kore",
      "provider": "google",
      "status": "completed",
      "audio_asset_id": 123,
      "duration": null,
      "generation_time_ms": 620,
      "cache_key": "sha256...",
      "error_message": null,
      "created_by": 7,
      "created_at": "ISO_DATETIME",
      "updated_at": "ISO_DATETIME"
    }
  ]
}
```

### `GET /api/v2/tts/:id`

Response `200`: same TTS request object as above.

### `DELETE /api/v2/tts/:id`

Response `200`:

```json
{
  "message": "TTS request deleted",
  "id": 41
}
```

### `GET /api/v2/tts/voices`

Query params:
- `provider` (optional)

Response `200`:

```json
{
  "provider": "google",
  "voices": [
    "gemini-tts:Kore",
    "gemini-tts:Puck",
    "gemini-tts:Charon",
    "gtts:free"
  ]
}
```

If `provider` is omitted:

```json
{
  "providers": ["elevenlabs", "google", "openai"],
  "voices": {
    "google": ["gemini-tts:Kore", "gemini-tts:Puck", "gemini-tts:Charon", "gtts:free"],
    "openai": ["alloy", "ash", "ballad"],
    "elevenlabs": ["JBFqnCBsd6RMkjVDRZzb"]
  }
}
```

### `GET /api/v2/tts/languages`

Query params:
- `provider` (optional)

Response `200`:

```json
{
  "provider": "google",
  "languages": ["en", "en-US", "bn", "hi", "es", "ar"]
}
```

### `GET /api/v2/tts/worker/health`

Response `200`:

```json
{
  "worker_alive": true,
  "queued_jobs": 0,
  "async_enabled": true
}
```

---

## Internal Runtime

### `GET /api/v2/internal/health`

Response `200`:

```json
{
  "module": "internal",
  "status": "scaffolded"
}
```

### `GET /api/v2/internal/flows/:flow_id/runtime`

Query params:
- `call_session_id` (optional)

Response `200`:

```json
{
  "business_id": 1,
  "flow_id": 1,
  "auth_type": "access_token",
  "session": {
    "id": 9,
    "call_session_id": "call_123",
    "flow_version_id": 3,
    "current_node_id": 11,
    "status": "running",
    "started_at": "ISO_DATETIME",
    "ended_at": null
  },
  "active_flow_version": {
    "id": 3,
    "version_number": 1,
    "published_at": "ISO_DATETIME"
  },
  "current_node": {
    "id": 11,
    "node_key": "welcome_node",
    "node_type": "say_text",
    "name": "Welcome Prompt",
    "config": {}
  },
  "variables": {
    "customer_name": "Tanjim"
  },
  "transfer_summary": {
    "transfer_session_id": 12,
    "trace_id": "runtime-trace-123",
    "target_type": "queue",
    "queue_id": 5,
    "selected_agent_id": 9,
    "selected_extension": "1005",
    "selected_sip_endpoint": "00011005",
    "selected_sip_username": "00011005",
    "result_type": "transfer_timeout",
    "status": "timeout",
    "failure_reason": "no_answer",
    "reason_code": "no_agent_available",
    "started_at": "ISO_DATETIME",
    "ringing_at": "ISO_DATETIME",
    "connected_at": null,
    "ended_at": "ISO_DATETIME",
    "event_seq_last": 27
  }
}
```

If no session exists yet:

```json
{
  "business_id": 1,
  "flow_id": 1,
  "auth_type": "access_token",
  "session": null,
  "active_flow_version": {
    "id": 3,
    "version_number": 1,
    "published_at": "ISO_DATETIME"
  },
  "current_node": null,
  "variables": {},
  "transfer_summary": null
}
```

### `POST /api/v2/internal/flow/resolve-next`

Request:

```json
{
  "call_session_id": "call_123",
  "flow_id": 1,
  "current_node_id": 10,
  "result_type": "dtmf",
  "value": "1",
  "use_fallback": true,
  "fallback_action": {
    "type": "hangup",
    "reason": "runtime_error_fallback"
  },
  "variables": {
    "customer_name": "Tanjim",
    "language": "en"
  }
}
```

Notes:
- If no runtime session exists for `(business_id, call_session_id)`, a session is auto-created using active published flow version.
- `flow_id` or `flow_version_id` is required for first resolve.
- For subsequent resolves, session state is reused.
- Resolver matches outgoing edges by `condition_type` and `priority`.
- If `use_fallback=true`, resolver returns a safe fallback action instead of a runtime error response.
- Canary rollout support:
  - when runtime canary is enabled and the call is excluded by canary percentage, response is `status="canary_skipped"` with `runtime_action.type="legacy_fallback"`.
  - send `force_canary=true` in request payload to force runtime execution for this call (useful for test calls).
- Optional node-type rollout:
  - if runtime node type is not enabled by rollout config, resolver returns an error (or fallback response when `use_fallback=true`).
  - explicit per-node runtime flags override allowlist configuration.

Response `200`:

```json
{
  "status": "accepted",
  "business_id": 1,
  "auth_type": "access_token",
  "call_session_id": "call_123",
  "flow_id": 1,
  "flow_version_id": 3,
  "session_id": 9,
  "created_session": false,
  "current_node_id": 10,
  "next_node_id": 11,
  "next_node_type": "say_text",
  "matched_edge_id": 21,
  "runtime_action": {
    "type": "play_audio_asset",
    "audio_asset_id": 123,
    "tts_request_id": 45,
    "source": "generated"
  },
  "observability": {
    "trace_id": "runtime-trace-123",
    "resolved_at": "ISO_DATETIME",
    "event_type": "edge.selected"
  },
  "variables": {
    "customer_name": "Tanjim",
    "language": "en"
  },
  "tts": {
    "source": "generated",
    "audio_asset_id": 123,
    "tts_request_id": 45,
    "language": "en",
    "voice": "gemini-tts:Kore",
    "provider": "google",
    "provider_variant": "gemini-tts"
  }
}
```

Possible runtime action shapes:
- `{"type":"play_audio_asset","audio_asset_id":123,...}`
- `{"type":"collect_dtmf","max_digits":1,"timeout_seconds":5,...}`
- `{"type":"transfer_call","target_type":"queue","queue_id":5,"transfer_session_id":12,"transfer_result_type":"transfer_connected","transfer_bridge":{"action":"dial","technology":"pjsip","dial_string":"PJSIP/00011005","endpoint":"00011005","timeout_seconds":20,"channel_vars":{"DIALYRA_TRANSFER_SESSION_ID":"12","DIALYRA_CALL_SESSION_ID":"101"},"cdr_userfield_append":"transfer_session_id=12"}}`
- `{"type":"hangup","reason":"flow_completed"}`
- `{"type":"noop","node_type":"condition"}`

`transfer_call` bridge contract notes:
- when `transfer_result_type=transfer_connected`, runtime includes `transfer_bridge` for FastAGI/Asterisk dial execution.
- `transfer_bridge.channel_vars` must be injected into dial channel for traceability.
- `transfer_bridge.cdr_userfield_append` should be appended to CDR `userfield` for correlation.
- transfer execution hardening:
  - can be globally toggled by `FLOW_TRANSFER_EXECUTION_ENABLED`
  - dial bridge emission can be toggled by `FLOW_TRANSFER_DIAL_BRIDGE_ENABLED`
  - dial timeout precedence can be controlled by `FLOW_TRANSFER_TIMEOUT_PRECEDENCE`:
    - `node_then_queue` (default)
    - `queue_then_node`
    - `node_only`
    - `queue_only`
  - runtime enforces business/system in-flight transfer limits before execution

Fallback response `200` when `use_fallback=true` and runtime resolve fails:

```json
{
  "status": "accepted_with_fallback",
  "business_id": 1,
  "auth_type": "access_token",
  "call_session_id": "call_123",
  "flow_id": 1,
  "flow_version_id": null,
  "runtime_action": {
    "type": "hangup",
    "reason": "runtime_error_fallback"
  },
  "fallback_used": true,
  "warning": "No matching edge found for current node/result"
}
```

Canary-skipped response `200`:

```json
{
  "status": "canary_skipped",
  "business_id": 1,
  "auth_type": "access_token",
  "call_session_id": "call_123",
  "flow_id": 1,
  "flow_version_id": null,
  "runtime_action": {
    "type": "legacy_fallback",
    "reason": "runtime_canary_skip"
  },
  "fallback_used": true,
  "warning": "Flow runtime canary gate skipped this call",
  "observability": {
    "trace_id": "runtime-trace-123",
    "resolved_at": null,
    "event_type": "canary.skip",
    "canary": {
      "enabled": true,
      "allowed": false,
      "forced": false,
      "bucket": 77,
      "percent": 25
    }
  }
}
```

### `POST /api/v2/internal/calls/:call_id/node-entered`

Request: any JSON object.

Response `200`:

```json
{
  "status": "accepted",
  "event": "node.entered",
  "session_id": 9,
  "call_id": "string",
  "business_id": 1,
  "payload": {}
}
```

### `POST /api/v2/internal/calls/:call_id/node-completed`

Request: any JSON object.

Response `200`:

```json
{
  "status": "accepted",
  "event": "node.completed",
  "session_id": 9,
  "call_id": "string",
  "business_id": 1,
  "payload": {}
}
```

### `POST /api/v2/internal/calls/:call_id/dtmf`

Request: any JSON object.

Response `200`:

```json
{
  "status": "accepted",
  "event": "dtmf.received",
  "session_id": 9,
  "call_id": "string",
  "business_id": 1,
  "payload": {}
}
```

Notes:
- This endpoint appends runtime DTMF events.
- Runtime now also writes normalized event rows to unified `call_events`.
- Related read APIs:
  - `GET /api/v2/calls/dtmf` (JWT auth, selector-based DTMF timeline)
  - `GET /api/v2/calls/:call_id/events` (JWT auth, unified event timeline)

### `POST /api/v2/internal/calls/:call_id/playback-event`

Request: any JSON object.

Response `200`:

```json
{
  "status": "accepted",
  "event": "playback.completed",
  "session_id": 9,
  "call_id": "string",
  "business_id": 1,
  "payload": {}
}
```

### `POST /api/v2/internal/calls/:call_id/runtime-error`

Request: any JSON object.

Response `200`:

```json
{
  "status": "accepted",
  "event": "runtime.error",
  "session_id": 9,
  "call_id": "string",
  "business_id": 1,
  "payload": {}
}
```

### `POST /api/v2/internal/calls/:call_id/transfer-event`

Request:

```json
{
  "event_type": "transfer_ringing|transfer_connected|transfer_failed|transfer_timeout|transfer_completed",
  "transfer_session_id": 12,
  "dial_status": "ANSWER",
  "failure_reason": null
}
```

Dial outcome mapping:
- `ANSWER` -> `transfer_connected`
- `NOANSWER` -> `transfer_timeout`
- `BUSY` -> `transfer_failed` (`failure_reason=busy`)
- `CONGESTION` -> `transfer_failed` (`failure_reason=congestion`)
- `CHANUNAVAIL` -> `transfer_failed` (`failure_reason=channel_unavailable`)
- `CANCEL` -> `transfer_failed` (`failure_reason=cancelled`)

Notes:
- provide `transfer_session_id` whenever available so runtime updates the exact transfer session row.
- if `transfer_session_id` is missing, runtime falls back to latest transfer session for that call.
- runtime persists mapped outcome into `transfer_sessions.status` and `transfer_sessions.failure_reason`.
- lifecycle behavior:
  - `transfer_ringing` sets `transfer_sessions.ringing_at`
  - `transfer_connected` sets `transfer_sessions.connected_at`
  - `transfer_completed` finalizes transfer session (`status=completed`, `ended_at`)
- flow branch compatibility:
  - use `condition_type=transfer_connected|transfer_failed|transfer_timeout`
  - do not use `condition_type=transfer_completed` (event is lifecycle/audit only)
- runtime normalizes and stores transfer timeline payload shape in `flow_runtime_events` and unified `call_events` with:
  - `transfer_session_id`
  - `transfer_type`
  - `result_type`
  - `status`
  - `queue_id`
  - `agent_id`
  - `selected_sip_endpoint`
  - `selected_extension`
  - `selected_sip_username`
  - `strategy_used`
  - `reason_code`
  - `failure_reason`
  - `trace_id`
  - `event_seq`
  - `occurred_at`
  - `ingested_at`
- contract guarantee:
  - these transfer keys are always present in persisted timeline payloads (nullable if not yet known)
  - missing ingress fields are backfilled from `transfer_sessions` and transfer selection metadata when available
  - duplicate ingress events are suppressed from transfer lifecycle transitions and emitted as `transfer.duplicate_dropped`
  - event/status mismatch emits `transfer.consistency_warning` for diagnostics

Response `200`:

```json
{
  "status": "accepted",
  "event": "transfer_connected",
  "event_id": 21,
  "trace_id": "runtime-trace-123",
  "session_id": 9,
  "call_id": "string",
  "business_id": 1,
  "payload": {}
}
```

### `POST /api/v2/internal/calls/:call_id/wait-event`

Request:

```json
{
  "event_type": "wait_completed|wait_failed",
  "duration_ms": 3000
}
```

Response `200`:

```json
{
  "status": "accepted",
  "event": "wait_completed",
  "event_id": 22,
  "trace_id": "runtime-trace-123",
  "session_id": 9,
  "call_id": "string",
  "business_id": 1,
  "payload": {}
}
```

### `POST /api/v2/internal/calls/:call_id/record-event`

Request:

```json
{
  "event_type": "recording_started|recording_stopped|recording_paused|recording_resumed|recording_failed",
  "recording_id": "rec_1"
}
```

Response `200`:

```json
{
  "status": "accepted",
  "event": "recording_started",
  "event_id": 23,
  "trace_id": "runtime-trace-123",
  "session_id": 9,
  "call_id": "string",
  "business_id": 1,
  "payload": {}
}
```

### `POST /api/v2/internal/call-events`

Request: any JSON object.

Response `200`:

```json
{
  "status": "accepted",
  "event": "call-events",
  "business_id": 1,
  "payload": {}
}
```

### `GET /api/v2/internal/audio-assets/:asset_id/playback-target`

Scope: `fastagi:runtime`

Response `200`:

```json
{
  "audio_asset_id": 123,
  "playback_target": "/data/audio-assets/11/uploads/0f8...a6",
  "format": "wav"
}
```

### `GET /api/v2/internal/call-events`

Query params:
- `status` optional: `pending|processed|failed`
- `page` optional, default `1`
- `page_size` optional, default `20`, max `200`

Response `200`:

```json
{
  "items": [
    {
      "id": 12,
      "business_id": 11,
      "call_log_id": 901,
      "call_session_id": 333,
      "event_name": "Hangup",
      "event_fingerprint": "sha256hex",
      "action_id": "ami-action-id",
      "uniqueid": "1746796458.7",
      "linkedid": "1746796458.7",
      "processing_status": "failed",
      "process_attempts": 3,
      "last_error": "Call correlation failed",
      "processed_at": null,
      "created_at": "2026-05-11T12:30:00",
      "updated_at": "2026-05-11T12:31:00"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

### `POST /api/v2/internal/call-events/:event_id/reprocess`

Reprocesses one stored event by ID using the same idempotent call-event pipeline.

Response `200`:

```json
{
  "status": "accepted",
  "event": "call-event.reprocess",
  "result": {
    "event_id": 13,
    "call_log_id": 901,
    "call_log_uuid": "d66a...",
    "call_session_id": 333,
    "event": "Hangup",
    "status": "completed"
  }
}
```

---

## SIP Trunks

The v2 SIP trunk endpoints are blocked and should be replaced with the matching `/api/v3/sip-trunks` endpoint.

Guard behavior:

- Default mode is `block`.
- Runtime override is controlled by `SIP_TRUNK_V2_ENDPOINT_GUARD_MODE`.
- Allowed guard modes are `block`, `recommend`, and `noop`.

Blocked response `410`:

```json
{
  "error": "SIP trunk v2 endpoints are blocked. Use the v3 SIP trunk endpoints.",
  "code": "SIP_TRUNK_V2_BLOCKED",
  "recommended_endpoint": "/api/v3/sip-trunks",
  "recommendation": "Use the matching /api/v3/sip-trunks endpoint. Global access writes must use version=v2 with mode=allocated.",
  "docs_url": "/api/docs"
}
```

### `POST /api/v2/sip-trunks`

Request:

```json
{
  "business_id": 1,
  "provider_profile": "bdwebs_linphone_v1",
  "name": "BDWebs Main",
  "provider_name": "BDWebs",
  "host": "202.40.176.2",
  "port": 5060,
  "username": "09617179124",
  "password": "secret",
  "from_user": "09617179124",
  "from_domain": "sip.provider.com",
  "context": "outbound",
  "status": "inactive",
  "max_concurrent_calls": 50,
  "is_active": true,
  "settings": {}
}
```

Notes:
- `provider_profile` is required. Current supported value: `bdwebs_linphone_v1`.
- Global SIP creation is v2-only: superuser can omit `business_id` to create a global trunk (`scope=global`, `business_id=null`).
- Global SIP access is controlled by `settings.global_access`; if omitted, it defaults to `{"mode":"all"}` for backward compatibility.
- Profile defaults are enforced server-side for SIP compatibility:
  - `type=registration`
  - `auth_type=userpass`
  - `transport=udp`
  - `dtmf_mode=rfc4733`
  - `context=outbound`
- `dtmf_mode` is optional. Default: `rfc4733`.
- Allowed values: `rfc4733`, `inband`, `info`, `auto`, `auto_info`, `none`.
- If an invalid `dtmf_mode` is sent, API returns validation error.
- Inbound flow routing:
  - inbound-enabled trunks should use `context=dialyra-inbound-trunk`.
  - dialplan `dialyra-inbound-trunk` sets inbound channel variables and enters FastAGI.
  - FastAGI bootstraps the inbound `call_session` and resolves the business inbound flow.
  - legacy settings like `settings.inbound_target_extension` may be kept as provider identity hints, but inbound no longer routes directly to that local extension.

Response `201`:

```json
{
  "id": 1,
  "business_id": 1,
  "provider_profile": "bdwebs_linphone_v1",
  "name": "BDWebs Main",
  "provider_name": "BDWebs",
  "type": "registration",
  "host": "202.40.176.2",
  "port": 5060,
  "username": "09617179124",
  "auth_type": "userpass",
  "transport": "udp",
  "dtmf_mode": "rfc4733",
  "from_user": "09617179124",
  "from_domain": "sip.provider.com",
  "context": "from-trunk",
  "status": "inactive",
  "max_concurrent_calls": 50,
  "is_active": true,
  "apply_status": "pending",
  "last_apply_error": null,
  "last_applied_at": null,
  "last_rollback_at": null,
  "settings": {},
  "created_at": "ISO_DATETIME",
  "updated_at": "ISO_DATETIME"
}
```

### `GET /api/v2/sip-trunks`

Query params:
- `business_id` (optional)

Response `200`:

```json
{
  "items": [
    {
      "id": 1,
      "business_id": 1,
      "provider_profile": "bdwebs_linphone_v1",
      "name": "BDWebs Main",
      "provider_name": "BDWebs",
      "type": "registration",
      "host": "202.40.176.2",
      "port": 5060,
      "username": "09617179124",
      "auth_type": "userpass",
      "transport": "udp",
      "dtmf_mode": "rfc4733",
      "from_user": "09617179124",
      "from_domain": "sip.provider.com",
      "context": "from-trunk",
      "status": "inactive",
      "max_concurrent_calls": 50,
      "is_active": true,
      "apply_status": "pending",
      "last_apply_error": null,
      "last_applied_at": null,
      "last_rollback_at": null,
      "settings": {},
      "global_access_mode": "all",
      "created_at": "ISO_DATETIME",
      "updated_at": "ISO_DATETIME"
    }
  ]
}
```

Global SIP list behavior:
- `superuser` can list global SIP trunks.
- business users can see global SIP trunks through `?business_id=...` only when:
  - the business has `allow_global_sip_fallback=true`
  - the global trunk `settings.global_access` permits that business/user.

### `GET /api/v2/sip-trunks/:trunk_id`

Response `200`: same SIP trunk object as above.

### `PUT /api/v2/sip-trunks/:trunk_id`

Request (any updatable fields):

```json
{
  "name": "BDWebs Backup",
  "host": "202.40.176.2",
  "port": 5060,
  "username": "09617170000",
  "password": "new-secret",
  "dtmf_mode": "auto_info",
  "status": "active",
  "max_concurrent_calls": 60
}
```

Notes:
- `provider_profile` is optional on update. If omitted, the backend reuses the stored profile or falls back to the default profile.

Response `200`: same SIP trunk object as above.

### `PUT /api/v2/sip-trunks/:trunk_id/global-access`

Superuser only. Applies only to trunks with `scope=global`.

Request for current/backward-compatible access:

```json
{
  "mode": "all"
}
```

Request for business allowlist:

```json
{
  "mode": "business",
  "business_ids": [1, 5]
}
```

Request for stuff-user allowlist:

```json
{
  "mode": "stuff",
  "stuff_user_ids": [2, 9]
}
```

Response `200`:

```json
{
  "sip_trunk_id": 20,
  "scope": "global",
  "global_access": {
    "mode": "business",
    "business_ids": [1, 5],
    "stuff_user_ids": []
  }
}
```

Runtime rules:
- business must still have `allow_global_sip_fallback=true`.
- `mode=all`: any fallback-enabled business can use the global trunk.
- `mode=business`: only listed businesses can use the global trunk.
- `mode=stuff`: only listed stuff users can use the global trunk.

### `DELETE /api/v2/sip-trunks/:trunk_id`

Behavior:
- soft delete (`is_active=false`, `status=inactive`)

Response `200`:

```json
{
  "message": "SIP trunk soft deleted"
}
```

### `POST /api/v2/sip-trunks/:trunk_id/test`

Response `200`:

```json
{
  "sip_trunk_id": 1,
  "status": "ok|failed",
  "checks": {
    "dns_resolve": {
      "ok": true,
      "details": "resolved"
    },
    "tcp_connect": {
      "ok": true,
      "details": "connected"
    },
    "ami_ping": {
      "ok": true,
      "details": "Response: Success"
    }
  }
}
```

### `POST /api/v2/sip-trunks/:trunk_id/reload`

Request body:

```json
{
  "enable_inbound": true
}
```

Notes:

- `enable_inbound` defaults to `false`.
- When `true`, the trunk context is set to `dialyra-inbound-trunk`.
- When `true`, the business inbound call config is created only if missing.
- Existing selected inbound flow/config is not overwritten.
- When `true`, inbound-enabled registration trunks keep a `ps_endpoint_id_ips` identify row mapped to the provider host/IP.

Response `200`:

```json
{
  "sip_trunk_id": 1,
  "status": "accepted|failed",
	  "message": "Asterisk pjsip reload executed",
	  "realtime_enabled": true,
	  "realtime": {
	    "ids": {
	      "base": "dialyra_b1_t1_trunk",
	      "endpoint": "dialyra_b1_t1_trunk_ep",
	      "aor": "dialyra_b1_t1_trunk_aor",
	      "auth": "dialyra_b1_t1_trunk_auth",
	      "registration": "dialyra_b1_t1_trunk_reg",
	      "identify": "dialyra_b1_t1_trunk_ident"
	    },
	    "rows": {
	      "ps_endpoints": true,
	      "ps_aors": true,
	      "ps_auths": true,
	      "ps_registrations": true,
	      "ps_endpoint_id_ips": true
	    },
	    "details": {
	      "endpoint": {
	        "id": "dialyra_b1_t1_trunk_ep",
	        "context": "dialyra-inbound-trunk",
	        "transport": "transport-udp",
	        "aors": "dialyra_b1_t1_trunk_aor"
	      },
	      "identify": {
	        "id": "dialyra_b1_t1_trunk_ident",
	        "endpoint": "dialyra_b1_t1_trunk_ep",
	        "match": "202.40.176.2"
	      },
	      "registration": {
	        "id": "dialyra_b1_t1_trunk_reg",
	        "server_uri": "sip:202.40.176.2:5060",
	        "client_uri": "sip:09617179124@202.40.176.2",
	        "contact_user": "09617179124"
	      }
	    }
	  },
	  "inbound": {
	    "enabled": true,
	    "context": "dialyra-inbound-trunk",
    "config_created": false,
    "config": {
      "business_id": 1,
      "enabled": true,
      "flow_id": null,
      "fallback_mode": "latest_published_flow",
      "effective_flow_id": 12,
      "ready_for_inbound": true
    }
  },
  "output": "string",
  "apply_status": "active|failed"
}
```

### `POST /api/v2/sip-trunks/:trunk_id/apply`

Response `200`:

```json
{
  "sip_trunk_id": 1,
  "status": "accepted|failed",
  "message": "Asterisk pjsip reload executed",
  "output": "string",
  "apply_status": "active|failed"
}
```

### `POST /api/v2/sip-trunks/:trunk_id/rollback`

Response `200`:

```json
{
  "sip_trunk_id": 1,
  "status": "rolled_back",
  "apply_status": "rolled_back",
  "reload_output": "string"
}
```

### `GET /api/v2/sip-trunks/:trunk_id/status`

Response `200`:

```json
{
  "sip_trunk_id": 1,
  "status": "active",
  "active_calls": 0,
  "max_concurrent_calls": 50,
  "runtime_details": "string",
  "realtime": {
    "ids": {
      "base": "dialyra_b1_t1_trunk",
      "endpoint": "dialyra_b1_t1_trunk_ep",
      "aor": "dialyra_b1_t1_trunk_aor",
      "auth": "dialyra_b1_t1_trunk_auth",
      "registration": "dialyra_b1_t1_trunk_reg",
      "identify": "dialyra_b1_t1_trunk_ident"
    },
    "rows": {
      "ps_endpoints": true,
      "ps_aors": true,
      "ps_auths": true,
      "ps_registrations": true,
      "ps_endpoint_id_ips": false
    }
  }
}
```

### `GET /api/v2/sip-trunks/realtime/health`

Access:
- `superuser`

Response `200`:

```json
{
  "ready": true,
  "missing_tables": [],
  "counts": {
    "ps_endpoints": 12,
    "ps_aors": 12,
    "ps_auths": 9,
    "ps_registrations": 9,
    "ps_endpoint_id_ips": 3
  }
}
```

## Audio Assets API

Audio assets are reusable audio files for IVR prompts, hold music, campaigns, playback nodes, TTS output, and runtime transfer behavior.

All endpoints require JWT auth.

Permission model:

- Read endpoints require `businesses.read`.
- Manage endpoints require `businesses.manage`.
- Business visibility is limited to superuser, owning `stuff` user, or active workspace membership.
- Manage access is limited to superuser, owning `stuff` user, or active workspace `owner`/`admin`.

Allowed upload values:

- `type`: `upload`, `tts`, `system`, `generated`
- `status`: `processing`, `ready`, `failed`, `deleted`
- default categories: `ivr_prompt`, `hold_music`, `campaign_audio`
- extra categories can be enabled with `AUDIO_ASSET_EXTRA_CATEGORIES`
- default extensions: `wav`, `gsm`, `ulaw`, `alaw`, `mp3`
- extension allowlist can be changed with `AUDIO_ASSET_ALLOWED_EXTENSIONS`

Audio asset response shape:

```json
{
  "id": 15,
  "uuid": "7f22f1a6-403e-4d6b-a0d0-8b01e4f7b7e9",
  "business_id": 1,
  "name": "Support Hold Music",
  "slug": "support-hold-music",
  "type": "upload",
  "category": "hold_music",
  "file_name": "7f22f1a6-403e-4d6b-a0d0-8b01e4f7b7e9.wav",
  "original_file_name": "hold.wav",
  "file_path": "/data/audio-assets/1/uploads/7f22f1a6-403e-4d6b-a0d0-8b01e4f7b7e9.wav",
  "public_path": "/audio-assets/1/uploads/7f22f1a6-403e-4d6b-a0d0-8b01e4f7b7e9.wav",
  "duration": 12.4,
  "format": "wav",
  "sample_rate": 8000,
  "channels": 1,
  "file_size": 198400,
  "source": "manual_upload",
  "language": "en",
  "voice": null,
  "status": "ready",
  "is_deleted": false,
  "deleted_at": null,
  "deleted_by": null,
  "delete_reason": null,
  "created_by": 5,
  "created_at": "2026-06-07T12:00:00",
  "updated_at": "2026-06-07T12:00:00"
}
```

### Upload Audio Asset

`POST /api/v2/audio-assets/upload`

Creates an audio asset from a multipart file upload.

Content type:

```text
multipart/form-data
```

Form fields:

- `business_id` required.
- `file` required.
- `name` optional. Defaults to uploaded file name.
- `type` optional. Defaults to `upload`.
- `category` required.
- `language` optional.
- `voice` optional.
- `source` optional. Defaults to `manual_upload`.
- `status` optional. Defaults to `ready`.

Example form:

```text
business_id=1
name=Support Hold Music
category=hold_music
type=upload
language=en
file=@hold.wav
```

Response `201`:

```json
{
  "id": 15,
  "uuid": "7f22f1a6-403e-4d6b-a0d0-8b01e4f7b7e9",
  "business_id": 1,
  "name": "Support Hold Music",
  "slug": "support-hold-music",
  "type": "upload",
  "category": "hold_music",
  "file_name": "7f22f1a6-403e-4d6b-a0d0-8b01e4f7b7e9.wav",
  "original_file_name": "hold.wav",
  "file_path": "/data/audio-assets/1/uploads/7f22f1a6-403e-4d6b-a0d0-8b01e4f7b7e9.wav",
  "public_path": "/audio-assets/1/uploads/7f22f1a6-403e-4d6b-a0d0-8b01e4f7b7e9.wav",
  "duration": 12.4,
  "format": "wav",
  "sample_rate": 8000,
  "channels": 1,
  "file_size": 198400,
  "source": "manual_upload",
  "language": "en",
  "voice": null,
  "status": "ready",
  "is_deleted": false,
  "deleted_at": null,
  "deleted_by": null,
  "delete_reason": null,
  "created_by": 5,
  "created_at": "2026-06-07T12:00:00",
  "updated_at": "2026-06-07T12:00:00"
}
```

Validation/error examples:

- `400` `{"error":"Missing required file"}`
- `400` `{"error":"Unsupported file format"}`
- `400` `{"error":"category is required"}`
- `400` `{"error":"Invalid category"}`
- `400` `{"error":"File size exceeds limit (20 MB)"}`
- `403` `{"error":"Insufficient permission for this business"}`
- `404` `{"error":"Business not found"}`
- `409` `{"error":"Audio slug already exists in this business"}`

### List Audio Assets

`GET /api/v2/audio-assets?business_id=1&include_deleted=false`

Lists audio assets visible to the authenticated user.

Query parameters:

- `business_id` optional for superuser; required if caller wants to scope to one business.
- `include_deleted` optional boolean string. Defaults to `false`.

Response `200`:

```json
{
  "items": [
    {
      "id": 15,
      "uuid": "7f22f1a6-403e-4d6b-a0d0-8b01e4f7b7e9",
      "business_id": 1,
      "name": "Support Hold Music",
      "slug": "support-hold-music",
      "type": "upload",
      "category": "hold_music",
      "file_name": "7f22f1a6-403e-4d6b-a0d0-8b01e4f7b7e9.wav",
      "original_file_name": "hold.wav",
      "file_path": "/data/audio-assets/1/uploads/7f22f1a6-403e-4d6b-a0d0-8b01e4f7b7e9.wav",
      "public_path": "/audio-assets/1/uploads/7f22f1a6-403e-4d6b-a0d0-8b01e4f7b7e9.wav",
      "duration": 12.4,
      "format": "wav",
      "sample_rate": 8000,
      "channels": 1,
      "file_size": 198400,
      "source": "manual_upload",
      "language": "en",
      "voice": null,
      "status": "ready",
      "is_deleted": false,
      "deleted_at": null,
      "deleted_by": null,
      "delete_reason": null,
      "created_by": 5,
      "created_at": "2026-06-07T12:00:00",
      "updated_at": "2026-06-07T12:00:00"
    }
  ]
}
```

### Get Audio Asset

`GET /api/v2/audio-assets/:asset_id`

Returns one audio asset record.

Response `200`:

```json
{
  "id": 15,
  "uuid": "7f22f1a6-403e-4d6b-a0d0-8b01e4f7b7e9",
  "business_id": 1,
  "name": "Support Hold Music",
  "slug": "support-hold-music",
  "type": "upload",
  "category": "hold_music",
  "file_name": "7f22f1a6-403e-4d6b-a0d0-8b01e4f7b7e9.wav",
  "original_file_name": "hold.wav",
  "file_path": "/data/audio-assets/1/uploads/7f22f1a6-403e-4d6b-a0d0-8b01e4f7b7e9.wav",
  "public_path": "/audio-assets/1/uploads/7f22f1a6-403e-4d6b-a0d0-8b01e4f7b7e9.wav",
  "duration": 12.4,
  "format": "wav",
  "sample_rate": 8000,
  "channels": 1,
  "file_size": 198400,
  "source": "manual_upload",
  "language": "en",
  "voice": null,
  "status": "ready",
  "is_deleted": false,
  "deleted_at": null,
  "deleted_by": null,
  "delete_reason": null,
  "created_by": 5,
  "created_at": "2026-06-07T12:00:00",
  "updated_at": "2026-06-07T12:00:00"
}
```

### Update Audio Asset

`PUT /api/v2/audio-assets/:asset_id`

Updates mutable metadata. This does not replace the audio file.

Request:

```json
{
  "name": "Support Hold Music V2",
  "type": "upload",
  "category": "hold_music",
  "status": "ready",
  "language": "en",
  "voice": null,
  "source": "manual_upload"
}
```

Response `200`: audio asset response shape.

Validation/error examples:

- `400` `{"error":"name cannot be empty"}`
- `400` `{"error":"Invalid audio type"}`
- `400` `{"error":"Invalid audio status"}`
- `400` `{"error":"Invalid category"}`
- `403` `{"error":"Cannot update deleted audio asset"}`
- `409` `{"error":"Audio slug already exists in this business"}`

### Stream Audio Asset

`GET /api/v2/audio-assets/:asset_id/stream`

Streams the audio file inline.

Response `200`:

```text
binary audio response
```

Response headers include a detected MIME type:

- `wav` -> `audio/wav`
- `mp3` -> `audio/mpeg`
- `ulaw`, `alaw`, `gsm` -> `audio/basic`
- unknown -> `application/octet-stream`

### Download Audio Asset

`GET /api/v2/audio-assets/:asset_id/download`

Downloads the audio file as an attachment.

Response `200`:

```text
binary audio response
```

### Delete Audio Asset

`DELETE /api/v2/audio-assets/:asset_id`

Soft-deletes the audio asset and removes the physical file when possible.

Request:

```json
{
  "delete_reason": "Uploaded wrong file"
}
```

Response `200`:

```json
{
  "message": "Audio asset soft deleted and file removed",
  "audio_asset_id": 15,
  "is_deleted": true,
  "deleted_at": "2026-06-07T12:15:00"
}
```

If the asset is already deleted, response `200`:

```json
{
  "message": "Audio asset already deleted",
  "audio_asset_id": 15,
  "is_deleted": true
}
```

### Sync Audio Asset To Asterisk

`POST /api/v2/audio-assets/:asset_id/sync-to-asterisk`

Marks the audio asset as synced for Asterisk playback metadata. The file must exist and the asset must not be deleted.

Response `200`:

```json
{
  "audio_asset_id": 15,
  "status": "synced",
  "details": {
    "status": "synced",
    "synced_at": "2026-06-07T12:20:00",
    "synced_by": 5,
    "file_path": "/data/audio-assets/1/uploads/7f22f1a6-403e-4d6b-a0d0-8b01e4f7b7e9.wav"
  }
}
```

### Test Audio Asset Playback

`POST /api/v2/audio-assets/:asset_id/test-playback`

Tests playback through AMI using `AUDIO_PLAYBACK_TEST_CHANNEL`.

Required config:

- `AUDIO_PLAYBACK_TEST_CHANNEL`
- `AUDIO_PLAYBACK_TEST_TIMEOUT_MS`

Response `200`:

```json
{
  "audio_asset_id": 15,
  "status": "ok",
  "details": {
    "tested_at": "2026-06-07T12:25:00",
    "tested_by": 5,
    "file_exists": true,
    "test_channel": "PJSIP/00011033",
    "playback_target": "/data/audio-assets/1/uploads/7f22f1a6-403e-4d6b-a0d0-8b01e4f7b7e9",
    "ami_ok": true,
    "ami_details": "Response: Success..."
  }
}
```

If AMI responds with warning/failure but the request itself is valid, response is still `200` with:

```json
{
  "audio_asset_id": 15,
  "status": "warning",
  "details": {
    "ami_ok": false,
    "ami_details": "Response: Error..."
  }
}
```

Common read/stream/download errors:

- `403` `{"error":"Insufficient permission for this business"}`
- `404` `{"error":"Audio asset not found"}`
- `404` `{"error":"Business not found"}`
- `404` `{"error":"Audio file not found"}`
- `410` `{"error":"Audio asset is deleted"}`

## Agent & Queue Admin APIs (Phase 3)

Auth:
- JWT only
- permission middleware: `businesses.read`
- business-level role enforcement in service: `owner|admin|manager`
- exception: `POST /api/v2/agents/:id/availability` also allows self-update for `agent` role when mapped by `agent.user_id`

### Endpoint Index

- `POST /api/v2/agents`
- `GET /api/v2/agents`
- `GET /api/v2/agents/:agent_id`
- `PUT /api/v2/agents/:agent_id`
- `DELETE /api/v2/agents/:agent_id`
- `POST /api/v2/agents/:agent_id/availability`
- `POST /api/v2/agents/extensions`
- `GET /api/v2/agents/extensions`
- `GET /api/v2/agents/extensions/:id`
- `PUT /api/v2/agents/extensions/:id`
- `DELETE /api/v2/agents/extensions/:id`
- `POST /api/v2/agents/extensions/:id/bind`
- `PUT /api/v2/agents/:agent_id/extensions`
- `POST /api/v2/agents/calls/originate`
- `POST /api/v2/queues`
- `GET /api/v2/queues`
- `GET /api/v2/queues/:queue_id`
- `PUT /api/v2/queues/:queue_id`
- `DELETE /api/v2/queues/:queue_id`
- `POST /api/v2/queues/:queue_id/agents`
- `DELETE /api/v2/queues/:queue_id/agents/:agent_id`
- `GET /api/v2/queues/live`
- `POST /api/v2/queues/:queue_id/routing/dry-run`
- `POST /api/v2/departments`
- `GET /api/v2/departments`
- `GET /api/v2/departments/:department_id`
- `PUT /api/v2/departments/:department_id`
- `DELETE /api/v2/departments/:department_id`
- `GET /api/v2/departments/:department_id/schedule`
- `POST /api/v2/departments/:department_id/schedule`
- `PUT /api/v2/departments/:department_id/schedule`
- `POST /api/v2/departments/:department_id/schedule/:mode`
- `GET /api/v2/departments/:department_id/agents`
- `POST /api/v2/departments/:department_id/agents`
- `PUT /api/v2/departments/:department_id/agents`
- `DELETE /api/v2/departments/:department_id/agents/:agent_id`
- `POST /api/v2/departments/:department_id/dry-run`
- `GET /api/v2/transfer-sessions`
- `GET /api/v2/transfer-sessions/:transfer_session_id`

### Agent Status Values

- `status`: `active|inactive|suspended|deleted`
- `availability_status`: `available|busy|offline|paused|after_call_work`

### Queue Values

- `strategy`: `round_robin|least_busy|priority|random|skill_based`
- `status`: `active|inactive|archived`
- `timeout_action`: `fallback_node|hangup|voicemail|callback_request|external_transfer`

### Department Values

- `strategy`: `round_robin|least_busy|priority|random|skill_based` (default: `least_busy`)
- `status`: `active|inactive|archived`

### Transfer Node Key Contract (Phase 4)

- Preferred key: `config.target_type`
- Legacy key: `config.transfer_type` (deprecated)
- `FLOW_TRANSFER_CALL_ENABLED=true` enables the `transfer_call` node contract for all supported target types.
- Supported `target_type` values: `agent|queue|department|external_number`.
- Current compatibility:
  - if only `transfer_type` is provided, backend still accepts it temporarily
  - flow validation emits warning code: `LEGACY_TRANSFER_TYPE_DEPRECATED`
- Migration guidance:
  - replace `transfer_type` with `target_type`
  - keep same value semantics

### `transfer_call` Config (Queue Mode)

Minimal config:

```json
{
  "target_type": "queue",
  "queue_id": 5,
  "transfer_connected_key": "node_success",
  "transfer_failed_key": "node_failed",
  "transfer_timeout_key": "node_timeout"
}
```

Auto-create queue mode:

```json
{
  "target_type": "queue",
  "auto_create_queue": true,
  "queue_template": {
    "name": "Support Queue",
    "strategy": "least_busy",
    "status": "active",
    "hold_music_audio_id": 12,
    "hold_tts": {
      "text": "Please stay on the line while we connect your call.",
      "provider": "google",
      "provider_variant": "gtts",
      "language": "bn",
      "voice": "gtts:free"
    },
    "max_wait_seconds": 60,
    "timeout_action": "fallback_node",
    "timeout_target_node_key": "fallback_node_key",
    "description": "Primary support queue",
    "metadata": {
      "department": "support",
      "skill_match_mode": "all_of"
    }
  },
  "timeout_seconds": 20,
  "skill_requirements": {
    "language": ["bn", "en"]
  },
  "skill_match_mode": "all_of",
  "transfer_connected_key": "node_success",
  "transfer_failed_key": "node_failed",
  "transfer_timeout_key": "node_timeout"
}
```

Validation notes:
- `queue_template.name` is required when `auto_create_queue=true` and `queue_id` is missing.
- `queue_template.name` must be unique within the business for auto-create mode (`DUPLICATE_QUEUE_TEMPLATE_NAME` on conflict).
- `queue_template.hold_music_audio_id` must belong to same business and be active.
- `queue_template.hold_tts.text` is supported for auto-create mode; backend generates a TTS audio asset and links it as `hold_music_audio_id`.
- provide either `queue_template.hold_music_audio_id` or `queue_template.hold_tts.text` (not both).
- optional `queue_template.hold_tts.provider|provider_variant|language|voice` overrides TTS settings.
- `queue_template.timeout_target_node_key` is preferred; backend resolves it to node id.
- `queue_template.timeout_action=fallback_node` requires timeout target (`timeout_target_node_key` or `timeout_target_node_id`).
- non-`fallback_node` timeout actions must not include timeout target.
- `skill_match_mode` must be `all_of|any_of`.

Edge contract for transfer outcomes:
- use `condition_type=transfer_connected`
- use `condition_type=transfer_failed`
- use `condition_type=transfer_timeout`
- avoid plain `timeout` for transfer outcome routing

Publish-time transfer branch validation:
- `transfer_connected_key` is required (blocking validation error).
- missing `transfer_failed_key` or `transfer_timeout_key` produces warnings (publish allowed).
- warnings are also emitted when `transfer_failed_key` or `transfer_timeout_key` points to the same node as `transfer_connected_key`.

Warning example (`POST /api/v2/flows/:id/validate`):

```json
{
  "flow_id": 1,
  "status": "draft",
  "valid": true,
  "errors": [],
  "warnings": [
    {
      "code": "TRANSFER_FAILED_PATH_SAME_AS_CONNECTED",
      "node_id": 27,
      "message": "transfer_failed_key points to same node as transfer_connected_key"
    },
    {
      "code": "TRANSFER_TIMEOUT_PATH_SAME_AS_CONNECTED",
      "node_id": 27,
      "message": "transfer_timeout_key points to same node as transfer_connected_key"
    }
  ]
}
```

### `transfer_call` Config (Department Mode)

Supported when `FLOW_TRANSFER_CALL_ENABLED=true`. When enabled, `transfer_call` validation accepts all supported target types, including `queue` and `department`.

```json
{
  "target_type": "department",
  "department_id": 12,
  "timeout_seconds": 20,
  "skill_requirements": {
    "language": ["bn"],
    "topic": ["support"]
  },
  "skill_match_mode": "all_of",
  "strategy": "least_busy",
  "transfer_connected_key": "node_success",
  "transfer_failed_key": "node_failed",
  "transfer_timeout_key": "node_timeout",
  "department_transfer_no_answer_key": "node_no_answer",
  "department_failure_route": {
    "department_transfer_no_agent_available": "node_no_agent",
    "department_transfer_skills_mismatch": "node_skill_fallback",
    "department_transfer_outside_schedule": "node_schedule_fallback",
    "department_transfer_capacity_full": "node_capacity_fallback",
    "department_transfer_error": "node_error_fallback"
  }
}
```

Validation notes:
- `department_id` is required and must reference an active department in the same flow business.
- `strategy` is optional and must be `least_busy|round_robin|priority|random|skill_based`.
- `skill_requirements` must be an object when provided.
- `skill_match_mode` must be `all_of|any_of`.
- `timeout_seconds` must be an integer from `1` to `180`.
- `department_transfer_*_key` values must reference existing node keys.
- `department_failure_route` must be an object whose keys are supported `department_transfer_*` outcomes and whose values reference existing node keys.
- Department-specific outcome keys are stored in node config; flow edge `condition_type` should continue to use the generic transfer conditions unless a later migration expands the DB edge constraint.

### `POST /api/v2/agents`

Request:

```json
{
  "business_id": 2,
  "user_id": 21,
  "name": "Support Agent 1",
  "email": "agent1@example.com",
  "phone": "+8801XXXXXXXXX",
  "sip_extension": "1001",
  "status": "active",
  "availability_status": "offline",
  "max_concurrent_calls": 1,
  "current_active_calls": 0,
  "skills": {"language": ["bn", "en"]},
  "metadata": {"team": "support"}
}
```

Notes:
- `user_id` is required and must reference an active `users.id` with active `agent` membership in the same business.
- `sip_extension` is optional.
- If provided, it must be numeric (`2-16` digits).
- API derives SIP login username as `<business.sip_login_prefix><sip_extension>`.
- `sip_endpoint` is system-managed and uses tenant-safe SIP identity (typically prefixed username).

Response `201`: agent object (includes derived `sip_username` when `sip_extension` is set).

### `POST /api/v2/agents/extensions`

Creates/updates a local realtime SIP extension (`ps_auths`, `ps_aors`, `ps_endpoints`) for agent phones.

Request:

```json
{
  "business_id": 2,
  "user_id": 21,
  "extension": "1001",
  "password": "1001pass",
  "display_name": "Agent 1001",
  "transport": "transport-udp",
  "context": "dialyra-ivr",
  "allow": "ulaw,alaw",
  "dtmf_mode": "rfc4733",
  "max_contacts": 1,
  "qualify_frequency": 30,
  "remove_existing": true
}
```

Notes:
- Identity model:
  - `extension` = display/business extension (human-facing, e.g. `1005`)
  - `sip_username`/`sip_endpoint` = real Asterisk SIP identity (tenant-safe, e.g. `00011005`)
- `user_id` is optional; when provided, extension is bound to that user's agent profile in the same business scope.
- `extension` must be numeric (`2-16` digits).
- `username` is system-derived and should not be sent in payload.
- Derived `username` = `<business.sip_login_prefix><extension>`.
- `sip_endpoint` in realtime provisioning uses this same derived username identity.
- Returns `agent_id` as `agents.id` and `user_id` as `users.id` when bound.

Response `201`:

```json
{
  "business_id": 2,
  "extension": "1001",
  "username": "00011001",
  "sip_endpoint": "00011001",
  "transport": "transport-udp",
  "context": "dialyra-ivr",
  "allow": "ulaw,alaw",
  "dtmf_mode": "rfc4733",
  "ids": {
    "endpoint_id": "00011001",
    "aor_id": "00011001",
    "auth_id": "00011001-auth"
  }
}
```

### `GET /api/v2/agents/extensions?business_id=2`

Response `200`:

```json
{
  "items": [
    {
      "id": 31,
      "business_id": 2,
      "agent_id": 10,
      "user_id": 21,
      "agent_name": "Support Agent 1",
      "extension": "1001",
      "sip_username": "00011001",
      "sip_endpoint": "00011001",
      "is_primary": true,
      "is_active": true,
      "created_at": "2026-05-30T12:00:00",
      "updated_at": "2026-05-30T12:05:00"
    }
  ]
}
```

### `GET /api/v2/agents/extensions/:id`

Response `200`: single extension-binding object (same schema as list item).

### `PUT /api/v2/agents/:agent_id/extensions`

Request:

```json
{
  "extension": "1005",
  "transfer": true
}
```

Notes:
- `extension` must already exist in Asterisk SIP.
- `transfer` default is `false`.
- If the extension is owned by another agent and `transfer=false`, request fails with guidance.
- If `transfer=true`, extension is safely transferred and response includes warning + revert hint.

### `POST /api/v2/agents/extensions/:id/bind`

Bind an existing extension-assignment row to another agent user.

Request:

```json
{
  "user_id": 21,
  "is_primary": true
}
```

Notes:
- `user_id` must be active, must have active `agent` membership in same business.
- If `is_primary=true`, other extensions for the target agent are set non-primary via set-based update.

### `PUT /api/v2/agents/extensions/:id`

Request:

```json
{
  "is_active": false
}
```

Notes:
- Only `is_active` is supported in this endpoint.
- Setting `is_active=false` clears primary on this row and promotes another active extension for the same agent (if any).

### `DELETE /api/v2/agents/extensions/:id`

Notes:
- Soft-deletes the mapping row (`is_active=false`, `is_deleted=true`).
- Also deprovisions endpoint/auth/aor from Asterisk realtime tables.

### `POST /api/v2/agents/calls/originate`

Originate an agent-side call where source is a local SIP extension.

Supports:
- local extension to extension (`to_type=extension`)
- local extension to PSTN via trunk (`to_type=external_number`)

Validation:
- For `to_type=extension`, `from_extension` and `to` must be different.
- Dial behavior:
  - request uses display `from_extension`/`to`
  - runtime resolves mapped `sip_endpoint` from `agent_extensions`
  - originate executes against resolved `sip_endpoint` identities (not raw display extension)

Request (extension target):

```json
{
  "business_id": 2,
  "from_extension": "1003",
  "to": "1004",
  "to_type": "extension",
  "timeout_seconds": 30
}
```

Request (external number target):

```json
{
  "business_id": 2,
  "from_extension": "1004",
  "to": "09617179124",
  "to_type": "external_number",
  "sip_trunk_id": 1,
  "timeout_seconds": 30
}
```

Response `200`:

```json
{
  "status": "initiated",
  "business_id": 2,
  "from_extension": "1003",
  "to": "1004",
  "to_type": "extension",
  "call_log_uuid": "uuid",
  "call_session_id": 201,
  "action_id": "uuid",
  "sip_trunk_id": null,
  "sip_endpoint": null,
  "timeout_seconds": 30,
  "auth_type": "jwt",
  "response": "Response: Success"
}
```

### `GET /api/v2/agents?business_id=2`

Response `200`:

```json
{
  "items": []
}
```

### `GET /api/v2/agents/:agent_id`

Response `200`: agent object.

### `PUT /api/v2/agents/:agent_id`

Request: profile-only partial fields.  
Allowed fields: `name`, `phone`, `status`, `availability_status`, `max_concurrent_calls`, `skills`.  
Not allowed here: `business_id`, `agent_id`, `user_id`, `sip_extension`, `sip_endpoint`, `extensions`, `metadata`, `current_active_calls`.

Response `200`: updated agent object.

### `DELETE /api/v2/agents/:agent_id`

Response `200`:

```json
{
  "message": "Agent deleted",
  "id": 10
}
```

### `POST /api/v2/agents/:agent_id/availability`

Request:

```json
{
  "availability_status": "available"
}
```

Response `200`: updated agent object.

### `POST /api/v2/queues`

Request:

```json
{
  "business_id": 2,
  "name": "Support Queue",
  "description": "Primary support queue",
  "strategy": "least_busy",
  "status": "active",
  "hold_music_audio_id": 12,
  "max_wait_seconds": 60,
  "timeout_action": "fallback_node",
  "timeout_target_node_id": 55,
  "metadata": {"department": "support"}
}
```

Response `201`: queue object.

Validation notes:
- `name` required, max `128` chars, unique per business (`409` on duplicate).
- `timeout_action=fallback_node` requires `timeout_target_node_id`.
- non-`fallback_node` timeout actions must not include `timeout_target_node_id`.

### `GET /api/v2/queues?business_id=2`

Response `200`:

```json
{
  "items": []
}
```

### `GET /api/v2/queues/:queue_id`

Response `200`: queue object.

### `PUT /api/v2/queues/:queue_id`

Request: partial queue fields (same as create, optional).

Response `200`: updated queue object.

Validation notes:
- Same uniqueness and timeout consistency rules as create.
- Duplicate name returns `409`.

### `DELETE /api/v2/queues/:queue_id`

Response `200`:

```json
{
  "message": "Queue deleted",
  "id": 5
}
```

### `POST /api/v2/queues/:queue_id/agents`

Request:

```json
{
  "agent_id": 10,
  "priority": 1,
  "is_active": true
}
```

Response `200`:

```json
{
  "id": 99,
  "queue_id": 5,
  "agent_id": 10,
  "priority": 1,
  "is_active": true
}
```

Validation notes:
- `priority` must be integer `>= 1`.
- `is_active` must be a real boolean (`true/false`, `1/0`, `yes/no`, `on/off` accepted).
- archived queue cannot be modified.
- agent must belong to same business and be eligible (`status` not `deleted|suspended`).
- round-robin selection uses `queue_agents.last_assigned_at` for tie-break order.

### `DELETE /api/v2/queues/:queue_id/agents/:agent_id`

Response `200`:

```json
{
  "message": "Agent removed from queue",
  "queue_id": 5,
  "queue_name": "Support Queue",
  "agent_id": 10
}
```

Validation notes:
- archived queue cannot be modified.
- target agent must exist and belong to same business as queue.

### `GET /api/v2/queues/live?business_id=2`

Response `200`:

```json
{
  "items": [
    {
      "queue_id": 5,
      "queue_name": "Support Queue",
      "description": "Primary support queue",
      "strategy": "least_busy",
      "status": "active",
      "hold_music_audio_id": 1,
      "max_wait_seconds": 60,
      "timeout_action": "fallback_node",
      "timeout_target_node_id": 22,
      "total_agents": 3,
      "available_agents": 1,
      "at_capacity_agents": 1,
      "busy_agents": 1,
      "paused_agents": 1,
      "offline_agents": 0,
      "ineligible_agents": 0,
      "active_transfer_sessions": 2,
      "routing_readiness": "ready",
      "ready_for_transfer": true,
      "reason_code": null,
      "primary_readiness_reason": null,
      "last_decision_reason": "selected",
      "last_decision_at": "2026-05-31T12:40:00",
      "last_assigned_at": "2026-05-31T12:39:58",
      "recent_selected_agents_5m": 2,
      "metadata": {
        "department": "support"
      },
      "stale_sessions_detected": false,
      "stale_sessions_count": 0,
      "event_lag_ms": 320,
      "last_consistency_warning_at": null,
      "waiting_callers": 0,
      "average_wait_seconds": null,
      "longest_wait_seconds": null
    }
  ]
}
```

Health diagnostics notes:
- `stale_sessions_detected` becomes `true` when in-flight transfer sessions exceed stale threshold (`FLOW_TRANSFER_STALE_SESSION_SEC`, default `300`).
- `event_lag_ms` is computed from latest update timestamp among in-flight transfer sessions for that queue.
- `last_consistency_warning_at` reflects latest transfer consistency warning timestamp derived from transfer session diagnostics metadata.

### `POST /api/v2/queues/:queue_id/routing/dry-run`

Manager-only dry-run target selector for debugging routing decisions without dialing.

Request (optional):

```json
{
  "trace_id": "manual-test-001",
  "skill_requirements": {
    "language": ["en"],
    "topic": ["support"]
  },
  "skill_match_mode": "all_of"
}
```

Response `200`:

```json
{
  "queue_id": 5,
  "queue_name": "Support Queue",
  "business_id": 2,
  "dry_run": true,
  "result": {
    "success": true,
    "queue_id": 5,
    "selected_agent_id": 10,
    "selected_extension": "1005",
    "selected_sip_endpoint": "00011005",
    "selected_sip_username": "00011005",
    "strategy_used": "least_busy",
    "reason_code": null,
    "decision_trace": {
      "trace_id": "manual-test-001",
      "business_id": 2,
      "queue_id": 5,
      "steps": []
    }
  }
}
```

### `POST /api/v2/departments`

Creates a business-scoped department. Departments are independent from queues and flow nodes.

Request:

```json
{
  "business_id": 2,
  "name": "Billing Department",
  "description": "Billing and payment support",
  "status": "active",
  "strategy": "least_busy",
  "metadata": {
    "default_language": "bn"
  }
}
```

Response `201`:

```json
{
  "id": 3,
  "business_id": 2,
  "name": "Billing Department",
  "description": "Billing and payment support",
  "status": "active",
  "strategy": "least_busy",
  "metadata": {
    "default_language": "bn"
  },
  "created_at": "2026-06-04T10:00:00",
  "updated_at": "2026-06-04T10:00:00"
}
```

Validation notes:
- `name` required, max `128` chars, unique per business (`409` on duplicate).
- `strategy` defaults to `least_busy`.
- department stores no flow node ids.

### `GET /api/v2/departments?business_id=2`

Response `200`:

```json
{
  "items": [
    {
      "id": 3,
      "business_id": 2,
      "name": "Billing Department",
      "description": "Billing and payment support",
      "status": "active",
      "strategy": "least_busy",
      "metadata": {
        "default_language": "bn"
      },
      "created_at": "2026-06-04T10:00:00",
      "updated_at": "2026-06-04T10:00:00"
    }
  ]
}
```

### `GET /api/v2/departments/:department_id`

Response `200`:

```json
{
  "id": 3,
  "business_id": 2,
  "name": "Billing Department",
  "description": "Billing and payment support",
  "status": "active",
  "strategy": "least_busy",
  "availability_status": "open",
  "availability": {
    "availability_status": "open",
    "availability_mode": "always_open",
    "is_open_now": true,
    "schedule_reason": "schedule_not_configured",
    "timezone": "Asia/Dhaka",
    "is_configured": false
  },
  "metadata": {
    "default_language": "bn"
  },
  "created_at": "2026-06-04T10:00:00",
  "updated_at": "2026-06-04T10:00:00"
}
```

Availability notes:
- `availability_status` is resolved by the reusable department availability engine.
- `availability_status` allowed values: `open|closed`.
- `availability_mode` allowed values: `always_open|scheduled|closed`.
- The engine checks `availability_mode` first.
- If `availability_mode=always_open`, status is `open`.
- If `availability_mode=closed`, status is `closed`.
- If `availability_mode=scheduled`, status is determined using current date/time, configured timezone, weekly hours, and holiday overrides.
- If no `department_schedule_windows` row exists, the department resolves as `availability_mode=always_open` and `availability_status=open`.

### `PUT /api/v2/departments/:department_id`

Request: partial department fields.  
Allowed fields: `name`, `description`, `status`, `strategy`, `metadata`.

Response `200`: updated department object.

Validation notes:
- Duplicate name in same business returns `409`.
- `status`: `active|inactive|archived`.
- `strategy`: `round_robin|least_busy|priority|random|skill_based`.

### `DELETE /api/v2/departments/:department_id`

Response `200`:

```json
{
  "message": "Department deleted",
  "id": 3
}
```

Validation notes:
- Department with assigned agents cannot be deleted (`409`).
- Department schedule row is removed with the department.

### `GET /api/v2/departments/:department_id/agents`

Lists agent mappings for a department.

Response `200`:

```json
{
  "items": [
    {
      "id": 42,
      "business_id": 2,
      "department_id": 3,
      "agent_id": 10,
      "priority": 1,
      "is_active": true,
      "last_assigned_at": null,
      "created_at": "2026-06-04T10:05:00",
      "updated_at": "2026-06-04T10:05:00"
    }
  ]
}
```

Notes:
- Results are ordered by `priority ASC`, then mapping `id ASC`.
- This endpoint returns department membership/mapping data only; it does not modify agent profile fields.

### `POST /api/v2/departments/:department_id/agents`

Adds or updates an agent mapping for a department.

Request:

```json
{
  "agent_id": 10,
  "priority": 1,
  "is_active": true
}
```

Response `200`:

```json
{
  "id": 42,
  "business_id": 2,
  "department_id": 3,
  "agent_id": 10,
  "priority": 1,
  "is_active": true,
  "last_assigned_at": null,
  "created_at": "2026-06-04T10:05:00",
  "updated_at": "2026-06-04T10:05:00"
}
```

Validation notes:
- `priority` must be integer `>= 1`.
- `is_active` must be boolean.
- archived department cannot be modified.
- agent must belong to same business and be eligible (`status` not `deleted|suspended`).

### `PUT /api/v2/departments/:department_id/agents`

Updates mapping fields only. This does not modify the agent profile.

Request:

```json
{
  "agent_id": 10,
  "priority": 2,
  "is_active": false
}
```

Response `200`: department-agent mapping object.

### `DELETE /api/v2/departments/:department_id/agents/:agent_id`

Response `200`:

```json
{
  "message": "Agent removed from department",
  "department_id": 3,
  "department_name": "Billing Department",
  "agent_id": 10
}
```

### `GET /api/v2/departments/:department_id/schedule`

Returns the single schedule row for a department. If no row exists, the API returns the default open policy.

Response `200` when no configured row exists:

```json
{
  "id": null,
  "business_id": 2,
  "department_id": 3,
  "availability_mode": "always_open",
  "availability_status": "open",
  "timezone": "Asia/Dhaka",
  "weekly_hours": {},
  "holiday_overrides": [],
  "is_active": true,
  "metadata": null,
  "is_configured": false,
  "is_open_now": true,
  "schedule_reason": "schedule_not_configured",
  "created_at": null,
  "updated_at": null
}
```

### `POST /api/v2/departments/:department_id/schedule`

Creates the single schedule row for a department.

Request:

```json
{
  "availability_mode": "scheduled",
  "timezone": "Asia/Dhaka",
  "weekly_hours": {
    "mon": [{"open": "09:00", "close": "18:00"}],
    "tue": [{"open": "09:00", "close": "18:00"}],
    "wed": [{"open": "09:00", "close": "18:00"}],
    "thu": [{"open": "09:00", "close": "18:00"}],
    "fri": [{"open": "09:00", "close": "17:00"}],
    "sat": [],
    "sun": []
  },
  "holiday_overrides": [
    {"date": "2026-06-16", "mode": "closed"},
    {
      "date": "2026-06-17",
      "mode": "custom",
      "windows": [{"open": "10:00", "close": "14:00"}]
    }
  ],
  "is_active": true,
  "metadata": {
    "note": "Business hours schedule"
  }
}
```

Response `201`:

```json
{
  "id": 9,
  "business_id": 2,
  "department_id": 3,
  "availability_mode": "scheduled",
  "availability_status": "open",
  "timezone": "Asia/Dhaka",
  "weekly_hours": {
    "mon": [{"open": "09:00", "close": "18:00"}],
    "tue": [{"open": "09:00", "close": "18:00"}],
    "wed": [{"open": "09:00", "close": "18:00"}],
    "thu": [{"open": "09:00", "close": "18:00"}],
    "fri": [{"open": "09:00", "close": "17:00"}],
    "sat": [],
    "sun": []
  },
  "holiday_overrides": [
    {"date": "2026-06-16", "mode": "closed"},
    {
      "date": "2026-06-17",
      "mode": "custom",
      "windows": [{"open": "10:00", "close": "14:00"}]
    }
  ],
  "is_active": true,
  "metadata": {
    "note": "Business hours schedule"
  },
  "is_configured": true,
  "is_open_now": true,
  "schedule_reason": "weekly_open",
  "created_at": "2026-06-04T10:10:00",
  "updated_at": "2026-06-04T10:10:00"
}
```

Validation notes:
- Only one schedule row is allowed per department (`409` if already exists).
- `availability_mode`: `always_open|scheduled|closed`.
- `timezone` must be a valid IANA timezone when `availability_mode=scheduled`.
- `weekly_hours` uses day keys `mon|tue|wed|thu|fri|sat|sun`.
- time windows use `HH:MM` 24-hour format and `open` must be earlier than `close`.
- `holiday_overrides.mode`: `closed|custom`.
- Schedule date fields are normalized to canonical `YYYY-MM-DD`; for example `2026-06-4` is stored and evaluated as `2026-06-04`.

### `PUT /api/v2/departments/:department_id/schedule`

Updates the existing schedule row.

Request: partial or full schedule fields.

Response `200`: updated schedule object.

Validation notes:
- Returns `404` if the schedule row does not exist.
- Use `POST` first to create the department schedule.

### `POST /api/v2/departments/:department_id/schedule/:mode`

Toggles only the department schedule `availability_mode`.

Path params:
- `mode`: `always_open|scheduled|closed`

Behavior:
- Changes only `availability_mode`.
- Preserves existing `weekly_hours`, `holiday_overrides`, `timezone`, and `metadata`.
- If no schedule row exists, creates one with the requested mode, business timezone, empty `weekly_hours`, and empty `holiday_overrides`.
- If mode is `scheduled` and no windows are configured, live `availability_status` will usually be `closed` until schedule windows are added.

Response `200`: updated schedule object.

### `POST /api/v2/departments/:department_id/dry-run`

Dry-run department target selector for debugging routing decisions without dialing.

Request (optional):

```json
{
  "trace_id": "department-dry-run-001",
  "skill_requirements": {
    "language": ["bn"],
    "topic": ["support"]
  },
  "skill_match_mode": "all_of",
  "strategy": "round_robin"
}
```

Response `200`:

```json
{
  "department_id": 3,
  "department_name": "Billing Department",
  "business_id": 2,
  "dry_run": true,
  "result": {
    "success": true,
    "target_type": "department",
    "department_id": 3,
    "department_name": "Billing Department",
    "selected_agent_id": 10,
    "selected_extension": "1005",
    "selected_sip_endpoint": "00011005",
    "selected_sip_username": "00011005",
    "strategy_used": "round_robin",
    "strategy_source": "flow_override",
    "reason_code": null,
    "department_outcome": null,
    "availability": {
      "availability_status": "open",
      "availability_mode": "scheduled",
      "is_open_now": true,
      "schedule_reason": "weekly_open",
      "timezone": "Asia/Dhaka",
      "is_configured": true
    },
    "decision_trace": {
      "trace_id": "department-dry-run-001",
      "business_id": 2,
      "department_id": 3,
      "target_type": "department",
      "steps": []
    }
  }
}
```

Failure response still returns `200` for deterministic selector outcomes, with `result.success=false`, `reason_code`, and `department_outcome`.

Possible deterministic `department_outcome` values:
- `department_transfer_no_agent_available`
- `department_transfer_skills_mismatch`
- `department_transfer_outside_schedule`
- `department_transfer_capacity_full`
- `department_transfer_error`

Validation notes:
- `skill_requirements` must be an object when provided.
- `skill_match_mode`: `all_of|any_of`.
- optional `strategy`: `least_busy|round_robin|priority|random|skill_based`.
- Department-agent `priority` is lower-number-wins and is always applied after eligibility filters. The selector keeps only the highest-priority eligible bucket, then runs the selected strategy inside that bucket.
- If an agent stores flat skills like `["support", "bn", "en"]`, each `skill_requirements` field is matched against that flat set.
- Example for flat skills: `{"language": ["bn"], "topic": ["support"]}` matches `["support", "bn", "en"]` with `all_of`.
- Dry-run may update department-agent `last_assigned_at` as part of selector tie-break state, matching queue dry-run behavior.

### `GET /api/v2/departments/:department_id/live`

Returns a department operational readiness snapshot.

Response `200`:

```json
{
  "department_id": 3,
  "department_name": "Service Department",
  "business_id": 1,
  "description": "Service routing group",
  "strategy": "least_busy",
  "status": "active",
  "availability": {
    "availability_mode": "scheduled",
    "availability_status": "open",
    "is_configured": true,
    "is_open_now": true,
    "schedule_reason": "weekly_window",
    "timezone": "Asia/Dhaka"
  },
  "total_agents": 2,
  "available_agents": 1,
  "at_capacity_agents": 0,
  "busy_agents": 1,
  "paused_agents": 0,
  "offline_agents": 0,
  "ineligible_agents": 0,
  "agents_without_active_extension": 0,
  "active_transfer_sessions": 1,
  "routing_readiness": "ready",
  "ready_for_transfer": true,
  "reason_code": null,
  "primary_readiness_reason": null,
  "last_assigned_at": "2026-06-04T15:30:00",
  "recent_selected_agents_5m": 1,
  "stale_sessions_detected": false,
  "stale_sessions_count": 0,
  "event_lag_ms": 1200,
  "last_consistency_warning_at": null
}
```

Readiness values include:

- `ready`
- `inactive_department`
- `outside_schedule`
- `no_mapped_agents`
- `no_capacity`
- `all_paused`
- `no_active_extension`
- `no_available_agent`

### `GET /api/v2/transfer-sessions?business_id=2&status=connected&page=1&page_size=20`

Optional filters:

- `queue_id`: return queue transfer sessions for one queue.
- `department_id`: return department transfer sessions for one department.
- `agent_id`: return transfer sessions selected for one agent.
- `call_session_id`: return transfer sessions for one call session.

Query params:
- `business_id` optional (defaults to first manageable business)
- `status` optional (`initiated|queued|ringing|connected|failed|timeout|abandoned|completed`)
- `queue_id` optional
- `agent_id` optional
- `call_session_id` optional
- `date_from` optional ISO datetime (filters `created_at >= date_from`)
- `date_to` optional ISO datetime (filters `created_at <= date_to`)
- `sort_by` optional (`id|created_at|started_at|ringing_at|connected_at|ended_at|status`), default `created_at`
- `sort_order` optional (`asc|desc`), default `desc`
- `page` optional, default `1`
- `page_size` optional, default `20`, max `200`

Response `200`:

```json
{
  "items": [
    {
      "id": 12,
      "business_id": 2,
      "call_session_id": 101,
      "flow_runtime_session_id": 44,
      "source_node_id": 88,
      "transfer_type": "queue",
      "queue_id": 5,
      "agent_id": 10,
      "external_number": null,
      "status": "connected",
      "started_at": "2026-05-31T12:39:58",
      "ringing_at": "2026-05-31T12:39:59",
      "connected_at": "2026-05-31T12:40:02",
      "ended_at": null,
      "failure_reason": null,
      "metadata": {
        "trace_id": "runtime-trace-123"
      },
      "created_at": "2026-05-31T12:39:58",
      "updated_at": "2026-05-31T12:40:02"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 1,
    "pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

### `GET /api/v2/transfer-sessions/:transfer_session_id`

Response `200`:

```json
{
  "id": 12,
  "business_id": 2,
  "call_session_id": 101,
  "flow_runtime_session_id": 44,
  "source_node_id": 88,
  "transfer_type": "queue",
  "queue_id": 5,
  "agent_id": 10,
  "external_number": null,
  "status": "connected",
  "started_at": "2026-05-31T12:39:58",
  "ringing_at": "2026-05-31T12:39:59",
  "connected_at": "2026-05-31T12:40:02",
  "ended_at": null,
  "failure_reason": null,
  "metadata": {
    "trace_id": "runtime-trace-123"
  },
  "detail": {
    "selection_context": {
      "queue_id": 5,
      "strategy_used": "least_busy",
      "selected_agent_id": 10,
      "selected_extension": "1005",
      "selected_sip_endpoint": "00011005",
      "selected_sip_username": "00011005",
      "reason_code": null,
      "decision_trace": {}
    },
    "bridge": {
      "action": "dial",
      "technology": "pjsip",
      "dial_string": "PJSIP/00011005",
      "endpoint": "00011005",
      "timeout_seconds": 20,
      "hold_music_audio_id": 1,
      "channel_vars": {
        "DIALYRA_TRANSFER_SESSION_ID": "12"
      },
      "cdr_userfield_append": "transfer_session_id=12"
    },
    "outcome_diagnostics": {
      "event_type": "transfer_connected",
      "dial_status": "ANSWER",
      "normalized_reason": "answered",
      "hangup_cause": "16",
      "dialed_peer_name": "PJSIP/00011005-0000001a",
      "dialed_peer_number": "00011005",
      "answered_time_ms": "10500",
      "dialed_time_ms": "10900",
      "applied_status": "connected",
      "failure_reason": null,
      "applied_at": "2026-05-31T12:40:02"
    },
    "outcome_guard": {
      "last_outcome_apply_state": "applied",
      "last_outcome_event_type": "transfer_connected",
      "last_outcome_applied_at": "2026-05-31T12:40:02",
      "duplicate_event_count": 0,
      "last_duplicate_event_key": null,
      "last_rejected_outcome": null
    },
    "timeout_resolution": {
      "dial_timeout_seconds": 20,
      "dial_timeout_source": "transfer_call.timeout_seconds",
      "dial_timeout_context": {
        "node_timeout": 20,
        "queue_timeout": 60,
        "precedence": "node_then_queue"
      }
    }
  },
  "created_at": "2026-05-31T12:39:58",
  "updated_at": "2026-05-31T12:40:02"
}
```

## Billing API

Billing protects paid call execution with stuff-user credit wallets. All endpoints in this section are superuser-only.

The billing system is controlled by feature flags. When enforcement is disabled, billing can reserve/finalize and log warnings without blocking calls. When enforcement is enabled, insufficient credit or required Redis failures can block call origination/inbound flow execution before paid work starts.

Key `.env` flags:

- `BILLING_ENABLED`: master billing switch.
- `BILLING_ENFORCEMENT_ENABLED`: when true, required billing failures can block calls.
- `BILLING_INBOUND_ENABLED`: enables inbound billing reservations/finalization.
- `BILLING_OUTBOUND_ENABLED`: enables outbound billing reservations/finalization.
- `BILLING_REDIS_REQUIRED`: when true, Redis must be available for enforced billing reservations.
- `BILLING_OUTBOUND_RESERVE_SECONDS`: outbound pre-call reserve window.
- `BILLING_INBOUND_RESERVE_SECONDS`: inbound pre-call reserve window.
- `BILLING_ZERO_BILL_RELEASE_GRACE_SECONDS`: safety window before an ambiguous zero-bill reserved call can be released without CDR truth. Explicit `failed`, `busy`, `no_answer`, or cancelled calls can release immediately.
- `BILLING_USER_VIEW_ALLOWED_ROLES`: comma-separated platform or workspace roles allowed to view their own billing credits/history.
- `BILLING_OBSERVABILITY_ENABLED`: emits billing counters/logs.

### Billing Rollout Stages

`GET /api/v2/billing/rollout`

Returns the effective billing rollout stage and active flag values.

Response `200`:

```json
{
  "rollout": {
    "stage": "reserve_without_blocking",
    "flags": {
      "billing_enabled": true,
      "enforcement_enabled": false,
      "redis_required": true,
      "inbound_enabled": false,
      "outbound_enabled": true,
      "observability_enabled": true
    },
    "reserve_seconds": {
      "outbound": 60,
      "inbound": 60
    },
    "defaults": {
      "unit": "BDT",
      "outbound_cost_per_minute": "0.000000",
      "inbound_cost_per_minute": "0.000000",
      "outbound_billing_increment_seconds": 1,
      "inbound_billing_increment_seconds": 1,
      "outbound_minimum_charge_seconds": 0,
      "inbound_minimum_charge_seconds": 0
    }
  }
}
```

Rollout stage meanings:

- `disabled`: `BILLING_ENABLED=false`; billing does not affect calls.
- `observe_only`: billing master flag is on, but inbound and outbound billing paths are off.
- `reserve_without_blocking`: inbound and/or outbound reservation is active, but failed reservations do not block calls.
- `enforced`: failed required billing checks can block calls.

### Billing Observability

`GET /api/v2/billing/observability`

Returns in-process billing counters useful during rollout and incident checks.

Response `200`:

```json
{
  "observability": {
    "status": "ok",
    "counters": {
      "billing.reserve.success": 4,
      "billing.finalize.success": 4,
      "billing.reserve.insufficient_credit": 1
    },
    "generated_at": "2026-06-07T10:20:30.123456"
  }
}
```

### Billing Clearance Health

`GET /api/v2/billing/clearance/health`

Returns asynchronous billing clearance worker and queue status. Superuser only.

Response `200`:

```json
{
  "enabled": true,
  "worker_alive": true,
  "queue": "billing:clearance",
  "consumer_group": "billing-clearance-workers",
  "worker_concurrency": 20,
  "batch_size": 100,
  "stream_length": 42,
  "processing_jobs": 2,
  "failed_jobs": 0,
  "last_processed_at": "2026-07-26T12:00:00",
  "last_result": {
    "status": "finalized",
    "call_session_id": 170,
    "final_status": "charged"
  },
  "last_error": null
}
```

### Billing Rate Plans

`GET /api/v2/billing/rate-plan`

Backward-compatible alias for `GET /api/v2/billing/rate-plans/global`.

`PUT /api/v2/billing/rate-plan`

Backward-compatible alias for `PUT /api/v2/billing/rate-plans/global`.

New rate-plan APIs support three rate types:

- `custom`: per stuff user, highest priority during diagnostics.
- `own`: system plan used when an Own SIP context applies.
- `global`: system fallback plan and current runtime billing source.

Current runtime reservation/finalization still uses the active `global` plan. The `custom` and `own` APIs configure the future resolver and diagnostics without changing existing call billing behavior.

`GET /api/v2/billing/rate-plans`

Lists singleton system plans (`own`, `global`).

Response `200`:

```json
{
  "items": [
    {
      "id": 2,
      "rate_type": "own",
      "stuff_user_id": null,
      "scope": "global",
      "business_id": null,
      "outbound_cost_per_minute": "0.800000",
      "inbound_cost_per_minute": "0.300000",
      "outbound_billing_increment_seconds": 1,
      "inbound_billing_increment_seconds": 1,
      "outbound_minimum_charge_seconds": 0,
      "inbound_minimum_charge_seconds": 0,
      "is_active": true,
      "source": "database"
    }
  ]
}
```

`GET /api/v2/billing/rate-plans/:rate_type`

Returns one system plan. `rate_type` must be `own` or `global`.

`PUT /api/v2/billing/rate-plans/:rate_type`

Creates or updates one system plan. `rate_type` must be `own` or `global`.

Request:

```json
{
  "outbound_cost_per_minute": "1.00",
  "inbound_cost_per_minute": "0.50",
  "outbound_billing_increment_seconds": 1,
  "inbound_billing_increment_seconds": 1,
  "outbound_minimum_charge_seconds": 0,
  "inbound_minimum_charge_seconds": 0
}
```

Validation:

- `rate_type` is path-only and must not be sent in the JSON body.
- Cost fields must be non-negative decimals.
- Billing increment fields must be positive integers.
- Minimum charge fields must be non-negative integers.

Response `200`:

```json
{
  "rate_type": "global",
  "scope": "global",
  "business_id": null,
  "created": false,
  "rate_plan": {
    "id": 1,
    "rate_type": "global",
    "stuff_user_id": null,
    "scope": "global",
    "business_id": null,
    "outbound_cost_per_minute": "1.000000",
    "inbound_cost_per_minute": "0.500000",
    "outbound_billing_increment_seconds": 1,
    "inbound_billing_increment_seconds": 1,
    "outbound_minimum_charge_seconds": 0,
    "inbound_minimum_charge_seconds": 0,
    "is_active": true,
    "created_by_user_id": 1,
    "created_at": "2026-06-07T10:00:00",
    "updated_at": "2026-06-07T10:10:00",
    "source": "database"
  }
}
```

`GET /api/v2/billing/rate-plans/custom?stuff_user_id=2&is_active=true&limit=50`


Lists custom per-user rate plans.

`GET /api/v2/billing/rate-plans/custom/:stuff_user_id`

Returns the active custom rate plan for a stuff user.

`PUT /api/v2/billing/rate-plans/custom/:stuff_user_id`

Creates, updates, or reactivates the custom rate plan for a stuff user. The request body uses the same money/increment fields as system plans.

`DELETE /api/v2/billing/rate-plans/custom/:stuff_user_id`

Soft-deactivates the active custom rate plan.

`GET /api/v2/billing/rate-plans/effective/:stuff_user_id?sip_scope=business`

Runs the central resolver and returns the diagnostic effective plan. Priority is active custom, then active own when Own SIP context applies, then active global.

Response `200`:

```json
{
  "stuff_user_id": 2,
  "resolved_rate_type": "custom",
  "sip_context": {
    "sip_scope": "business"
  },
  "rate_plan": {
    "id": 4,
    "rate_plan_id": 4,
    "rate_type": "custom",
    "stuff_user_id": 2,
    "outbound_cost_per_minute": "1.250000",
    "inbound_cost_per_minute": "0.750000",
    "outbound_billing_increment_seconds": 1,
    "inbound_billing_increment_seconds": 1,
    "outbound_minimum_charge_seconds": 0,
    "inbound_minimum_charge_seconds": 0,
    "is_active": true,
    "source": "database"
  }
}
```

### Wallet Lookup

`GET /api/v2/billing/wallets?stuff_user_id=5`

Returns a stuff user's credit wallet and Redis cache snapshot.

Response `200` when wallet exists:

```json
{
  "wallet": {
    "id": 10,
    "stuff_user_id": 5,
    "stuff_user": {
      "id": 5,
      "email": "agent@example.com",
      "full_name": "Agent User",
      "status": "active"
    },
    "balance": "120.000000",
    "unit": "BDT",
    "is_active": true,
    "redis_version": 3,
    "last_synced_at": "2026-06-07T10:20:00",
    "created_at": "2026-06-07T09:00:00",
    "updated_at": "2026-06-07T10:20:00"
  },
  "redis_cache": {
    "status": "hit",
    "balance": "120.000000",
    "unit": "BDT",
    "version": 3
  },
  "wallet_exists": true,
  "ready_for_billing": true,
  "reason_code": null
}
```

### My Billing Credits

`GET /api/v2/billing/me/credits`

Returns the authenticated user's visible billing account and available credit from the database source of truth.

Access is controlled by `BILLING_USER_VIEW_ALLOWED_ROLES`. The allowlist checks both the user's platform role, for example `stuff`, and the user's primary workspace membership role, for example `owner`, `admin`, `manager`, `agent`, or `viewer`.

Resolution rules:

- If the user belongs to a business, the endpoint returns the business owner's stuff wallet, which is the same wallet used by call billing.
- If the user has no business membership and is a `stuff` user, the endpoint returns that user's own wallet.
- Superuser management endpoints remain separate; this endpoint is for the caller's visible billing account.

Response `200`:

```json
{
  "billing_account": {
    "source": "primary_business_owner",
    "business_id": 1,
    "stuff_user_id": 2,
    "wallet_id": 1,
    "wallet_exists": true,
    "wallet_active": true,
    "ready_for_billing": true,
    "reason_code": null
  },
  "unit": "BDT",
  "balance": "14.100000",
  "available_credit": "12.100000"
}
```

### My Billing History

`GET /api/v2/billing/me/history?limit=50&direction=outbound&billing_status=charged`

Returns call-session billing history for the authenticated user's visible billing account. History is generated from `call_sessions`, not ledger rows, so it reflects call-level billing outcomes. The summary uses database wallet/reservation state, not Redis.

Query parameters:

- `limit`: optional, default `50`, max `200`.
- `direction`: optional `inbound` or `outbound`.
- `billing_status`: optional status filter such as `reserved`, `charged`, `released`, `free`, `blocked`, `warning`, or `reconciled`.

Response `200`:

```json
{
  "billing_account": {
    "source": "primary_business_owner",
    "business_id": 1,
    "stuff_user_id": 2,
    "wallet_id": 1,
    "ready_for_billing": true,
    "reason_code": null
  },
  "summary": {
    "unit": "BDT",
    "balance": "14.100000",
    "available_credit": "14.100000"
  },
  "items": [
    {
      "call_session_id": 157,
      "business_id": 1,
      "direction": "outbound",
      "call_status": "completed",
      "billing_status": "charged",
      "billing_cleared": true,
      "billing_cleared_at": "2026-06-07T06:49:34.349642",
      "billing_clear_reason": "charged",
      "billing_finalization_attempts": 1,
      "billing_last_attempt_at": "2026-06-07T06:49:34.330102",
      "billing_reservation_key": "call-session-157",
      "billing_reserved_amount": "2.000000",
      "billing_charged_amount": "3.266667",
      "billing_released_amount": "0.000000",
      "billing_error": null,
      "dialed_number": "01631596697",
      "started_at": "2026-06-07T06:43:44",
      "answered_at": "2026-06-07T06:43:50",
      "ended_at": "2026-06-07T06:45:28",
      "duration_seconds": 103,
      "bill_seconds": 98,
      "ami_action_id": "4a030438-00b3-4454-8b60-fee1fc1ceff2",
      "uniqueid": "1780814624.30",
      "linkedid": null,
      "created_at": "2026-06-07T06:43:44.746496",
      "updated_at": "2026-06-07T06:49:34.349642"
    }
  ],
  "count": 1,
  "limit": 50,
  "filters": {
    "billing_status": "charged",
    "direction": "outbound"
  }
}
```

Response `200` when wallet does not exist:

```json
{
  "wallet": null,
  "stuff_user": {
    "id": 5,
    "email": "agent@example.com",
    "full_name": "Agent User",
    "status": "active"
  },
  "wallet_exists": false,
  "ready_for_billing": false,
  "reason_code": "wallet_missing"
}
```

### Add Wallet Credit

`POST /api/v2/billing/wallets/:stuff_user_id/credits`

Adds credit to a stuff user's wallet. If the wallet does not exist, it is created. Use `idempotency_key` to safely retry top-ups.

Request:

```json
{
  "amount": "100.00",
  "unit": "BDT",
  "note": "Manual top-up for pilot rollout",
  "idempotency_key": "topup-2026-06-07-0001"
}
```

Response `201`:

```json
{
  "wallet": {
    "id": 10,
    "stuff_user_id": 5,
    "balance": "220.000000",
    "unit": "BDT",
    "is_active": true,
    "redis_version": 4,
    "last_synced_at": "2026-06-07T10:25:00",
    "created_at": "2026-06-07T09:00:00",
    "updated_at": "2026-06-07T10:25:00",
    "stuff_user": {
      "id": 5,
      "email": "agent@example.com",
      "full_name": "Agent User",
      "status": "active"
    }
  },
  "ledger": {
    "id": 44,
    "wallet_id": 10,
    "stuff_user_id": 5,
    "event_type": "credit_added",
    "amount": "100.000000",
    "balance_before": "120.000000",
    "balance_after": "220.000000",
    "reference_type": "manual_top_up",
    "reference_id": "10",
    "idempotency_key": "topup-2026-06-07-0001",
    "note": "Manual top-up for pilot rollout",
    "created_by_user_id": 1,
    "created_at": "2026-06-07T10:25:00"
  },
  "wallet_created": false,
  "idempotent_replay": false,
  "redis_sync": {
    "status": "synced",
    "stuff_user_id": 5,
    "wallet_id": 10
  }
}
```

If an existing `idempotency_key` is reused, the backend returns `409` and does not add credit. Reuse is rejected even when `amount` and `unit` are the same, so each successful top-up must use a new key:

```json
{
  "error": "idempotency_key_conflict",
  "message": "This idempotency_key has already been used. Use a different idempotency_key for a new top-up."
}
```

### Debit Wallet Credit

`POST /api/v2/billing/wallets/:stuff_user_id/debits`

Subtracts credit from a stuff user's wallet. The wallet must already exist, be active, match the requested unit, and have enough available balance after reserved call credit is considered. Use a new `idempotency_key` for every debit request.

Request:

```json
{
  "amount": "23.00",
  "unit": "BDT",
  "note": "Manual balance correction",
  "idempotency_key": "debit-500"
}
```

Response `201`:

```json
{
  "wallet": {
    "id": 10,
    "stuff_user_id": 5,
    "balance": "197.000000",
    "unit": "BDT",
    "is_active": true,
    "redis_version": 5,
    "last_synced_at": "2026-06-07T10:30:00",
    "created_at": "2026-06-07T09:00:00",
    "updated_at": "2026-06-07T10:30:00",
    "stuff_user": {
      "id": 5,
      "email": "agent@example.com",
      "full_name": "Agent User",
      "status": "active"
    }
  },
  "ledger": {
    "id": 45,
    "wallet_id": 10,
    "stuff_user_id": 5,
    "event_type": "balance_debited",
    "amount": "-23.000000",
    "balance_before": "220.000000",
    "balance_after": "197.000000",
    "reference_type": "manual_debit",
    "reference_id": "10",
    "idempotency_key": "debit-500",
    "note": "Manual balance correction",
    "created_by_user_id": 1,
    "created_at": "2026-06-07T10:30:00"
  },
  "wallet_created": false,
  "idempotent_replay": false,
  "redis_sync": {
    "status": "synced",
    "stuff_user_id": 5,
    "wallet_id": 10
  }
}
```

If an existing `idempotency_key` is reused, the backend returns `409` and does not debit credit:

```json
{
  "error": "idempotency_key_conflict",
  "message": "This idempotency_key has already been used. Use a different idempotency_key for a new debit."
}
```

If the wallet does not have enough available balance after reserved call credit, the backend returns `409`:

```json
{
  "error": "insufficient_wallet_available_balance"
}
```

### Wallet Ledger

`GET /api/v2/billing/wallets/:stuff_user_id/ledger?limit=50`

Returns recent wallet ledger events. `limit` defaults to `50` and is capped at `200`.

Response `200`:

```json
{
  "wallet": {
    "id": 10,
    "stuff_user_id": 5,
    "balance": "220.000000",
    "unit": "BDT",
    "is_active": true,
    "redis_version": 4,
    "last_synced_at": "2026-06-07T10:25:00",
    "created_at": "2026-06-07T09:00:00",
    "updated_at": "2026-06-07T10:25:00",
    "stuff_user": {
      "id": 5,
      "email": "agent@example.com",
      "full_name": "Agent User",
      "status": "active"
    }
  },
  "redis_cache": {
    "status": "hit",
    "balance": "220.000000",
    "unit": "BDT",
    "version": 4
  },
  "items": [
    {
      "id": 44,
      "wallet_id": 10,
      "stuff_user_id": 5,
      "event_type": "credit_added",
      "amount": "100.000000",
      "balance_before": "120.000000",
      "balance_after": "220.000000",
      "reference_type": "manual_top_up",
      "reference_id": "10",
      "idempotency_key": "topup-2026-06-07-0001",
      "note": "Manual top-up for pilot rollout",
      "created_by_user_id": 1,
      "created_at": "2026-06-07T10:25:00"
    }
  ],
  "count": 1,
  "wallet_exists": true,
  "limit": 50
}
```

### Wallet Cache Sync

`POST /api/v2/billing/wallets/:stuff_user_id/sync`

Bootstraps or refreshes one stuff user's wallet cache in Redis from the database.

Response `200`:

```json
{
  "redis_sync": {
    "status": "synced",
    "stuff_user_id": 5,
    "wallet_id": 10
  }
}
```

`POST /api/v2/billing/wallets/sync?limit=500`

Bootstraps or refreshes multiple wallet caches in Redis from the database. `limit` defaults to `500`.

Response `200`:

```json
{
  "redis_sync": {
    "status": "completed",
    "limit": 500,
    "synced": 12,
    "failed": 0,
    "items": []
  }
}
```

### Billing Blocked Call Response

When `BILLING_ENABLED=true`, the relevant direction flag is enabled, and `BILLING_ENFORCEMENT_ENABLED=true`, a call can be blocked before execution if the stuff user does not have enough credit or billing cannot safely reserve credit.

Example blocked response:

```json
{
  "error": "insufficient credits",
  "code": "INSUFFICIENT_CREDIT",
  "reason_code": "insufficient_credit",
  "required_credit": "1.000000",
  "available_credit": "0.250000",
  "billing_owner_user_id": 5
}
```

### Billing Fields On Call Records

Call history and reconciliation can include billing metadata such as:

- `billing_wallet_id`: wallet used for the call.
- `billing_owner_user_id`: stuff user whose credit paid for the call.
- `billing_rate_plan_id`: rate plan used for the calculation.
- `billing_reservation_key`: Redis reservation key for the active call.
- `billing_reserved_amount`: amount reserved before call execution.
- `billing_final_amount`: final charged amount after duration reconciliation.
- `billing_refunded_amount`: unused reserved amount returned after finalization.
- `billing_status`: current billing lifecycle status.
- `billing_reason_code`: billing failure, warning, or reconciliation reason.
- `billing_cleared`: durable settlement flag. `false` means reconciliation must still settle the wallet/reservation for this call.
- `billing_cleared_at`: timestamp when wallet settlement was completed.
- `billing_clear_reason`: final settlement reason such as `charged`, `released`, `free`, `blocked`, or `warning`.
- `billing_finalization_attempts`: number of settlement attempts made for this call.
- `billing_last_attempt_at`: timestamp of the latest settlement attempt.

### Billing Settlement Lifecycle

Billing uses `billing_cleared` as the durable source of truth for whether a call has been financially settled.

At reservation time:

- `billing_status` is set to `reserved`.
- `billing_cleared` is set to `false`.
- Redis tracks wallet `balance`, aggregate `reserved`, and the call reservation hash.

At call completion or reconciliation:

- If the call is explicit `failed`, `busy`, `no_answer`, or cancelled, the reservation is released, the final charge is `0`, and `billing_cleared=true`.
- If the call is answered/completed, final charge is calculated from CDR `billsec` or trusted connected duration, unused reservation is released, and `billing_cleared=true`.
- If final charge is higher than the initial reservation, the extra amount can be charged only when the unreserved wallet balance is still sufficient.
- If the call looks completed but trusted duration/CDR truth is missing, reconciliation leaves `billing_cleared=false` so the call can be retried later.
- `billing_cleared=true` means wallet settlement is complete. It does not mean the call was answered.

Reconciliation should fetch terminal calls where:

```text
billing_cleared = false
AND billing_reservation_key IS NOT NULL
AND call status is terminal
```

This avoids the old inconsistency where Redis reservations could be released while call rows still looked unsettled, or call rows could remain stuck because `billing_status` alone no longer described the full settlement state.

## Business Event Webhooks

Business event webhooks are configured once per business and receive selected call/runtime/billing events by `POST` request. They are independent from flow-node webhook nodes.

Delivery is asynchronous: Flask records the event, creates webhook delivery rows, and a background worker sends HTTP requests. FastAGI does not send webhook HTTP requests directly.

Supported event types:

```json
[
  "call.completed",
  "call.failed",
  "node.executed",
  "dtmf.received",
  "transfer.connected",
  "transfer.failed",
  "transfer.timeout",
  "transfer.completed",
  "wait.completed",
  "wait.failed",
  "recording.started",
  "recording.stopped",
  "recording.failed",
  "runtime.error",
  "billing.charged",
  "billing.blocked",
  "billing.released"
]
```

Use `"*"` in `event_types` to subscribe to all supported events.

### HMAC Signature

Each delivery includes these headers:

```http
X-Dialyra-Event-Id: <event id>
X-Dialyra-Event-Type: <event type>
X-Dialyra-Timestamp: <UTC ISO timestamp>
X-Dialyra-Signature: sha256=<hex digest>
```

Signature base string:

```text
<X-Dialyra-Timestamp>.<raw JSON request body>
```

Signature algorithm:

```text
HMAC-SHA256(secret, signature_base_string)
```

The webhook URL may be `http://` or `https://`. Endpoint security and TLS choice are business responsibility; Dialyra provides HMAC authenticity. By default, Dialyra blocks private/internal destination addresses during delivery to protect platform infrastructure. For local development only, `BUSINESS_WEBHOOK_ALLOW_PRIVATE_URLS=true` can allow private targets.

### Delivery Payload

```json
{
  "event": {
    "id": "a1b2c3...",
    "type": "dtmf.received",
    "occurred_at": "2026-07-06T10:00:00.123456",
    "source": "dialyra",
    "source_event_id": 123,
    "source_event_table": "call_events"
  },
  "business": {
    "id": 1
  },
  "call": {
    "call_session_id": 170,
    "call_log_id": 170,
    "business_id": 1,
    "direction": "outbound",
    "status": "completed",
    "from_number": "1000",
    "to_number": "01631596697",
    "dialed_number": "01631596697",
    "flow_id": 12,
    "flow_version_id": 18,
    "sip_trunk_id": 5,
    "started_at": "2026-07-06T09:59:10",
    "answered_at": "2026-07-06T09:59:20",
    "ended_at": "2026-07-06T10:00:00",
    "duration_seconds": 50,
    "bill_seconds": 40,
    "uniqueid": "1780833383.70",
    "linkedid": null,
    "ami_action_id": "102bae32-7661-4161-95e0-bd0b9d535af4"
  },
  "template_values": {
    "call_session_id": "170",
    "business_id": "1",
    "flow_id": "12",
    "dialed_number": "01631596697",
    "dtmf_value": "1",
    "dtmf_sequence": ["1"],
    "dtmf_history": [
      {
        "digits": "1",
        "node_key": "main_menu",
        "node_id": 44,
        "timestamp": "2026-07-06T09:59:30.123456"
      }
    ],
    "order_id": "ORD-1001",
    "order_action": "confirmed"
  },
  "template_values_source": "redis",
  "data": {
    "digits": "1",
    "trace_id": "manual-test-001"
  }
}
```

`template_values` is resolved from runtime Redis first, then DB fallback. It contains system call values, custom values supplied during call initiation, and flow runtime values such as `set_variable`, `dtmf_value`, `dtmf_sequence`, and `dtmf_history`. Internal runtime keys beginning with `__` are excluded.

### `GET /api/v2/business-webhooks?business_id=1`

Lists webhook subscriptions for a business.

Response `200`:

```json
{
  "items": [
    {
      "id": 1,
      "business_id": 1,
      "name": "CRM webhook",
      "url": "https://crm.example.com/dialyra/events",
      "event_types": ["call.completed", "dtmf.received"],
      "status": "active",
      "timeout_seconds": 5,
      "secret_configured": true,
      "last_delivery_at": null,
      "last_success_at": null,
      "last_failure_at": null,
      "last_error": null,
      "created_by_user_id": 2,
      "created_at": "2026-07-06T10:00:00",
      "updated_at": "2026-07-06T10:00:00"
    }
  ],
  "supported_event_types": ["call.completed", "call.failed"]
}
```

### `POST /api/v2/business-webhooks`

Creates a webhook subscription.

Request:

```json
{
  "business_id": 1,
  "name": "CRM webhook",
  "url": "https://crm.example.com/dialyra/events",
  "event_types": ["call.completed", "dtmf.received", "transfer.connected"],
  "timeout_seconds": 5
}
```

Optional:

```json
{
  "secret": "business-provided-hmac-secret"
}
```

If `secret` is omitted, backend generates one and returns it only once in the create response.

Response `201`:

```json
{
  "id": 1,
  "business_id": 1,
  "name": "CRM webhook",
  "url": "https://crm.example.com/dialyra/events",
  "event_types": ["call.completed", "dtmf.received", "transfer.connected"],
  "status": "active",
  "timeout_seconds": 5,
  "secret_configured": true,
  "secret": "generated-secret-returned-once",
  "secret_returned_once": true
}
```

### `GET /api/v2/business-webhooks/:id`

Returns one webhook subscription. The secret is never returned from this endpoint.

### `PUT /api/v2/business-webhooks/:id`

Updates name, URL, event types, timeout, status, or secret.

Request:

```json
{
  "name": "CRM webhook v2",
  "url": "https://crm.example.com/dialyra/events",
  "event_types": ["*"],
  "timeout_seconds": 10,
  "status": "active"
}
```

Rotate generated secret:

```json
{
  "rotate_secret": true
}
```

Set provided secret:

```json
{
  "secret": "new-business-secret"
}
```

When the secret changes, it is returned once in the response.

### `DELETE /api/v2/business-webhooks/:id`

Disables the subscription by setting `status=disabled`.

### `POST /api/v2/business-webhooks/:id/pause`

Sets `status=paused`. Paused subscriptions do not receive new deliveries.

### `POST /api/v2/business-webhooks/:id/resume`

Sets `status=active`.

### `POST /api/v2/business-webhooks/:id/test`

Queues one test delivery for this subscription.

Response `202`:

```json
{
  "status": "queued",
  "subscription_id": 1,
  "enqueued": 1,
  "event_type": "call.completed"
}
```

### `GET /api/v2/business-webhooks/:id/deliveries`

Lists delivery attempts for a subscription. Requires business manage permission because delivery payloads can include call and billing data.

Query params:

- `page`
- `page_size`

Each delivery item returns the raw outbound `payload` plus convenience fields:

```json
{
  "template_values": {
    "call_session_id": "170",
    "order_action": "confirmed"
  },
  "template_values_source": "redis"
}
```

### `GET /api/v2/business-webhooks/deliveries/:delivery_id`

Returns one delivery with payload, latest response code/body, latest error, attempt count, and timestamps. Requires business manage permission. The stored HMAC signature is not returned. Receivers should verify signatures from HTTP delivery headers.

### `POST /api/v2/business-webhooks/deliveries/:delivery_id/retry`

Resets a delivery to `pending` and wakes the delivery worker. Requires business manage permission.

### `GET /api/v2/business-webhooks/health`

Returns business webhook worker status.
