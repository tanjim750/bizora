# SIP Trunk Realtime Mapping (v2)

Status: implementation contract  
Scope: mapping from Dialyra `sip_trunks` records to Asterisk realtime `ps_*` tables.

## 1. Naming Convention

For trunk:
- `business_id = B`
- `id = T`
- `name = N`

Base key:
- `dialyra_b{B}_t{T}_{slug(N)}`

Derived IDs:
- endpoint: `{base}_ep`
- aor: `{base}_aor`
- auth: `{base}_auth`
- registration: `{base}_reg`
- identify: `{base}_ident`

These IDs must be deterministic and stable for idempotent upserts.

---

## 2. Endpoint Mapping (`ps_endpoints`)

Row key:
- `id = endpoint_id`

Fields:
- `id` <- endpoint id
- `transport` <- trunk `transport` (fallback system default)
- `aors` <- aor id
- `auth` / `outbound_auth` <- auth id when the trunk needs an auth object
- `context` <- trunk `context` (fallback `outbound`)
- `from_user` <- trunk `from_user` (fallback `username`)
- `from_domain` <- trunk `from_domain` (fallback `host`)
- `disallow` = `all`
- `allow` = `ulaw,alaw`
- `direct_media` = `no`
- `rtp_symmetric` = `yes`
- `force_rport` = `yes`
- `rewrite_contact` = `yes`

---

## 3. AOR Mapping (`ps_aors`)

Row key:
- `id = aor_id`

Fields:
- `id` <- aor id
- `contact` <- `sip:{host}:{port}`
- optional defaults:
  - `max_contacts = 1`
  - `remove_existing = yes`
  - `qualify_frequency` from settings/default

---

## 4. Auth Mapping (`ps_auths`)

Row key:
- `id = auth_id`

Fields:
- `id` <- auth id
- `auth_type` = `userpass`
- `username` <- trunk `username`
- `password` <- decrypted `password_encrypted`

Auth rows are required for:
- `registration` trunks
- `ip` trunks when `auth_type=userpass` and `username` is present

No `ps_auths` row is written for unauthenticated `ip` trunks.

---

## 5. Registration Mapping (`ps_registrations`) for `registration` only

Row key:
- `id = registration_id`

Fields:
- `id` <- registration id
- `outbound_auth` <- auth id
- `server_uri` <- `sip:{host}:{port}`
- `client_uri` <- `sip:{username}@{host}`
- `contact_user` <- `from_user` fallback `username`
- `transport` <- trunk `transport`
- `retry_interval` <- setting/default
- `forbidden_retry_interval` <- setting/default
- `expiration` <- setting/default

No `ps_registrations` row for `ip` trunks.

---

## 6. Identify Mapping (`ps_endpoint_id_ips`)

Row key:
- `id = identify_id`

Fields:
- `id` <- identify id
- `endpoint` <- endpoint id
- `match` <- trunk `host`

Identify rows are required for:
- `ip` trunks
- `registration` trunks when inbound is enabled with context `dialyra-inbound-trunk`

For outbound-only `registration` trunks, the identify row is removed.

---

## 7. Type Rules

### `type = registration`
Required rows:
- endpoint + aor + auth + registration

Required fields:
- `username`, `password`, `host`, `port`

### `type = ip`
Required rows:
- endpoint + aor + identify

Required fields:
- `host`, `port`

Conditional rows:
- auth only when `auth_type=userpass` and `username` is present

Forbidden rows:
- registration

---

## 8. Apply and Delete Behavior

On apply:
1. Validate trunk payload.
2. Upsert all required realtime rows for type.
3. Remove obsolete rows that no longer apply for the type.
4. Trigger `pjsip reload`.
5. Verify runtime state.

On soft-delete/inactivate:
1. Remove (or disable) trunk-linked realtime rows.
2. Trigger `pjsip reload`.

Cleanup selector:
- rows with IDs prefixed by `dialyra_b{B}_t{T}_`.

---

## 9. Security Rules

1. Keep trunk secret encrypted at rest in Dialyra DB.
2. Decrypt only inside sync worker before writing to `ps_auths`.
3. Never return password in API responses.
4. Mask sensitive values in logs/audit metadata.

---

## 10. Sync Metadata

`sip_trunks` should track:
- `apply_status` (`pending|applying|active|failed|rolled_back`)
- `last_apply_error`
- `last_applied_at`
- `last_rollback_at`
- optional revision/hash for drift detection

---

## 11. Verification Commands

After apply:
1. `pjsip show endpoint <endpoint_id>`
2. `pjsip show registrations` (registration trunks)
3. Reachability/OPTIONS check
4. Status endpoint normalization
