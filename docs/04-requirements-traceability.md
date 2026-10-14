# 04 — Requirements Traceability

> Every requirement has a spec, acceptance criteria, and a test location. Every judging criterion has
> evidence a judge can see. If a row has no test, it is not done.

---

## 1. Functional requirements

| FR | Requirement (short) | Spec | Acceptance criteria | Test location |
|---|---|---|---|---|
| FR-001 | Verified Firebase ID token on every API call | 001 | AC-001-5 | `backend/tests/integration/test_auth.py` |
| FR-002 | Workspace isolation (API and rules) | 001, 003, 013 | AC-001-4, AC-003-11, AC-013-1 | `tests/integration/test_org_isolation.py`, rules tests in the emulator |
| FR-003 | Create a workspace for an individual or a company; free trial starts | 013 | AC-013-1…4 | `tests/unit/test_workspace_service.py`, `tests/integration/test_workspace_api.py` |
| FR-004 | Plan limits enforced by the server; usage visible | 013, 003, 004 | AC-013-7…13, AC-003-3, AC-004-11 | `tests/unit/test_plans.py`, `tests/integration/test_entitlements.py` |
| FR-005 | Paid plans and the loan readiness report shown as coming soon | 013 | AC-013-6, AC-013-11 | `test_plans.py`, `widgets/PlanAndUsage/*.test.tsx` |
| FR-010 | Upload PDF, images, CSV, XLSX within limits; pages split and triaged | 003 | AC-003-1…4 | `tests/unit/test_file_types.py`, `test_page_triage.py`, `test_document_service.py` |
| FR-011 | Exact copies recorded, not read, not counted | 003 | AC-003-5, AC-003-6 | `test_document_service.py` |
| FR-012 | Content duplicates held until a person decides | 006, 009 | AC-006-1…6, AC-009-9 | `tests/unit/test_duplicates.py`, `tests/scenarios/test_s3_duplicates.py` |
| FR-013 | Documents library with live status and filters | 003 | AC-003-7…10 | `tests/integration/test_documents_api.py`, `pages/DocumentsPage.test.tsx` |
| FR-020 | Classification; uncertain type asks the user | 005 | AC-005-1…3 | `tests/scenarios/test_reading.py` |
| FR-021 | AI reader + witness + verifier with provenance | 005 | AC-005-4…9 | `tests/unit/test_verify.py`, `test_normalize.py`, `tests/scenarios/test_reading.py` |
| FR-022 | Ledger import with a confirmed mapping | 005 | AC-005-10…12 | `tests/unit/test_ledger_parse.py`, `tests/scenarios/test_ledger.py` |
| FR-023 | Integrity checks with evidence and verdicts | 006 | AC-006-7…12 | `tests/unit/checks/*`, `tests/scenarios/test_s2_tampered.py` |
| FR-024 | Categorization with precedence | 007 | AC-007-1, AC-007-2 | `tests/unit/test_categorize.py` |
| FR-030 | Months reconcile on every change, order-independent | 004, 007 | AC-004-4…7, AC-007-3, AC-007-7 | `tests/unit/test_reconcile_order.py` (hypothesis), `tests/scenarios/test_s5_reverse.py` |
| FR-031 | Deterministic, explainable matching; automatic only when unique | 007 | AC-007-5, AC-007-8, AC-007-17 | `tests/unit/test_reconcile_scoring.py`, `tests/unit/test_reconcile.py` |
| FR-032 | Exact, split, multi-invoice, net-of-tax, ledger matches | 007 | AC-007-4, AC-007-6 | `test_reconcile.py` |
| FR-033 | Exceptions become review items | 009 | AC-009-1…3 | `tests/unit/test_review_items.py` |
| FR-034 | Resolve by match, correction, duplicate decision or ignore; audited; month re-runs | 009, 007 | AC-009-4…7, AC-007-13 | `tests/unit/test_review_service.py`, `tests/integration/test_review_api.py` |
| FR-035 | Month summary (figures, auto-match rate, items, risk) | 007 | AC-007-9, AC-007-12 | `tests/unit/test_figures.py`, `pages/MonthPage.test.tsx` |
| FR-036 | Bank cash evidence separate from document support; honest month completion | 007 | AC-007-14, AC-007-15, AC-007-18 | `tests/unit/test_month_workflow.py`, `design/mocks/reconciliation.html`; state/figure tests in T007-04…08 |
| FR-037 | Separate document approval and payment confirmation without bank evidence | 007 | AC-007-16 | `design/mocks/reconciliation.html`; audited API and migration tests in T007-06a |
| FR-038 | Fixed workspace currency; explicit agreement for differently printed currency, no FX | 007 | AC-007-19 | `tests/unit/test_reconcile_scoring.py`; persistence and UI in T007-06a/T007-10 |
| FR-040 | Cross-document and month checks | 007 | AC-007-10, AC-007-11 | `tests/unit/checks/test_month_checks.py`, `tests/scenarios/test_s4_diversion.py` |
| FR-041 | Risk level per document and month from policy | 008 | AC-008-1…3, AC-008-11 | `tests/unit/test_risk.py` |
| FR-042 | Explanation and next steps, grounded or template | 008 | AC-008-4…6 | `tests/unit/test_grounding.py`, `tests/scenarios/test_explanations.py` |
| FR-043 | Acknowledge or dismiss findings with reasons | 008 | AC-008-9 | `tests/unit/test_finding_service.py` |
| FR-050 | Dashboard KPIs, month strip, alerts, review preview | 010 | AC-010-1…4, AC-010-9 | `tests/unit/test_insight_service.py`, `pages/DashboardPage.test.tsx` |
| FR-051 | Money flow by statement line under the framework, with bars, table and client and supplier views, and drill-down | 010 | AC-010-5…8, AC-010-12 | `tests/unit/test_money_flow.py`, `widgets/MoneyFlow/*.test.tsx` |
| FR-052 | Month strip states | 010 | AC-010-9 | `widgets/MonthStrip.test.tsx` |
| FR-053 | Months in and out, and the cash-flow statement; full-width charts | 010 | AC-010-4, AC-010-13, AC-010-14 | `tests/unit/test_cash_flow.py`, `widgets/CashFlow/*.test.tsx` |
| FR-060 | Profile and bank accounts (masked) | 013 | AC-013-2, AC-013-14 | `test_workspace_service.py`, `tests/unit/test_accounts.py` |
| FR-061 | Profile suggestions with evidence; user decides | 014 | AC-014-4…7 | `tests/unit/test_profile_suggestions.py`, `tests/scenarios/test_profile.py` |
| FR-062 | Clients and suppliers with accounts seen | 014 | AC-014-1…3 | `tests/unit/test_counterparties.py` |
| FR-054, FR-055 | Company account/subledger classifications and P&L | 018 | AC-018-1…7 | `test_profit_loss.py`, `test_profit_loss_api.py`, P&L UI tests |
| FR-070 | Finance Assistant: tools, retrieval, memory (P1) | 011 | AC-011-1…13 | `tests/unit/test_finance_tools.py`, `backend/evals/assistant/` |
| FR-071 | Roles restrict actions (P1) | 013 | AC-013-17…19 | `tests/unit/test_access.py` (table-driven) |
| FR-072 | Model Armor screening and quarantine (P1) | 015 | AC-015-1 | `tests/scenarios/test_s6_injection.py` |
| FR-073 | Run graph (P1) | 015 | AC-015-4 | `widgets/RunGraph/*.test.tsx` |
| FR-074 | Every classification and categorization is a label a person can confirm or correct; people win (P1) | 016 | AC-016-1…7 | `tests/unit/test_labels.py` (property test over re-runs), `tests/integration/test_labels_api.py`, `pages/LabelsPage.test.tsx` |
| FR-075 | Cash-flow class follows the workspace's framework (IFRS or US GAAP) | 016, 010 | AC-016-8, AC-010-12 | `tests/unit/test_categories.py`, `tests/unit/test_money_flow.py` |
| FR-076 | Run history of every model and tool call, with feedback joined; content only with synthetic data (P1) | 017 | AC-017-2…7 | `tests/unit/test_settings_content_capture.py`, `tests/integration/test_run_events_api.py`, `pages/RunsPage.test.tsx` |

## 2. Non-functional requirements

| NFR | Target | Verified by |
|---|---|---|
| NFR-01 | ≤ 60 s p50 per 3-page statement; month run ≤ 20 s p50 | E-PERF (spec 012) |
| NFR-02 | Progress visible ≤ 2 s | Listener tests; manual check on the deployed env; AC-004-8 |
| NFR-03 | Read API p95 ≤ 500 ms | AC-010-10; Cloud Monitoring on the demo env |
| NFR-04 | Seeded tampering and duplicates detected; 0 false `TAMPERED` | Scenario tests (gate) + E-FOR, E-DUP |
| NFR-05 | ≥ 85% auto-matched on S1; 0 wrong automatic matches | AC-007-8 (gate) + E-REC |
| NFR-06 | Workspace isolation in API and rules; no secrets | `test_org_isolation.py`, rules tests, secret scan in CI |
| NFR-07 | ≤ USD 0.01 per page; ≤ USD 0.40 for S1's statements and invoices; exact duplicates free | E-EXT, E-PERF; [`21`](21-cost-analysis.md) |
| NFR-08 | WCAG AA contrast; no colour-only meaning; chart table alternatives | axe in stories and E2E; AC-008-10, AC-010-7 |
| NFR-09 | Idempotent workflows; order-independent months | AC-004-3, AC-004-5, AC-007-7 |
| NFR-10 | Correlated logs and traces | AC-004-12, AC-017-9; tracing unit/integration tests, `make trace-smoke`, manual check in Cloud Logging and Trace |
| NFR-11 | English UI, all strings externalized | ESLint `i18next/no-literal-string` in `make check`; AC-001-14 |
| NFR-12 | Personal data minimization | `test_accounts.py`, log review, AC-003-4, AC-013-2 |
| NFR-13 | Responsive and touch-friendly | Visual tests at 390/834/1440; 360 px check; AC-001-16 |
| NFR-14 | UI quality gates | `make check` (tokens-check, no_raw_styles), Storybook axe, visual tests, Lighthouse; AC-001-15, AC-001-17, AC-001-18, AC-010-11 |
| NFR-15 | Safe data evolution | Upcaster and migration tests, schema drift gate; AC-001-19 – AC-001-22 |

## 3. Judging criteria → evidence

| Criterion (weight) | What we show | Where |
|---|---|---|
| **Technical Merit & Gen AI (40%)** | Two ADK workflows (dynamic per-document with per-page parallel reads; static per-month) on Cloud Run + Cloud Tasks; adaptive reading (Gemini on page images + free text-layer or OCR witness + verifier); Gemini proposes ledger mappings from shapes only; order-independent reconciliation; grounded explanations; Finance Assistant with tools, Firestore vector retrieval, Sessions and Memory Bank; ADK traces as a run graph; DeepEval with a Gemini judge; evals with real numbers | [`06`](06-agent-design.md), [`07`](07-document-intelligence.md), [`17`](17-observability.md), eval report, the run graph in the demo |
| **Problem Alignment & Impact (25%)** | Theme 1 fraud and risk detection + process automation for small businesses: duplicates, edited statements and payment diversion caught before month close; 80–85% of matching automated with a short, honest review queue | [`01`](01-brainstorm-and-decision.md), [`01a`](01a-concept-deep-dive.md), [`02`](02-research.md), proposal |
| **Innovation & Creativity (25%)** | "Two readings before an accusation", the second one free; uploads in any order with the same result; a supplier's changed bank account found across documents; a profile the documents fill in, with proof; catching an attempt to talk to the AI | hero scenarios ([`01a`](01a-concept-deep-dive.md) §5) |
| **UX & Solution Design (10%)** | Dashboard separate from the tables; money-flow Sankey; evidence viewer with the lamp; a review queue that works on a phone; a friendly, accessible design system with a real logo | [`11`](11-frontend.md), [`12`](12-design-system.md), `design/mocks/` |
