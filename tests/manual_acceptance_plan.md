# Manual acceptance and exploratory plan

Status: prepared, not executed. Use a staging deployment with disposable test businesses and no live provider effects unless explicitly approved by the business owner. Record tester, build commit, browser/device, date, observed result, and screenshots or request IDs for every case. A business owner signs off only after reviewing the evidence.

| Case | Actor and action | Expected result |
| --- | --- | --- |
| UAT-01 | Viewer signs in and selects an assigned business. | Only active memberships appear; overview and records show data from the selected business. |
| UAT-02 | Viewer attempts manager navigation, direct manager URL, and a record write. | Manager controls stay hidden; direct URL and write are denied without changing data. |
| UAT-03 | Manager opens a second, unrelated business ID or record ID by changing the URL. | No foreign record or metadata is disclosed. |
| UAT-04 | Operator creates a canonical record, repeats the same idempotency key, then changes the payload under that key. | First write succeeds; replay does not duplicate; changed replay is rejected. |
| UAT-05 | Manager compares product source evidence and confirms a mapping. | Evidence and chosen canonical product are visible; the stored mapping matches the review; no unrelated product changes. |
| UAT-06 | Manager reviews an identity conflict and a proposal. | Decision, reason, and audit identity are retained; no external action occurs from review alone. |
| UAT-07 | Operator records a partial refund, requests and schedules a callback, and prepares an outbound call. | Monetary limits hold, callback status is correct, and preparation does not claim provider execution. |
| UAT-08 | User signs out, then uses the Back button and a saved business URL. | Protected data is no longer available; sign-in is required again. |
| UAT-09 | Tester uses only keyboard to sign in, navigate, open forms, submit, and dismiss mobile navigation at 320 px. | Focus remains visible, labels describe controls, Escape closes navigation, and content does not overflow. |
| UAT-10 | Tester repeats UAT-01, UAT-07, and UAT-09 in current Chrome, Firefox, and Safari on supported desktop/mobile devices. | Same business result and permissions; no browser-specific breakage. |
| UAT-11 | Tester disconnects the configured AI or integration provider in staging, then retries a relevant flow. | UI reports unavailable or failed status honestly; canonical records and outbound state remain unchanged. |

Exploratory charter: follow unexpected links, vary filter values and page numbers, refresh after writes, use two tabs with stale state, paste malformed IDs and dates, and try interrupted requests. Record each defect with reproducible steps and affected business/role. Do not classify an unscripted session as passed until a human tester performs it.

Beta gate: after internal sign-off and PostgreSQL/TLS checks, invite opted-in users to staging, collect task completion and defect reports, triage data and permission issues before expanding access. No beta session has run as part of this report.
