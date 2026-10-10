# Tasks 009 — Review & Decision

## Phase 1 — Backend (TDD)

- [ ] **T009-01** **TDD** complete `case_state.py` transition table and guards (table-driven test). (AC-009-11, AC-009-14)
- [ ] **T009-02** **TDD** `ReviewService.update_finding` (dismiss requires reason; events). (AC-009-4)
- [ ] **T009-03** **TDD** `ReviewService.decide` atomic write: case, memo FINAL, event. (AC-009-13)
- [ ] **T009-04** Routers: `PATCH /findings/{id}`, `POST /decision`, `GET /events`; integration tests for each error code. (AC-009-11, AC-009-15)

## Phase 2 — Design system additions

- [ ] **T009-05** `SeverityBadge`, `VerdictBadge`, `GradeBadge`, `Gauge`, `StatTile`, `CitationChip`, `CodeText`, `Drawer`, `Dialog`, `Popover`, `SafeMarkdown` with axe checks.

## Phase 3 — Workspace tabs

- [ ] **T009-06** Overview (RiskSummary, tiles with formula popovers, integrity strip, top findings). (AC-009-1, AC-009-2)
- [ ] **T009-07** Findings tab with grouping, filters, acknowledge/dismiss. (AC-009-3, AC-009-4)
- [ ] **T009-08** Evidence viewer: page render, overlays, facts, readings comparison (AI reader vs witness), related findings, keyboard, deep link, no-bbox notice. (AC-009-5, AC-009-6, AC-009-7)
- [ ] **T009-09** Cash flow tab (chart + table alternative + transactions table → viewer). (AC-009-8)
- [ ] **T009-10** Reconciliation tab. (AC-009-9)
- [ ] **T009-11** Memo tab with citation chips and grounding badge. (AC-009-10)
- [ ] **T009-12** Decision panel (rules mirror, reason field, conditions list, confirm dialog for overrides, server error mapping, post-decision state). (AC-009-12, AC-009-13)
- [ ] **T009-13** Activity tab. (AC-009-15)

## Phase 4 — Verify (P0)

- [ ] **T009-14** Component tests (MSW) for decision panel guards and evidence viewer states.
- [ ] **T009-15** Playwright smoke: S2 → open A01 evidence → try approve (blocked) → decline with reason → event visible.
- [ ] **T009-16** `backend/scripts/seed_demo.py` (creates `org_demo` cases from S1–S3 seed-1 via the API and runs them) and `reset_demo.py` (deletes the org's Firestore tree and GCS prefix).
- [ ] **T009-17** Deployed walkthrough on S1, S2, S3; fix UX issues; update `docs/20-implementation-status.md`.

## Phase 5 — P1 (after the cut line)

- [ ] **T009-18** Memo edit + `PUT /memo` + guard re-run. (AC-009-16)
- [ ] **T009-19** Transaction re-categorize + stale banner. (AC-009-17)
- [ ] **T009-20** Information-request letter draft (`draft_info_request.md` prompt). (AC-009-18)
