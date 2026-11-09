# Backend issues: Business Data (canonical domain API)

Domain status: **live**

Last updated: 2026-11-09. Source: synthesised from the verified code scans in `docs/frontend-api-reference.md` (written against commit 5f176a2, cited below as Part A to E) and re-checked on `main` at 8010daa, plus `tests/issues.md`, `tests/testing_report.md` and the teammate's frontend notes. **UNVERIFIED** means inferred from code and never run. Rows marked FIXED are kept so nobody re-reports them. The frontend team does not fix the backend; it writes problems here and gives the UI an honest workaround. To add a row, follow `.agents/workflows/backend-issue.md` (or the template in `README.md`).

| ID | Severity | Issue | Evidence | Impact on the UI | Suggested action for the backend owner | Frontend workaround |
|---|---|---|---|---|---|---|
| BD-01 | high | No PATCH/PUT/DELETE; customer and product fields cannot be edited (only re-post with source id and `connection_id`, or variant update) | Part A H4, section 5.6 | no edit forms | PATCH with `expected_updated_at` | read-only detail pages |
| BD-02 | high | Re-posting an existing SKU returns 400 `PRODUCT_REVIEW_REQUIRED`; a distinct product needs MANAGER `deduplication` | Part A G19 | operator add-product fails | return the candidate ids | call `products/assess/` first |
| BD-03 | medium | `q` returns 400 on 18 resources (payments, calls and others); filters are single exact values; `since/until` need an offset (`%2B` in a query string); `is_anonymous=true` returns 400; unknown query keys return 400 | Part A G12, section 5.4 | brittle filters | support `q` or publish capabilities; allow ranges; lenient booleans | hide search where unsupported; send `Z` and `True` |
| BD-04 | medium | A missing or foreign related id returns 400 `INVALID_RELATION`, not 404; a non-member and an unknown business both return 404 | Part A G14 | causes are blurred | consistent codes | map to "not found" |
| BD-05 | medium | Customer message `content` is stored wrapped in `<untrusted_customer_data>` | `app/models.py:530-531` | raw wrapper visible | return raw text plus a flag | strip the wrapper; never render as HTML |
| BD-06 | medium | `source_metadata`, `config`, `recording_url` are never returned; the product-review reason is kept in private `source_metadata` | Part A G20; handoff F02 | no durable review display | a safe read projection | show it in-session only |
| BD-07 | medium | No field schema for the 32 resources | handoff F01 | forms must hard-code rules | OpenAPI plus field metadata | Part A section 2.3 |
| BD-08 | low | Tag case differs (`POST tags/` vs `?tag=`); decimals are numbers here but strings in BI, Overview and Configuration; timeline `id` repeats across kinds | Part A G13, section 5.17 | mismatches | normalise | upper-case tags; key rows by (entity_kind, id) |
