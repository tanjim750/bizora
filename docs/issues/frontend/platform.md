# Platform, auth, routing and runtime: frontend issues

Backend counterpart: [`../backend/platform.md`](../backend/platform.md). Rules: frontend only (`frontend/**`, docs); never change backend code; record backend problems in the backend file; never push.

## Items from the audit

| ID | Sev | Problem | What the frontend does |
|---|---|---|---|
| DOM-03 | high | Huge integers in URL/query give HTML 500 (OverflowError / DataError): `/customers/99999999999999999999/`, `?customer=<huge>`, POST `inventory_quantity=2**70`; every `<int:pk>` route (also observability, configuration, BI, graph). | Never assume JSON on a 500; the normalizer must handle HTML bodies. Validate ids before building URLs. |
| DOM-11 | medium | Error shapes inconsistent: DRF-native errors have no `code` (page=0 -> 404 `{detail}`, 405, Overview/Config/Obs 403 `{detail}`); unknown URLs return HTML 404; bad `page_size` silently ignored; out-of-range page -> 404. | Normalizer must accept `{code,detail}`, `{detail}`, `{error}`, DRF field dicts and HTML. |
| PLA-10 | low | Frontend proxy passes upstream bodies unchanged (DEBUG HTML page possible); a missing `Origin` is allowed; bodies read via `.text()` (no multipart). | Recommend to the owner: wrap non-JSON upstream errors as `{detail}` in the proxy. |

## UI-found issues

_(none recorded yet; add rows: ID `FE-<DOMAIN>-NN`, severity, symptom, screen/route, fix.)_
