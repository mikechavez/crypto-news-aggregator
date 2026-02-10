# Windsurf Context Index - High Priority Files

**Generated:** 2026-02-10
**Total Windsurf Files:** 231
**Files with High-Value Keywords:** 167
**Files in 50-200 Line Sweet Spot:** 93

---

## How to Use This Index

This index identifies the highest-priority Windsurf context files for extracting historical context during FEATURE-041A. Rather than reading all 231 files (~45K lines), focus on the 93 files below.

**Workflow:**
1. Identify your module (e.g., processing, ingestion, scheduling)
2. Read only HIGH PRIORITY files from that cluster (5-10 files per module)
3. Extract context following FEATURE-041A template
4. Mark source as "Windsurf: [filename]" in context doc
5. Link to system doc anchor (FEATURE-039 docs)

**Rules:**
- Don't read all 231 files
- Use this index to find relevant subset per module
- If file contradicts code, note for FEATURE-041B
- If duplicate of another doc, cite both but don't duplicate entry

---

## Files by Topic Cluster

### Processing (Entities, Narratives, Signals)
**41 files** — Narrative discovery, entity extraction, signal calculation

**High Priority (5):**
1. **NARRATIVE_DISCOVERY_IMPLEMENTATION.md** (185 lines)
   - **Keywords:** decision, why, architecture
   - **Summary:** Two-layer narrative discovery replacing 12-theme rigid classification. Layer 1 (discovery) extracts actors, actions, tensions, implications naturally. Layer 2 (salience clustering) groups by semantic similarity. Includes rationale for why natural discovery beats predefined themes.
   - **Links to:** 50-data-model.md § narratives collection
   - **Path:** `NARRATIVE_DISCOVERY_IMPLEMENTATION.md`

2. **NARRATIVE_MATCHING_FIX_VERIFICATION.md** (193 lines)
   - **Keywords:** bug, fix, decision
   - **Summary:** Critical bug fix: threshold change from `> 0.6` to `>= 0.6` improved match rate from 62.5% to 89.1%. Includes verification results showing all 41 matched narratives achieved 0.800 similarity scores. Explains why the boundary condition matters.
   - **Links to:** 50-data-model.md § matching logic
   - **Path:** `NARRATIVE_MATCHING_FIX_VERIFICATION.md`

3. **LIFECYCLE_STATE_IMPLEMENTATION.md** (159 lines)
   - **Keywords:** implementation, constraint
   - **Summary:** Five-state lifecycle tracking (emerging/rising/hot/cooling/dormant). Defines state transitions based on article count, velocity, and recency. Explains priority order: recency checks first, then activity level.
   - **Links to:** 50-data-model.md § lifecycle_state field
   - **Path:** `LIFECYCLE_STATE_IMPLEMENTATION.md`

4. **ENTITY_EXTRACTION_FIX_SUMMARY.md** (172 lines)
   - **Keywords:** bug, fix, incident
   - **Summary:** Entity extraction failures revealed by production data. Fixes included normalization, unknown type handling, and semantic boost for precision.
   - **Links to:** 50-data-model.md § entities processing
   - **Path:** `ENTITY_EXTRACTION_FIX_SUMMARY.md`

5. **SIGNALS_PERFORMANCE_FINAL_SUMMARY.md** (198 lines)
   - **Keywords:** decision, tradeoff, optimization
   - **Summary:** N+1 query problem: tried batch queries (slow), settled on parallel indexed queries. Before: 100+ sequential queries (5-10s). After: 50 parallel queries (~6s cold, <0.1s cached). Key insight: batch queries aren't always faster if they scan large collections.
   - **Links to:** 50-data-model.md § performance considerations
   - **Path:** `SIGNALS_PERFORMANCE_FINAL_SUMMARY.md`

**Medium Priority (10):**
- SALIENCE_CLUSTERING_UPDATE.md (181 lines) - Clustering algorithm refinement
- ENTITY_NORMALIZATION_SUMMARY.md (170 lines) - Entity type standardization
- NARRATIVE_VALIDATION_FEATURE.md (180 lines) - Quality assurance approach
- DUPLICATE_NARRATIVES_ANALYSIS.md (155 lines) - Deduplication strategy
- SIGNAL_DETECTION_IMPLEMENTATION.md (166 lines) - Signal calculation methods
- FINGERPRINT_SIMILARITY_SUMMARY.md (175 lines) - Matching mechanism
- SEMANTIC_BOOST_IMPLEMENTATION.md (92 lines) - Entity relevance weighting
- MISSING_NARRATIVES_PROCESSING_RESULTS.md (181 lines) - Recovery procedures
- TIMESTAMP_FIX_SUMMARY.md (244 lines) - Temporal consistency
- NARRATIVE_VALIDATION_FEATURE.md (180 lines) - QA methodology

**Low Priority (26):**
- NARRATIVE_DETECTION_TEST_RESULTS.md, ENTITY_EXTRACTION_DEBUG.md, MATCHING_FAILURE_DEBUG_RESULTS.md, FINGERPRINT_SIMILARITY_IMPLEMENTATION.md, ECHO_REACTIVATION_STATES_IMPLEMENTATION.md, ADAPTIVE_THRESHOLD_IMPLEMENTATION.md, REACTIVATED_STATE_FILTERING_FIX.md, ORGANIZATION_ENTITY_TYPE.md, LAST_ARTICLE_AT_IMPLEMENTATION.md, ARCHIVE_TAB_ISSUE_ANALYSIS.md, ARCHIVE_TAB_ISSUE_FOUND.md, ARCHIVE_TAB_ISSUE_RESOLVED.md, ARCHIVE_TAB_DEBUG_QUICKSTART.md, THEME_NARRATIVE_IMPACT_TEST_RESULTS.md, UNKNOWN_ENTITY_BUG_FIX_SUMMARY.md, NARRATIVE_CARDS_FIX.md, NARRATIVE_ENTITY_LINKING_FIX.md, NARRATIVE_ARTICLES_FIX.md, NARRATIVE_QUALITY_AUDIT.md, ENTITY_TYPE_DISPLAY_FIX.md, SIGNAL_CALCULATION_FIX.md, NARRATIVE_COVERAGE_ANALYSIS.md, ARTICLE_LIST_FIX.md, ARTICLE_LIST_FIX_DEPLOYMENT.md, DEPLOY_NARRATIVE_ARTICLES_FIX.md, HOTFIX_SENTIMENT_REMOVAL_VERIFICATION.md

---

### Ingestion (RSS, Article Fetching, News Sources)
**15 files** — RSS feeding, article enrichment, source management

**High Priority (3):**
1. **RSS_FETCHER_FIX_SUMMARY.md** (195 lines)
   - **Keywords:** bug, fix, incident
   - **Summary:** Critical production incident: RSS fetcher crashed every 30 minutes due to missing `OPENAI_API_KEY` in Settings class. No articles fetched for 20 hours. Root cause was LLM provider expecting field that wasn't defined.
   - **Links to:** 20-scheduling.md § fetch_news task
   - **Path:** `RSS_FETCHER_FIX_SUMMARY.md`

2. **RSS_EXPANSION_SUMMARY.md** (129 lines)
   - **Keywords:** decision, why, expansion
   - **Summary:** Rationale for RSS-only approach after API failures. CoinDesk and Bloomberg APIs blocked requests. RSS provides reliable fallback with ~150 sources. Cost-effective and resilient.
   - **Links to:** 30-ingestion.md (when created)
   - **Path:** `RSS_EXPANSION_SUMMARY.md`

3. **API_RETRY_LOGIC_IMPLEMENTATION.md** (109 lines)
   - **Keywords:** implementation, constraint
   - **Summary:** Retry logic with exponential backoff for API failures. Handles transient errors vs. permanent blocks. Critical for handling rate limiting.
   - **Links to:** 30-ingestion.md (when created)
   - **Path:** `API_RETRY_LOGIC_IMPLEMENTATION.md`

**Medium Priority (5):**
- RSS_FETCHER_TEST_RESULTS.md (82 lines) - Test validation
- PR_RSS_EXPANSION.md (111 lines) - RSS feature PR summary
- BENZINGA_REMOVAL_COMPLETE.md (252 lines) - Source removal procedure
- BENZINGA_DELETION_COMPLETE.md (177 lines) - Cleanup results
- BENZINGA_NARRATIVE_REMOVAL.md (117 lines) - Data cleanup

**Low Priority (7):**
- BENZINGA_DELETION_GUIDE.md, BENZINGA_BLACKLIST_FIX.md, BENZINGA_REMOVAL_SUMMARY.md, QUICK_REFERENCE_API_RETRY.md, RATE_LIMITING_COMPLETE.md, CONSERVATIVE_RATE_LIMITING.md, BACKFILL_READY_TO_RUN.md

---

### Data/Database (MongoDB, Collections, Schema)
**22 files** — Data persistence, collection management, schema evolution

**High Priority (4):**
1. **NARRATIVE_MATCHING_TEST_RESULTS.md** (165 lines)
   - **Keywords:** test, verification, bug
   - **Summary:** Test results validating narrative matching fixes. High-confidence matches (0.800 similarity). Database state changes tracked before/after.
   - **Links to:** 50-data-model.md § matching verification
   - **Path:** `NARRATIVE_MATCHING_TEST_RESULTS.md`

2. **NARRATIVE_FINGERPRINT_BACKFILL.md** (133 lines)
   - **Keywords:** implementation, constraint
   - **Summary:** Backfill strategy for adding fingerprint field to existing narratives. Batch processing approach with verification.
   - **Links to:** 50-data-model.md § fingerprint field
   - **Path:** `NARRATIVE_FINGERPRINT_BACKFILL.md`

3. **LIFECYCLE_HISTORY_TRACKING.md** (180 lines)
   - **Keywords:** implementation, why
   - **Summary:** Historical tracking of narrative state changes over time. Enables timeline visualization and retrospective analysis.
   - **Links to:** 50-data-model.md § lifecycle history
   - **Path:** `LIFECYCLE_HISTORY_TRACKING.md`

4. **BACKFILL_VALIDATION_TEST_RESULTS.md** (166 lines)
   - **Keywords:** test, verification
   - **Summary:** Comprehensive backfill validation approach. Sampling strategy, consistency checks, before/after state comparison.
   - **Links to:** 50-data-model.md § data integrity
   - **Path:** `BACKFILL_VALIDATION_TEST_RESULTS.md`

**Medium Priority (6):**
- NARRATIVE_CACHING_IMPLEMENTATION.md (157 lines) - Caching strategy
- DUPLICATE_NARRATIVES_SUMMARY.md (153 lines) - Merging approach
- NARRATIVE_PERSISTENCE_INVESTIGATION.md (432 lines) - Historical data analysis
- BACKFILL_COMPLETE_SUMMARY.md (159 lines) - Backfill results
- NARRATIVE_MATCHING_IMPLEMENTATION_SUMMARY.md (133 lines) - Matching implementation
- NARRATIVE_MERGE_SUMMARY.md (102 lines) - Merge logic

**Low Priority (12):**
- NARRATIVE_CACHING_TEST_RESULTS.md, TIMELINE_VIEW_READY_FOR_TESTING.md, FINGERPRINT_VALIDATION_IMPLEMENTATION.md, DUPLICATE_NARRATIVES_ANALYSIS.md, LIFECYCLE_STATE_BACKFILL_QUICK_START.md, NARRATIVE_BACKFILL_SESSION_SUMMARY.md, BACKFILL_NULL_FINGERPRINTS_QUICKSTART.md, MERGE_DUPLICATE_NARRATIVES_QUICKSTART.md, LIFECYCLE_STATE_BACKFILL_QUICK_START.md, DEPLOYMENT_VERIFICATION.md, NARRATIVE_VERIFICATION_RESULTS.md, NARRATIVE_VALIDATION_FEATURE.md

---

### Frontend (React, UI Components, Routing)
**8 files** — Frontend implementation, component behavior, UI fixes

**High Priority (3):**
1. **UI_FIXES_APPLIED.md** (196 lines)
   - **Keywords:** bug, fix, implementation
   - **Summary:** Collection of UI fixes for pagination, display issues, component rendering. Addresses breaking changes and visual inconsistencies.
   - **Links to:** 70-frontend.md (when created)
   - **Path:** `UI_FIXES_APPLIED.md`

2. **NARRATIVE_UI_FILTERING_ANALYSIS.md** (196 lines)
   - **Keywords:** analysis, implementation
   - **Summary:** Frontend filtering logic for narratives by lifecycle state and other criteria. Explains filtering strategy and performance implications.
   - **Links to:** 70-frontend.md (when created)
   - **Path:** `NARRATIVE_UI_FILTERING_ANALYSIS.md`

3. **ARCHIVE_TAB_ISSUE_FINDINGS.md** (195 lines)
   - **Keywords:** bug, analysis
   - **Summary:** Archive tab data visibility issues. Root cause analysis and fix strategies.
   - **Links to:** 70-frontend.md (when created)
   - **Path:** `ARCHIVE_TAB_ISSUE_FINDINGS.md`

**Medium Priority (2):**
- UI_FIXES_SUMMARY.md (89 lines) - Summary of UI improvements
- CORS_FIX_SUMMARY.md (89 lines) - CORS issue resolution

**Low Priority (3):**
- UI_VERIFICATION_SUMMARY.md, UI_VERIFICATION_REPORT.md, UI_ISSUES_FINAL_STATUS.md

---

### Briefing/Publishing (Generation, Email, Output)
**3 files** — Briefing generation, publishing pipeline, notification

**High Priority (2):**
1. **PROGRESS_TRACKING_IMPLEMENTATION.md** (156 lines)
   - **Keywords:** implementation, feature
   - **Summary:** Real-time progress tracking for briefing generation. Status updates, timing metrics, completion verification.
   - **Links to:** 60-llm.md § progress tracking
   - **Path:** `PROGRESS_TRACKING_IMPLEMENTATION.md`

2. **NARRATIVE_CACHING_IMPLEMENTATION.md** (157 lines)
   - **Keywords:** implementation, optimization
   - **Summary:** Caching briefings and narrative data to improve performance. Strategy for cache invalidation.
   - **Links to:** 60-llm.md § performance optimization
   - **Path:** `NARRATIVE_CACHING_IMPLEMENTATION.md`

**Medium Priority (1):**
- PR_NARRATIVE_CACHING.md (197 lines) - Caching feature PR

---

### Scheduling/Workers (Celery, Beat, Task Dispatch)
**0 files in high-priority set**

Note: Scheduling is well-documented in FEATURE-039 (20-scheduling.md). Priority files focus on implementation details rather than scheduling architecture.

---

### Testing, Quality, Deployment
**6 files** — Test frameworks, CI/CD, deployment verification

**High Priority (2):**
1. **NARRATIVE_DISCOVERY_IMPLEMENTATION.md** (185 lines)
   - **Keywords:** test, implementation
   - **Summary:** Comprehensive test coverage for narrative discovery. Unit tests, integration tests, real-world scenario validation.
   - **Links to:** FEATURE-043 validation
   - **Path:** `NARRATIVE_DISCOVERY_IMPLEMENTATION.md`

2. **BACKFILL_VALIDATION_TEST_RESULTS.md** (166 lines)
   - **Keywords:** test, verification
   - **Summary:** Backfill test methodology and results. Sampling strategy, consistency checks.
   - **Links to:** FEATURE-043 validation
   - **Path:** `BACKFILL_VALIDATION_TEST_RESULTS.md`

**Medium Priority (2):**
- NARRATIVE_DETECTION_TEST_RESULTS.md (141 lines) - Detection testing
- TEST_DEBT.md (75 lines) - Test coverage gaps

**Low Priority (2):**
- SALIENCE_TEST_RESULTS.md (121 lines) - Clustering tests
- HOTFIX_SENTIMENT_REMOVAL_VERIFICATION.md (76 lines) - Cleanup verification

---

### Security, Configuration
**2 files** — Security hardening, deployment configuration

**High Priority (1):**
1. **SECURITY_QUICK_START.md** (106 lines)
   - **Keywords:** security, incident
   - **Summary:** Security incident response and hardening procedures. Configuration security, secret management.
   - **Links to:** 08-config.md (when created)
   - **Path:** `SECURITY_QUICK_START.md`

**Medium Priority (1):**
- LLM_PROVIDER_FIX.md (92 lines) - LLM configuration issues

---

## Statistics

| Category | Total | High-Priority | Medium-Priority | Low-Priority |
|----------|-------|---------------|-----------------|--------------|
| Processing | 41 | 5 | 10 | 26 |
| Ingestion | 15 | 3 | 5 | 7 |
| Data/Database | 22 | 4 | 6 | 12 |
| Frontend | 8 | 3 | 2 | 3 |
| Briefing/Publishing | 3 | 2 | 1 | 0 |
| Scheduling/Workers | 0 | 0 | 0 | 0 |
| Testing | 6 | 2 | 2 | 2 |
| Security/Config | 2 | 1 | 1 | 0 |
| **TOTAL** | **97** | **20** | **27** | **50** |

---

## Next Steps (FEATURE-041A Integration)

1. **Context Extraction Workflow:**
   - For each system doc module, read HIGH and MEDIUM priority files from matching cluster
   - Example: To extract context for 50-data-model.md, read 10 files from Data/Database cluster
   - Create context sidecar linking to system doc anchors

2. **Priority Reading Order:**
   - Start with HIGH priority files (20 files, ~10K tokens)
   - Add MEDIUM priority if budget allows (27 files, ~15K tokens)
   - Skip LOW priority unless specific context needed

3. **Token Budget Allocation:**
   - Reading priority files: ~25K tokens
   - Extracting & summarizing: ~15K tokens
   - Documentation: ~10K tokens
   - **Total for FEATURE-041A: ~50K tokens**

4. **Contradiction Detection:**
   - Mark any Windsurf file that contradicts system docs for FEATURE-041B
   - Example: "RSS-only because APIs failed" (Windsurf) vs. current code still calling APIs

---

**Last Updated:** 2026-02-10
**Ready for:** FEATURE-041A Context Extraction
