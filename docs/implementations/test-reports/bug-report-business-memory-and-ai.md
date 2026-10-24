# Bug Report & Resolution Analysis: Business Memory & AI Intelligence

**Author:** Principal Distributed Systems & AI Engineer  
**Date:** 2026-10-24  
**Scope:** Business Memory & Knowledge Base (`app/services/domain_memory.py`, `app/services/knowledge_pipeline.py`, `app/services/hybrid_retrieval.py`) & AI Intelligence (`app/services/ai.py`)  
**Status:** ALL RESOLVED & VERIFIED (TDD RED -> GREEN Gate)  
**Total Identified Bugs:** 5  
**Total Resolved:** 5  
**Regression Test Count:** 296 / 296 Passed (100% Green)

---

## 1. Executive Summary & Defect Severity Matrix

During adversarial verification, stress testing, and exhaustive code path analysis of the Business Memory & AI Intelligence domain modules, 5 non-trivial bugs were uncovered spanning information lifecycle leakage, numerical stability in vector mathematics, channel normalization, and goal alignment hallucination.

All 5 defects were isolated with deterministic reproduction tests in [`app/test_bug_reproductions.py`](file:///home/naim/Codebase/Projects/bizora/app/test_bug_reproductions.py), confirmed via failing assertions (RED gate), resolved with minimal targeted architectural patches, and verified green across the full 296-test suite.

| Bug ID | Title | Module | Severity | Impact | Resolution Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **BUG-001** | `ARCHIVED` Knowledge Sources & Documents Leakage in Search | `hybrid_retrieval.py` | **HIGH** | Decommissioned policies and archived documentation leaked into semantic and keyword queries, corrupting AI context grounding. | **RESOLVED** (Exclusion filters applied at query & iteration level) |
| **BUG-002** | Stale `ARCHIVED` Version Resolution Bypass | `knowledge_pipeline.py` | **HIGH** | `resolve_active_version` only checked `SUPERSEDED`, allowing explicitly requested `ARCHIVED` documents without raising `StaleVersionError`. | **RESOLVED** (Enforced `StaleVersionError` on both document & source status) |
| **BUG-003** | Vector Math `NaN` / `Inf` Propagation | `hybrid_retrieval.py` | **MEDIUM** | Malformed embedding vectors containing `float('nan')` or `float('inf')` bypassed dot-product validation, corrupting similarity ranks. | **RESOLVED** (Sanitized IEEE-754 special values returning safe `0.0`) |
| **BUG-004** | Case-Sensitive Brand Tone Channel Overrides | `domain_memory.py` | **MEDIUM** | Case-sensitive dictionary lookup failed when override keys were stored in lowercase (e.g. `support`), reverting to default tone. | **RESOLVED** (Case-insensitive dictionary lookup implemented) |
| **BUG-005** | False Goal Alignment Hallucination | `ai.py` | **HIGH** | Blind fallback `if not matched_goal and goals: matched_goal = goals[0]` falsely linked unrelated issues (e.g. Marketing ROAS) to irrelevant goals (e.g. Courier RTO). | **RESOLVED** (Removed blind fallback; unaligned issues remain unaligned) |

---

## 2. Comprehensive Defect Analysis & Root Cause Resolution

### BUG-001: `ARCHIVED` Knowledge Sources & Documents Leakage in Search

- **Component:** `app/services/hybrid_retrieval.py` (`vector_search` & `keyword_search`)
- **Severity:** High (Data Integrity & Grounding Confidentiality)
- **Description:**  
  When knowledge sources or documents were archived (`status="ARCHIVED"`), their chunks remained discoverable through both dense semantic vector search and sparse BM25 keyword search because the query filters only checked for `status="SUPERSEDED"`. Consequently, an organization that decommissioned obsolete contracts, deprecated shipping rate cards, or deleted internal guides would still have those obsolete chunks retrieved and injected into the LLM context prompt.
- **Root Cause Analysis (RCA):**  
  In `vector_search`, chunk evaluation only checked `if doc.status == "SUPERSEDED": continue`. In `keyword_search`, the QuerySet only executed `.exclude(knowledge_document__status="SUPERSEDED")`. Neither function inspected `knowledge_source__status="ARCHIVED"` or `knowledge_document__status="ARCHIVED"`.
- **Reproduction Test:** [`test_bug_001_archived_knowledge_source_leaks_into_search`](file:///home/naim/Codebase/Projects/bizora/app/test_bug_reproductions.py#L40)
  ```python
  # Setup: Source with status='ARCHIVED' and ready document/chunks
  src = KnowledgeSource.objects.create(business=self.business, name="Old Policy", status="ARCHIVED", ...)
  doc = KnowledgeDocument.objects.create(business=self.business, knowledge_source=src, status="READY", ...)
  # Assertion: Search MUST NOT return chunks from archived sources
  kw_results = keyword_search(business=self.business, query="express priority overnight")
  self.assertEqual(len(kw_results), 0, "BUG-001: Keyword search returned chunks from ARCHIVED source!")
  ```
- **RED Gate Output:**
  ```text
  AssertionError: 1 != 0 : BUG-001: Keyword search returned chunks from ARCHIVED source!
  ```
- **Remediation:**  
  Updated both `vector_search` and `keyword_search` in `app/services/hybrid_retrieval.py` to filter at both the database QuerySet level (`.exclude(knowledge_document__status__in=["SUPERSEDED", "ARCHIVED"]).exclude(knowledge_document__knowledge_source__status="ARCHIVED")`) and the in-memory iteration guard.

---

### BUG-002: Stale `ARCHIVED` Version Resolution Bypass

- **Component:** `app/services/knowledge_pipeline.py` (`resolve_active_version`)
- **Severity:** High (Lifecycle & Version Alignment)
- **Description:**  
  The specification mandates that any explicitly requested historical document version that has been superseded or archived must raise `StaleVersionError` to prevent stale grounding. While `SUPERSEDED` documents triggered `StaleVersionError`, an explicitly targeted `ARCHIVED` document was returned without error.
- **Root Cause Analysis (RCA):**  
  Line 411 in `resolve_active_version` strictly checked `if doc.status == "SUPERSEDED": raise StaleVersionError(...)`, completely ignoring documents or parent sources with status `ARCHIVED`.
- **Reproduction Test:** [`test_bug_002_resolve_active_version_allows_archived_documents`](file:///home/naim/Codebase/Projects/bizora/app/test_bug_reproductions.py#L100)
  ```python
  archived_doc = KnowledgeDocument.objects.create(
      business=self.business, knowledge_source=src, version=1, status="ARCHIVED", ...
  )
  with self.assertRaises(StaleVersionError, msg="BUG-002: resolve_active_version allowed ARCHIVED document!"):
      resolve_active_version(business=self.business, knowledge_source_id=src.id, target_version=1)
  ```
- **RED Gate Output:**
  ```text
  AssertionError: StaleVersionError not raised : BUG-002: resolve_active_version allowed ARCHIVED document!
  ```
- **Remediation:**  
  Enhanced `resolve_active_version` to inspect both parent source status (`source.status == "ARCHIVED"`) and document version status (`doc.status in ("SUPERSEDED", "ARCHIVED")`), raising `StaleVersionError` immediately.

---

### BUG-003: Vector Math `NaN` / `Inf` Propagation

- **Component:** `app/services/hybrid_retrieval.py` (`cosine_similarity`)
- **Severity:** Medium (Numerical Stability & Memory Corruption)
- **Description:**  
  When calculating cosine similarity between query vectors and stored chunk vectors, passing non-standard float representations (`float('nan')` or `float('inf')` arising from upstream embedding quantization errors or API parsing failures) caused `math.sqrt` or division operations to propagate `nan`. Because `nan >= min_score` evaluates to `False` in unexpected ways, or produces sorting inconsistencies in Python's Timsort (`TypeError: '<' not supported`), this threatened retrieval pipeline crashes.
- **Root Cause Analysis (RCA):**  
  `cosine_similarity` only checked `norm_a == 0.0 or norm_b == 0.0`, lacking IEEE-754 NaN/Inf sanitization checks.
- **Reproduction Test:** [`test_bug_003_cosine_similarity_handles_nan_gracefully`](file:///home/naim/Codebase/Projects/bizora/app/test_bug_reproductions.py#L128)
  ```python
  nan_vec = [float("nan"), 0.5, 0.2, 0.1]
  normal_vec = [0.1, 0.5, 0.2, 0.1]
  sim = cosine_similarity(nan_vec, normal_vec)
  self.assertEqual(sim, 0.0, "BUG-003: cosine_similarity did not handle NaN gracefully!")
  ```
- **RED Gate Output:**
  ```text
  AssertionError: nan != 0.0 : BUG-003: cosine_similarity did not handle NaN gracefully!
  ```
- **Remediation:**  
  Added defensive pre-validation in `cosine_similarity` using `math.isnan(v)` and `math.isinf(v)` across both input vectors and final quotient, returning safe `0.0` on invalid floating-point numbers.

---

### BUG-004: Case-Sensitive Brand Tone Channel Overrides

- **Component:** `app/services/domain_memory.py` (`get_brand_tone`)
- **Severity:** Medium (Consistency & Usability)
- **Description:**  
  When tenant configuration saved channel overrides using standard lowercase naming conventions (e.g., `{"support": {"primary_tone": "Empathetic"}}` or `{"email": ...}`), calling `get_brand_tone(business, channel="SUPPORT")` or `channel="Support"` failed to match, silently falling back to the generic brand tone.
- **Root Cause Analysis (RCA):**  
  `get_brand_tone` executed `channel_upper = channel.upper()` and then checked `if channel_upper in data["channel_overrides"]`. If the stored dictionary keys were lowercase or mixed case, the exact membership check failed.
- **Reproduction Test:** [`test_bug_004_brand_tone_channel_override_case_insensitivity`](file:///home/naim/Codebase/Projects/bizora/app/test_bug_reproductions.py#L140)
  ```python
  set_brand_tone(
      business=self.business,
      tone=BrandToneData(
          primary_tone="Professional",
          channel_overrides={"support": {"primary_tone": "Empathetic & Caring"}},
      ),
  )
  tone = get_brand_tone(self.business, channel="SUPPORT")
  self.assertEqual(tone["primary_tone"], "Empathetic & Caring", "BUG-004: Channel override failed case-insensitive match!")
  ```
- **RED Gate Output:**
  ```text
  AssertionError: 'Professional' != 'Empathetic & Caring'
  ```
- **Remediation:**  
  Refactored channel override extraction to iterate over key-value pairs with normalized case comparison (`str(k).strip().upper() == channel_clean`), ensuring robust case-insensitive override application.

---

### BUG-005: False Goal Alignment Hallucination

- **Component:** `app/services/ai.py` (`generate_goal_aligned_recommendation`)
- **Severity:** High (AI Governance & Hallucination Elimination)
- **Description:**  
  When an AI recommendation was generated for an issue whose domain did not match any active business goals (e.g., pausing an underperforming Facebook advertising campaign for a business whose only active goal was "Reduce Courier RTO to 3%"), the engine falsely assigned the first goal in the list (`goals[0]`) to the recommendation metadata. The generated rationale hallucinated that pausing the ad campaign "Directly advances business goal 'Reduce Courier RTO Rate to 3%' (< 3%)".
- **Root Cause Analysis (RCA):**  
  Lines 320–322 of `generate_goal_aligned_recommendation` contained an unconstrained fallback:
  ```python
  if not matched_goal and goals:
      matched_goal = goals[0]
  ```
  This violated the Business Brain boundary rule that recommendations must only claim goal alignment when verifiable relevance exists.
- **Reproduction Test:** [`test_bug_005_recommendation_does_not_hallucinate_unrelated_goal_alignment`](file:///home/naim/Codebase/Projects/bizora/app/test_bug_reproductions.py#L164)
  ```python
  set_business_goal(business=self.business, name="Reduce Courier RTO Rate to 3%", category="LOGISTICS", ...)
  rec, _action = generate_goal_aligned_recommendation(
      business=self.business,
      issue_type="MARKETING_ROAS_DEGRADATION",
      candidate_action_type="PAUSE_CAMPAIGN",
  )
  self.assertIsNone(rec.metadata.get("aligned_goal"), "BUG-005: Marketing recommendation falsely claimed alignment with Logistics Courier goal!")
  ```
- **RED Gate Output:**
  ```text
  AssertionError: 'Reduce Courier RTO Rate to 3%' is not None : BUG-005: Marketing recommendation falsely claimed alignment with Logistics Courier goal!
  ```
- **Remediation:**  
  Removed the blind fallback to `goals[0]`. When no goal matches the domain category or issue type, `matched_goal` remains `None`, `metadata["aligned_goal"]` is omitted, and the recommendation is generated with a neutral, grounded operational rationale.

---

## 3. Verification & Regression Matrix

All 5 fixes were validated against both the dedicated bug reproduction suite and the complete test catalog.

```
----------------------------------------------------------------------
Ran 5 tests in 0.015s

OK (app.test_bug_reproductions)
----------------------------------------------------------------------
Ran 296 tests in 11.824s

OK (All Django Suites: 296 passed, 0 failed, 0 errors)
----------------------------------------------------------------------
Ruff Lint: All checks passed!
```

### Final Test Summary Table

| Test Suite | Tests Run | Result | Key Capabilities Verified |
| :--- | :--- | :--- | :--- |
| `app.test_bug_reproductions` | 5 | **5 / 5 PASSED** | Lifecycle leakage, version resolution, NaN handling, brand tone casing, goal alignment integrity |
| `app.test_critical_security_and_stress_testing` | 8 | **8 / 8 PASSED** | Cross-tenant isolation, concurrent chunk ingestion, vector poisoning, human approval bypass |
| `app.test_e2e_business_memory_knowledge_validation` | 14 | **14 / 14 PASSED** | End-to-end multi-tenant lifecycle, ingestion, version bumping, RRF retrieval, RAG grounding |
| `app.test_batch1_knowledge_pipeline` | 15 | **15 / 15 PASSED** | Sources, ingestion, document processing, chunking, deduplication, version management |
| `app.test_batch2_domain_memory` | 14 | **14 / 14 PASSED** | Operating profiles, policies, product knowledge, suppliers, tone, goals, historical decisions |
| `app.test_batch3_hybrid_retrieval` | 10 | **10 / 10 PASSED** | Embeddings, vector search, keyword search, Reciprocal Rank Fusion (RRF) |
| `app.test_batch4_ai_intelligence_integration` | 12 | **12 / 12 PASSED** | Grounded context assembly, goal alignment, repeat decision suppression, brand tone sanitization |
| Baseline Core & Analytics Suites | 218 | **218 / 218 PASSED** | Core models, event bus, analytics, attribution, diagnostic engines, actions |
| **TOTAL** | **296** | **296 / 296 PASSED** | **100% GREEN (Zero Regressions)** |

---

## 4. Conclusion & Architectural Readiness

With all 5 defects uncovered, isolated, and permanently resolved via test-driven assertions, the **Business Memory & Knowledge Base** and **AI Intelligence** modules achieve production-grade deterministic reliability:
- No decommissioned or archived documents can leak into retrieval contexts.
- Vector mathematics are mathematically guarded against non-numeric inputs.
- Brand tone configuration handles arbitrary channel casing.
- AI recommendations never fabricate false alignments with unrelated business goals.
