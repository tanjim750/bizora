# Business Memory & Knowledge and AI Intelligence: Feature Traceability Matrix

## 1. Executive Summary & Verification Metrics
- **Runtime Environment:** Python 3.12.13 / Django 4.2.27 LTS / Django REST Framework 3.15.2
- **Authoritative Database Standard:** PostgreSQL 16 (`pgvector` compatible, SQLite local dev fallback)
- **Verification:** PostgreSQL 16.15 with pgvector 0.8.7; SQLite remains a development fallback.
- **Suite Result (2026-10-28):** 342 tests passed on PostgreSQL/Python 3.12 with no skips. The SQLite fallback run passed with two PostgreSQL-only tests skipped out of 342 discovered tests.
- **Review Regression Coverage:** `app.test_rereview_regressions` covers transaction claims, policy prompts, refunds, call evidence, JSON filtering, and daily fact refresh.
- **Linting:** Changed Python files pass `ruff check`.

---

## 2. Module A: Business Memory & Knowledge (All 19 Features)

| Feature # | Feature Name | Primary Source File | Primary Functions / Models | Test Verification Suite & Test Methods |
|---|---|---|---|---|
| **F-01** | Business Profile | `app/services/domain_memory.py` | `set_business_profile`, `get_business_profile`, `BusinessMemory` | `app.test_batch2_domain_memory.test_feature_01_business_profile_lifecycle` |
| **F-02** | Business Policies | `app/services/domain_memory.py` | `set_business_policy`, `get_business_policies`, `BusinessMemory` | `app.test_batch2_domain_memory.test_feature_02_business_policies_categorization` |
| **F-03** | Product Knowledge | `app/services/domain_memory.py` | `set_product_knowledge`, `get_product_knowledge`, `BusinessMemory` | `app.test_batch2_domain_memory.test_feature_03_product_knowledge_sku_association` |
| **F-04** | Delivery Policy | `app/services/domain_memory.py` | `set_delivery_policy`, `get_delivery_policy`, `BusinessMemory` | `app.test_batch2_domain_memory.test_feature_04_delivery_policy_tiering` |
| **F-05** | Return & Refund Policy | `app/services/domain_memory.py` | `set_return_refund_policy`, `get_return_refund_policy`, `BusinessMemory` | `app.test_batch2_domain_memory.test_feature_05_return_refund_policy_rules` |
| **F-06** | Brand Tone | `app/services/domain_memory.py` | `set_brand_tone`, `get_brand_tone`, `validate_text_against_brand_tone` | `app.test_batch2_domain_memory.test_feature_06_brand_tone_restricted_words` |
| **F-07** | Support Knowledge | `app/services/domain_memory.py` | `set_support_knowledge`, `get_support_knowledge`, `BusinessMemory` | `app.test_batch2_domain_memory.test_feature_07_support_knowledge_escalation` |
| **F-08** | Business Goals | `app/services/domain_memory.py` | `set_business_goal`, `get_active_business_goals`, `BusinessGoal` | `app.test_batch2_domain_memory.test_feature_08_business_goals_prioritization` |
| **F-09** | Historical Decisions | `app/services/domain_memory.py` | `record_historical_decision`, `check_repeat_decision_conflict`, `HistoricalDecision` | `app.test_batch2_domain_memory.test_feature_09_historical_decisions_repeat_prevention` |
| **F-10** | Approved Suggestions | `app/services/domain_memory.py` | `promote_approved_suggestion`, `ApprovedSuggestion` | `app.test_batch2_domain_memory.test_feature_10_approved_suggestions_governance_gate` |
| **F-11** | Knowledge Sources | `app/services/knowledge_pipeline.py` | `register_knowledge_source`, `archive_knowledge_source`, `KnowledgeSource` | `app.test_batch1_knowledge_pipeline.test_feature_11_register_knowledge_source_valid_and_domain_invariants` |
| **F-12** | Document Ingestion | `app/services/knowledge_pipeline.py` | `ingest_document`, SHA-256 deduplication, `KnowledgeDocument` | `app.test_batch1_knowledge_pipeline.test_feature_12_ingest_document_deduplication_and_validation` |
| **F-13** | Document Processing | `app/services/knowledge_pipeline.py` | Section-aware chunking, token estimation, `KnowledgeChunk` | `app.test_batch1_knowledge_pipeline.test_feature_13_document_processing_and_chunking` |
| **F-14** | Document Versioning | `app/services/knowledge_pipeline.py` | Sequential atomic versioning (`v1` -> `v2`), `resolve_active_version` | `app.test_batch1_knowledge_pipeline.test_feature_14_document_versioning_and_superseding` |
| **F-15** | Embeddings | `app/services/hybrid_retrieval.py` | `generate_or_store_embedding`, dimension mismatch enforcement, `KnowledgeEmbedding` | `app.test_batch3_hybrid_retrieval.test_feature_15_embedding_storage_and_dimension_validation` |
| **F-16** | Vector Search | `app/services/hybrid_retrieval.py` | `vector_search`, `cosine_similarity`, tenant & active version filtering | `app.test_batch3_hybrid_retrieval.test_feature_16_vector_search_ranking_and_isolation` |
| **F-17** | Keyword Search | `app/services/hybrid_retrieval.py` | `keyword_search`, lexical sparse scoring, exact phrase matching | `app.test_batch3_hybrid_retrieval.test_feature_17_keyword_search_and_exact_match` |
| **F-18** | Hybrid Retrieval | `app/services/hybrid_retrieval.py` | `hybrid_retrieval`, Reciprocal Rank Fusion (RRF), citation preservation | `app.test_batch3_hybrid_retrieval.test_feature_18_hybrid_retrieval_reciprocal_rank_fusion` |
| **F-19** | Chunking Strategy | `app/services/knowledge_pipeline.py` | Configurable token limits, overlap, markdown heading awareness | `app.test_batch1_knowledge_pipeline.test_feature_19_chunking_strategy_overlap_and_markdown_headings` |

---

## 3. Module B: AI Intelligence Integration & Grounding

| Capability | Source File | Primary Functions | Description & Invariant Guardrails | Test Verification Methods |
|---|---|---|---|---|
| **Grounded Context Synthesis** | `app/services/ai.py` | `assemble_grounded_memory_context` | Connects AI directly to Business Profile, Active Goals, Brand Tone, and Hybrid Knowledge with citations. Enforces tenant boundary. | `app.test_batch4_ai_intelligence_integration.test_assemble_grounded_memory_context_synthesizes_all_domains`, `test_assemble_grounded_memory_context_tenant_isolation`, `test_assemble_grounded_memory_context_empty_query_and_no_match` |
| **Goal-Aligned Recommendations** | `app/services/ai.py` | `generate_goal_aligned_recommendation` | Elevates recommendation priority (`HIGH`) and confidence (`>0.85`) when aligned with active business goals. | `app.test_batch4_ai_intelligence_integration.test_generate_goal_aligned_recommendation_prioritizes_matching_goals`, `test_generate_goal_aligned_recommendation_with_no_matching_goal` |
| **Repeat-Decision Conflict Prevention** | `app/services/ai.py` | `generate_goal_aligned_recommendation` | Checks historical memory for previously rejected or ineffective decisions; flags conflict and prevents repeated mistakes. | `app.test_batch4_ai_intelligence_integration.test_repeat_decision_prevention_suppresses_rejected_actions` |
| **Brand Tone Output Sanitization** | `app/services/ai.py` | `enforce_brand_tone_on_output` | Dynamically applies channel brand tone, sanitizes restricted terms using non-alphanumeric boundary regex across mixed casings and punctuations. | `app.test_batch4_ai_intelligence_integration.test_enforce_brand_tone_on_output_sanitizes_restricted_terms`, `test_enforce_brand_tone_edge_cases_and_casing` |
| **Human-in-the-Loop Governance Gate** | `app/services/ai.py` | `promote_recommendation_to_memory` | Prevents unapproved AI suggestions from entering durable memory without explicit human approval (`status='APPROVED'`, `user`, `timestamp`). | `app.test_batch4_ai_intelligence_integration.test_promote_recommendation_to_memory_governance_gate`, `test_promote_recommendation_cross_tenant_isolation_rejected`, `test_promote_recommendation_requires_authoritative_user` |
| **Unified AI Service Facade** | `app/services/ai.py` | `__all__` export facade | Unified export of `ask_business_assistant`, `diagnose_business_issue`, `explain_campaign_performance`, `summarize_call`, etc. | Full suite regression (`app.test_ai_endpoints_matrix`, `app.test_ai_intelligence`) |

---

## 4. Architectural Boundary Invariants

1. **Business Memory != Business Data:**
   - **Enforcement:** Recursive inspection of source types and metadata payloads in `app/services/knowledge_pipeline.py`.
   - **Behavior:** Rejection of transactional payloads (`TRANSACTION_EVENT`, `RAW_WEBHOOK`, `ORDER_LOG`, `order_id`, `transaction_id`, `payment_intent_id`) with `DomainBoundaryViolationError`.
2. **Business Memory != Business Intelligence:**
   - **Enforcement:** Rejection of streaming metric snapshots and live aggregations (`LIVE_METRIC_SNAPSHOT`, `BI_AGGREGATION`, `ANOMALY_STREAM`, `metric_window`, `calculated_rate`, `p95_latency`) with `DomainBoundaryViolationError`.
3. **Strict Multi-Tenant Isolation:**
   - **Enforcement:** Explicit `business_id` verification on every read and write operation across all services.
   - **Behavior:** Missing, null, or mismatched tenant IDs immediately raise `TenantIsolationError`.
4. **Stale Version Suppression:**
   - **Enforcement:** Automatic deactivation/superseding on document updates (`status='SUPERSEDED'`) and chunk active flags (`is_current=False`). Direct requests for stale versions raise `StaleVersionError`.
5. **Human-in-the-Loop Memory Governance:**
   - **Enforcement:** AI recommendations strictly generate `SUGGESTED` records. Promotion to `ApprovedSuggestion` requires explicit human approval with user attribution; unapproved attempts raise `UnapprovedMemoryPromotionError`.

---

## 5. Runtime Contracts After Rereview

- **External executors:** Any supplied executor must run outside an enclosing database transaction, including actions whose default `is_simulated` flag is still true. The execution claim commits before the provider is called.
- **Policy context:** Support and assistant context includes active structured business, refund, delivery, and support memory with its rule metadata. Separate category budgets keep FAQs from crowding out policy rules.
- **Refund accounting:** `Refund.status='COMPLETED'` is the canonical completed state. Full and partial refund amounts reduce the original order-date cohort and attributed campaign totals. A refund linked only through its payment's order is included. Pending refunds do not reduce these totals.
- **Call evidence:** Missing, empty, and known legacy placeholder transcripts yield `UNKNOWN` purpose and outcome. Real transcript text and provider attribution are preserved; topic keywords produce a summary requiring follow-up rather than an order confirmation or cancellation.
- **Current knowledge:** PostgreSQL vector retrieval retains null metadata and missing `is_current` keys while excluding explicit false flags.
- **Daily facts:** Each reporting day has its own rule key. Recalculation refreshes that day's fact, and a corrected measurement below the threshold invalidates it. Legacy facts without a period key are retired when the deterministic calculation runs.

These checks cover local database and service behavior. Live AI/provider execution and deployment remain separate verification steps.
