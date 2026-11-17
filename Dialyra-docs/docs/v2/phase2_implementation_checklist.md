# Phase 2 Implementation Checklist (AuthZ v2)

Status: Execution checklist (post-Phase 1 sign-off)  
Goal: Implement AuthZ v2 with zero breakage and clear rollback points.

## 1. Guardrails Before Any Logic Change

1. Add feature flag in config:
   - `AUTHZ_V2_ENABLED = false` (default)
2. Keep existing behavior as fallback while v2 is introduced.
3. Add audit log event key for decision mismatches:
   - `authz.decision_diff`

Files:
- `server/app/config.py`
- `server/app/middleware/permissions.py`
- `server/app/services/audit_service.py` (if event helper constraints exist)

Acceptance:
- App starts with no behavior change.
- Flag can be toggled by env.

---

## 2. Role Constants and Canonical Vocabulary

1. Introduce canonical constants:
   - user roles: `superuser|stuff|general`
   - membership roles: `admin|manager|agent|viewer`
2. Replace hardcoded legacy role strings in service/middleware with constants.
3. Keep temporary legacy aliases only in compatibility layer.

Files:
- `server/app/api/v1/auth/service.py`
- `server/app/api/v1/businesses/service.py`
- `server/app/middleware/permissions.py`
- `server/app/models/user.py`
- `server/app/models/workspace_membership.py`

Acceptance:
- No runtime path requires `owner` as user role.
- No new code writes `owner` into membership role.

---

## 3. Authorization Resolver (New, Side-by-Side)

1. Create central resolver (pure function/service) to compute:
   - actor user
   - target business
   - actor active membership (if needed)
   - effective permission set
2. Keep old decorators running; compare old/new decisions when flag disabled.
3. Log any mismatch with actor, endpoint, business, old decision, new decision.

Files:
- `server/app/middleware/permissions.py` (or new `server/app/services/authz_resolver.py`)

Acceptance:
- Resolver is testable in isolation.
- No endpoint behavior change while `AUTHZ_V2_ENABLED=false`.

---

## 4. Decorator Refactor to Policy-Based Checks

1. Refactor/introduce decorators:
   - `require_superuser`
   - `require_stuff_or_superuser`
   - `require_same_business`
   - `require_business_membership(*roles)`
   - `require_permission(policy_key)`
2. `require_permission` logic:
   - `superuser` => platform override
   - non-superuser => evaluate membership permissions in target business
3. Remove direct role shortcuts like `owner/admin` checks.

Files:
- `server/app/middleware/permissions.py`

Acceptance:
- Decorators reference policy matrix keys from Phase 1.
- Cross-business checks always evaluate membership, not only `user.business_id`.

---

## 5. Auth Service User-Creation Rules

1. Consolidate creation on `POST /api/auth/users` contract.
2. Enforce matrix:
   - superuser: create `superuser|stuff|general`
   - stuff: create `general` only
   - general(admin): create `general` in same business only
3. For `general` creation:
   - create user
   - create membership for target business with role (`admin|manager|agent|viewer`)
4. Forbid invalid role combos with explicit error messages.

Files:
- `server/app/api/v1/auth/service.py`
- `server/app/api/v1/auth/routes.py`

Acceptance:
- Legacy endpoints (`/users/owner`, `/users/admin`, etc.) either removed or mapped to single endpoint safely.
- Unit tests cover all actor/target combinations.

---

## 6. Business Service Membership Logic Cleanup

1. Update membership defaults from legacy values to canonical values.
2. Remove owner-specific membership assumptions (`owner` membership role).
3. Keep ownership in `business.owner_user_id` only.
4. Ensure transfer ownership updates business owner link without requiring owner membership role.

Files:
- `server/app/api/v1/businesses/service.py`

Acceptance:
- Membership role domain is only `admin|manager|agent|viewer`.
- Ownership transfer does not write forbidden membership role values.

---

## 7. Route-Level Permission Mapping

1. Map each route to policy keys from `authz_policy_matrix_v2.md`.
2. Remove `require_roles("superuser","stuff")` duplication where permission policy already handles scope.
3. Ensure business-scoped endpoints resolve target business first.

Files:
- `server/app/api/v1/auth/routes.py`
- `server/app/api/v1/businesses/routes.py`
- `server/app/api/v1/access_tokens/routes.py`

Acceptance:
- Endpoint permissions are consistent with Phase 1 matrix.
- No route still references legacy role vocabulary for authz decisions.

---

## 8. Schema and Migration Adjustments

1. DB-level constraints:
   - membership unique `(business_id, user_id)` (already present; verify)
   - membership role check constraint
   - membership status check constraint
2. Migration/backfill script update:
   - map old values to new values
   - dry-run summary
   - idempotent apply

Files:
- `server/app/models/workspace_membership.py`
- `server/scripts/migrate_roles.py`

Acceptance:
- Dry-run reports deterministic output.
- Apply can be re-run without corrupting data.

---

## 9. API Schema and Docs Sync

1. Update request/response docs to single source:
   - `POST /api/auth/users` with `role` and membership assignment fields
2. Remove legacy endpoints and role references from docs.
3. Add forbidden scenarios and expected error responses.

Files:
- `server/docs/api_request_response_schema.md`
- `server/docs/auth_and_user.md`
- `server/docs/business_workspace.md`
- `server/docs/v2/authz_policy_matrix_v2.md` (if clarifications needed)

Acceptance:
- Docs match actual route/service behavior.
- No mention of deprecated role model.

---

## 10. Test Plan (Must Pass Before Enabling v2)

1. Table-driven authz tests:
   - actor account type x membership role x endpoint x expected status
2. User-creation tests:
   - allowed and denied combinations
3. Cross-business tests:
   - membership missing/inactive
4. Migration tests:
   - dry-run
   - apply
   - re-apply idempotency

Files:
- test modules under server test suite (create if missing)

Acceptance:
- All tests green with flag off and on.

---

## 11. Rollout Sequence

1. Deploy with `AUTHZ_V2_ENABLED=false` and decision-diff logging on.
2. Observe logs, fix mismatches.
3. Enable `AUTHZ_V2_ENABLED=true` in staging.
4. Run regression + permission matrix verification.
5. Enable in production.
6. After stable window, delete legacy code paths.

Rollback:
- Set `AUTHZ_V2_ENABLED=false` to restore legacy authorization path.

