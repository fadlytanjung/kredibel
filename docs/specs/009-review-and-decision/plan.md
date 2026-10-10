# Plan 009 — Review & Decision

## Backend

| File | Content |
|---|---|
| `domain/case_state.py` (complete) | full transition table + guards (open criticals, role, reason, recommendation/hard stops); `DecisionNotAllowed(code, details)` |
| `services/review_service.py` | `update_finding(principal, case, finding, status, reason)`; `decide(principal, case, outcome, reason, conditions)` running guards and the atomic write (case, memo FINAL, event) |
| `api/findings.py` (PATCH), `api/decision.py`, `api/events.py` | routers |
| `tests/unit/test_case_state.py` | table-driven test over every (status, outcome, role, open criticals, hard stop, reason) combination |

## Frontend

| Area | Files |
|---|---|
| Overview | `widgets/RiskSummary/`, `entities/analysis/ui/StatTile*`, `widgets/IntegrityStrip/`, `widgets/TopFindings/`, `shared/ui/Gauge.tsx` |
| Findings | `widgets/FindingsPanel/`, `features/review-finding/` (acknowledge, dismiss dialog) |
| Evidence viewer | `widgets/EvidenceViewer/` (`PdfPage.tsx` via react-pdf, `ImagePage.tsx`, `BBoxOverlay.tsx`, `FindingFacts.tsx`, `ReadingsComparison.tsx` (AI reader vs witness), keyboard hook), route `/cases/:id/evidence/:findingId` |
| Cash flow | `widgets/CashflowPanel/` (Recharts bars + line, table alternative, category breakdown, `TransactionsTable`) |
| Reconciliation | `widgets/ReconciliationPanel/` |
| Memo | `widgets/MemoPanel/`, `shared/lib/citations.ts` (parse markers), `shared/ui/CitationChip.tsx`, `shared/ui/SafeMarkdown.tsx` |
| Decision | `widgets/DecisionPanel/`, `features/decide-case/` (rules mirror + server error mapping) |
| Activity | `widgets/ActivityPanel/` |

Rendering detail: react-pdf renders the page at the container width; overlays are positioned with
`left = x0·W`, `top = y0·H`, `width = (x1−x0)·W`, `height = (y1−y0)·H`. The pdf.js worker is bundled
locally (CSP `worker-src 'self' blob:`).

## Constitution check

P3 ✔ (evidence viewer, citation chips) · P5 ✔ (server-enforced guards, reasons, audit) · P10 ✔
(state machine table test; component tests for every guard message)
