# AI Intelligence: frontend issues

Backend counterpart: [`../backend/ai-intelligence.md`](../backend/ai-intelligence.md). Rules: frontend only (`frontend/**`, docs); never change backend code; record backend problems in the backend file; never push.

## Items from the audit

| ID | Sev | Problem | What the frontend does |
|---|---|---|---|
| AIS-04 | high | Canned output shown as AI: provider unavailable still 200 with `tokens_used 180`, `model_name 'gemini-1.5-pro'`; suggest-reply 'We are reviewing your request...'; fallback summary persisted; `AiMessage` rows stamped gemini-1.5-pro 75/75 tokens; campaign explain/call summary use no LLM (hard-coded `target_roas 2.50`, keyword rules). | Do not label AI replies by `model_name` or `tokens_used`; show 'AI provider unavailable' only once the backend returns `provider_status`. |
| AIS-15 | low | If facts/issues are ever derived again, `get_or_create(defaults=...)` never refreshes evidence text (stale text reached the diagnosis prompt). | Show an honest unavailable/error state with the backend's `detail`; keep the normalizer defensive; re-test when the backend item is fixed. |

## UI-found issues

_(none recorded yet; add rows: ID `FE-<DOMAIN>-NN`, severity, symptom, screen/route, fix.)_
