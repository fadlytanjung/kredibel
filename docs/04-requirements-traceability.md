# 04 — Requirements Traceability

> Every requirement has a spec, acceptance criteria, and a test location. Every judging criterion has
> evidence a judge can see. If a row has no test, it is not done.

---

## 1. Functional requirements

| FR | Requirement (short) | Spec | Acceptance criteria | Test location |
|---|---|---|---|---|
| FR-001 | Verified Firebase ID token on every API call | 001 | AC-001-5 | `backend/tests/integration/test_auth.py` |
| FR-002 | Workspace (org) + role from custom claims | 001, 013 | AC-001-3, AC-001-4, AC-001-6, AC-013-1 | `test_auth.py` |
| FR-003 | Org isolation | 003 | AC-003-5 | `tests/integration/test_org_isolation.py` |
| FR-004 | Create case for an applicant | 003 | AC-003-1…3 | `tests/unit/test_case_service.py` |
| FR-005 | List cases | 003 | AC-003-4 | `tests/integration/test_cases_api.py`, `frontend/src/pages/CaseListPage.test.tsx` |
| FR-010 | Upload with type and plan limits | 003, 013 | AC-003-7…9, AC-003-12, AC-013-7 | `tests/unit/test_document_service.py`, `tests/unit/test_plans.py` |
| FR-011 | Duplicate rejection | 003 | AC-003-10 | `test_document_service.py` |
| FR-012 | Remove document in DRAFT | 003 | AC-003-16 | `test_document_service.py` |
| FR-013 | View pages | 003 | AC-003-15 | `tests/integration/test_documents_api.py` |
| FR-014 | Page split and triage | 003 | AC-003-11, AC-003-22 | `tests/unit/test_page_triage.py`, `test_document_service.py` |
| FR-020 | Start analysis async | 004 | AC-004-1…3 | `tests/unit/test_analysis_service.py` |
| FR-021 | Live progress | 004 | AC-004-4, AC-004-5, AC-004-10, AC-004-11 | `tests/scenarios/test_pipeline_skeleton.py`, `frontend/src/shared/firebase/listeners.test.ts` |
| FR-022 | Classification | 005 | AC-005-2…4 | `tests/scenarios/test_extraction.py` |
| FR-023 | Adaptive reading: AI reader + witness + verifier + provenance | 005 | AC-005-5…14, AC-005-16…20 | `tests/unit/test_verify.py`, `test_normalize.py`, `test_bbox.py`, `test_extraction_cache.py`, `tests/scenarios/test_extraction.py` |
| FR-024 | Low agreement → UNVERIFIABLE | 005 | AC-005-15 | `test_verify.py` |
| FR-025 | Forensic checks with evidence | 006, 007, 010 | AC-006-1…10, AC-006-13…15, AC-007-9, AC-007-11 | `tests/unit/forensics/*`, `tests/scenarios/test_forensics.py` |
| FR-026 | Integrity verdict + corroboration | 006, 010 | AC-006-11, AC-006-12, AC-010-10 | `tests/unit/forensics/test_verdict.py` |
| FR-027 | Categorization | 007 | AC-007-1…4 | `tests/unit/test_categorize.py` |
| FR-028 | Cash-flow metrics | 007 | AC-007-5…7 | `tests/unit/test_metrics.py` |
| FR-029 | Reconciliation | 007 | AC-007-8…10 | `tests/unit/test_reconciliation.py` |
| FR-030 | Scorecard + hard stops + recommendation | 008 | AC-008-1…5 | `tests/unit/test_scorecard.py`, `tests/scenarios/test_recommendation.py` |
| FR-031 | Memo with citations | 008 | AC-008-6…9 | `tests/scenarios/test_memo.py` |
| FR-032 | Grounding guard | 008 | AC-008-10…12 | `tests/unit/test_grounding.py` |
| FR-033 | No silent failures | 004 | AC-004-8, AC-004-9 | `test_analysis_service.py` |
| FR-040 | Workspace tabs | 009 | AC-009-1, AC-009-8…10, AC-009-15 | `frontend/src/widgets/**/*.test.tsx` |
| FR-041 | Evidence viewer | 009 | AC-009-5…7 | `widgets/EvidenceViewer/*.test.tsx`, Playwright smoke |
| FR-042 | Acknowledge / dismiss | 009 | AC-009-4 | `tests/unit/test_review_service.py` |
| FR-043 | Decision outcomes | 009 | AC-009-11, AC-009-13 | `test_review_service.py` |
| FR-044 | No approve over open critical | 009 | AC-009-11, AC-009-12 | `tests/unit/test_case_state.py` |
| FR-045 | Override needs risk_lead + reason | 009 | AC-009-11, AC-009-14 | `test_case_state.py` |
| FR-046 | Audit events | 003, 004, 009 | AC-003-3, AC-003-13, AC-009-13 | `tests/integration/test_events.py` |
| FR-050 | Model Armor screening + quarantine (P1) | 010 | AC-010-1…5 | `tests/scenarios/test_s6_injection.py` |
| FR-051 | Visual forensics capped (P1) | 010 | AC-010-9…11 | `tests/unit/forensics/test_visual.py` |
| FR-052 | Revision recovery (P1) | 010 | AC-010-6, AC-010-7 | `tests/unit/test_revision_diff.py` |
| FR-053 | Case assistant (P1) | 011 | AC-011-1…9 | `tests/unit/test_case_tools.py`, `backend/evals/assistant/` |
| FR-054 | Memo edit (P1) | 009 | AC-009-16 | `tests/integration/test_memo_api.py` |
| FR-055 | Run timeline (P1) | 010 | AC-010-8 | `widgets/RunTimeline/*.test.tsx` |
| FR-060 | Create workspace, free trial starts | 013 | AC-013-1, AC-013-2 | `tests/unit/test_workspace_service.py`, `tests/integration/test_workspace_api.py` |
| FR-061 | Sign-up modes and cap | 013 | AC-013-3 | `test_workspace_service.py` |
| FR-062 | Plans config; coming-soon tiers not selectable | 013 | AC-013-5, AC-013-6, AC-013-13 | `tests/unit/test_plans.py`, `widgets/PlanAndUsage/*.test.tsx` |
| FR-063 | Plan limits enforced server-side | 013, 003, 004 | AC-013-7, AC-013-9, AC-013-10, AC-003-23, AC-004-16 | `test_plans.py`, `tests/integration/test_entitlements.py` |
| FR-064 | Trial expiry behaviour | 013 | AC-013-8, AC-013-14 | `test_plans.py`, `test_entitlements.py` |
| FR-065 | Plan and usage visible | 013 | AC-013-12, AC-013-13, AC-013-15 | `test_workspace_api.py`, `widgets/PlanAndUsage/*.test.tsx` |
| FR-066 | Workspace settings; English only | 013 | AC-013-16…18 | `test_workspace_api.py`, ESLint i18n rule |
| FR-067 | Members and invites (P1) | 013 | AC-013-19, AC-013-20 | `tests/integration/test_members_api.py` |
| FR-068 | Credit-policy overrides (P1) | 013 | AC-013-21 | `tests/unit/test_policy_overrides.py` |
| FR-070 | Onboard individual or company applicant | 003 | AC-003-17, AC-003-21 | `tests/unit/test_applicant_service.py` |
| FR-071 | Account numbers masked + hashed; ID last 4 only | 003 | AC-003-18, AC-003-19 | `tests/unit/test_accounts.py`, `test_applicant_service.py` |
| FR-072 | Related parties with ownership | 003 | AC-003-19 | `test_applicant_service.py` |
| FR-073 | Case ↔ applicant snapshot | 003 | AC-003-1, AC-003-6 | `test_case_service.py` |
| FR-074 | Applicant audit events | 003, 014 | AC-003-20, AC-014-9 | `tests/integration/test_events.py` |
| FR-075 | Counterparty directory | 014 | AC-014-1…4 | `tests/unit/test_counterparties.py`, `tests/scenarios/test_profile.py` |
| FR-076 | Profile suggestions with evidence | 014 | AC-014-5…8 | `tests/unit/test_profile_suggestions.py`, `test_profile.py` |
| FR-077 | Analyst accepts or rejects | 014 | AC-014-9, AC-014-10, AC-014-15 | `tests/unit/test_applicant_service.py`, `widgets/SuggestionsPanel/*.test.tsx` |
| FR-078 | Holder check with profile; undeclared accounts | 014, 006 | AC-014-11, AC-014-12, AC-006-10 | `tests/unit/forensics/test_profile_checks.py` |
| FR-079 | Invoice tax-ID check (P1) | 014 | AC-014-13 | `test_profile_checks.py` |
| FR-080 | Related-party flows (P1) | 014 | AC-014-14 | `test_categorize.py`, `tests/scenarios/test_s7_related_party.py` |
| FR-081 | Pre-fill on upload (P1) | 014 | AC-014-17 | `tests/integration/test_prefill.py` |

## 2. Non-functional requirements

| NFR | Target | Verified by |
|---|---|---|
| NFR-01 | S1 end-to-end ≤ 3 min p50 | E-PERF (spec 012) |
| NFR-02 | Progress visible ≤ 2 s | Manual on deployed env + listener tests |
| NFR-03 | Read API p95 ≤ 500 ms | Cloud Monitoring on demo env |
| NFR-04 | Seeded tampering detected; 0 false TAMPERED | Scenario tests (gate) + E-FOR |
| NFR-05 | Memo figures grounded or labelled | Grounding unit tests + E-MEMO |
| NFR-06 | Org isolation in API and rules; no secrets | `test_org_isolation.py`, rules review, secret scan in CI |
| NFR-07 | ≤ USD 0.50 per new case, ≤ USD 0.01 per page read, ≤ USD 0.25 per re-run | E-PERF, E-EXT cost columns; [`21`](21-cost-analysis.md) |
| NFR-08 | WCAG AA contrast; no colour-only meaning | axe in component tests |
| NFR-09 | Idempotent runs | AC-004-6, AC-006-14 |
| NFR-10 | Correlated logs and traces | Manual check in Cloud Logging/Trace |
| NFR-11 | English UI, all strings externalized | ESLint `i18next/no-literal-string` in `make check`; AC-001-14 |
| NFR-12 | Personal data minimization | `test_accounts.py`, log review, AC-003-18/19 |

## 3. Judging criteria → evidence

| Criterion (weight) | What we show | Where |
|---|---|---|
| **Technical Merit & Gen AI (40%)** | ADK 2.x graph/dynamic workflow with page-level parallel branches; adaptive reading (Gemini on page images + text-layer/OCR witness + verifier) at ≈ 1/5 the cost of dual parsers; AI-suggested applicant profiles with evidence; Gemini structured outputs everywhere; grounding guard; Model Armor; Agent Platform Sessions; idempotent async runs on Cloud Run + Cloud Tasks; evals with real numbers | [`06`](06-agent-design.md), [`07`](07-document-intelligence.md), eval report, run timeline in the demo |
| **Problem Alignment & Impact (25%)** | Theme 1 fraud + risk + process automation for SME lending; sourced problem evidence; human-in-the-loop; Indonesia-first, SEA-ready policy | [`01`](01-brainstorm-and-decision.md), [`02`](02-research.md) §3, proposal |
| **Innovation & Creativity (25%)** | "Two readings before an accusation", the second one free; a profile the documents fill in, with proof; evidence-linked memo with a verifier; recovering the original value from a PDF's revision history; catching an attempt to talk to the AI | demo moments ([`01`](01-brainstorm-and-decision.md) §5.3) |
| **UX & Solution Design (10%)** | Evidence viewer, live pipeline, decision panel that explains itself, calm forensic design system | [`11`](11-frontend.md), [`12`](12-design-system.md) |
