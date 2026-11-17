# AuthZ Policy Matrix v2

Status: current implementation baseline  
Scope: Defines the authorization model currently enforced by `api/v2`.

## 1. Core Principles

1. `users.role` is account type only: `superuser | stuff | general`.
2. `stuff` is not a general permission bypass, but selected ownership workflows still treat the `stuff` owner as the business operator.
3. Business-level authorization is resolved from `workspace_memberships` + policy checks, with legacy owner checks in modules that still support owner-managed businesses.
4. `general` users may belong to multiple businesses with different membership roles.

---

## 2. Data Ownership Rules

1. `users` stores identity and account type only.
2. `businesses` stores business data only.
3. `workspace_memberships` stores business access:
   - `user_id`
   - `business_id`
   - `role` (`owner | admin | manager | agent | viewer`)
   - `status` (`active | inactive | suspended`)
   - timestamps/audit fields

---

## 3. Actor Context Resolution

For each protected request:

1. Authenticate actor (`JWT`).
2. If actor is `superuser`, allow global scope (still validate target business/resource existence).
3. If endpoint is business-scoped:
   - resolve target business from path/payload/resource
   - resolve active membership `(actor_user_id, business_id)`
   - deny if membership missing/inactive
4. Compute effective permissions from membership role policy.

Additional v2 rules:
- `stuff` is an account type. It is not an automatic permission bypass.
- A `stuff` user can create their first business without an existing workspace membership.
- In business/SIP services, `stuff` users who own the target business can manage or view that business even when the route decorator also uses membership-based permission checks.

---

## 4. Membership Role -> Permissions Matrix

### Common permission keys

- `businesses.read`
- `businesses.manage`
- `settings.manage`
- `members.manage`
- `users.create`
- `access_tokens.manage`

### Matrix

| Membership Role | businesses.read | businesses.manage | settings.manage | members.manage | users.create | access_tokens.manage |
|---|---|---|---|---|---|---|
| `owner` | yes | yes | yes | yes | yes | yes |
| `admin` | yes | yes | yes | yes | yes | yes |
| `manager` | yes | no | no | no | no | no |
| `agent` | yes | no | no | no | no | no |
| `viewer` | yes | no | no | no | no | no |

Notes:
- This reflects `app/middleware/permissions_v2.py`.
- Route services may apply stricter checks after the middleware permission passes.
- `superuser` is platform override, not membership-based.

---

## 5. User Creation Policy Matrix

| Actor | Can create `superuser` | Can create `stuff` | Can create `general` | Business scope |
|---|---|---|---|---|
| `superuser` | yes | yes | yes | any business |
| `stuff` | no | no | yes | owned business only |
| `general(admin)` | no | no | no | n/a |
| `general(manager|agent|viewer)` | no | no | no | n/a |

Required rule:
- `general` creation must include business assignment via membership flow.

---

## 6. Endpoint -> Required Policy Matrix

### Auth endpoints

| Endpoint | Actor Requirement | Business/Membership Requirement |
|---|---|---|
| `POST /api/v2/auth/bootstrap-superuser` | public + bootstrap secret | none |
| `POST /api/v2/auth/login` | public | none |
| `POST /api/v2/auth/refresh` | public (valid refresh token) | none |
| `POST /api/v2/auth/logout` | public (valid refresh token) | none |
| `GET /api/v2/auth/me` | authenticated | business context for non-superuser |
| `POST /api/v2/auth/users` | per creation matrix above | enforce scope rules |

### Business endpoints

| Endpoint | Required Permission | Scope Check |
|---|---|---|
| `GET /api/v2/businesses` | authenticated | return businesses actor can access |
| `POST /api/v2/businesses` | policy `businesses.manage` | platform/scope |
| `GET /api/v2/businesses/:id` | `businesses.read` | actor has active membership in `:id` or is superuser |
| `PUT /api/v2/businesses/:id` | `businesses.manage` | same as above |
| `DELETE /api/v2/businesses/:id` | `businesses.manage` | same as above |
| `GET /api/v2/businesses/:id/settings` | `businesses.read` | membership/superuser |
| `PUT /api/v2/businesses/:id/settings` | `settings.manage` | membership/superuser |
| `POST /api/v2/businesses/:id/global-sip/enable` | superuser | target business must exist and be active |
| `POST /api/v2/businesses/:id/global-sip/disable` | superuser | target business must exist and be active |

### Membership endpoints

| Endpoint | Required Permission | Scope Check |
|---|---|---|
| `POST /api/v2/businesses/:id/members` | `members.manage` | membership/superuser |
| `GET /api/v2/businesses/:id/members` | `businesses.read` | membership/superuser |
| `PUT /api/v2/businesses/:id/members/:member_id` | `members.manage` | membership/superuser |
| `DELETE /api/v2/businesses/:id/members/:member_id` | `members.manage` | membership/superuser |

### Access token endpoints

| Endpoint group | Required Permission | Scope Check |
|---|---|---|
| `/api/v2/access-tokens/*` | `access_tokens.manage` | per target business membership/scope or superuser |

---

## 7. Validation Contracts

### `POST /api/v2/auth/users`

Required:
- `full_name`, `email`, `password`, `role`

Conditional:
- if `role = superuser`: no `business_id` required
- if `role = stuff`: superuser only; no membership is auto-created
- if `role = general`: must include business assignment (direct or immediate membership create)

Forbidden:
- non-superuser creating `superuser`
- non-superuser creating `stuff`
- cross-business general creation without proper permission

---

## 8. Safety and Non-Break Rollout Rules

1. Introduce new resolver in dual-read mode first.
2. Log authorization decision diffs between old and new logic.
3. Switch writes to new model before strict read enforcement.
4. Enable strict enforcement behind feature flag.
5. Remove legacy branches only after stable monitoring window.

---

## 9. Finalized Decisions

1. `stuff` can create only `general` users; default scope is own business. Cross-business operations require explicit policy-permitted scope.
2. `manager` keeps business read access by default; member listing uses `businesses.read`.
3. Business deletion remains policy-restricted (practically superuser/strictly controlled in rollout).
4. `general(admin)` is not allowed to create users through `/api/v2/auth/users` in the current implementation.
