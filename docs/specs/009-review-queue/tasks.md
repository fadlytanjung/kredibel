# Tasks 009 — Review Queue

## Phase 1 — Items

- [x] **T009-01** **TDD** `review_items.py`: creation and closing per kind; priority; keys; waiting-for-statement rule. (AC-009-1, AC-009-3)
  `CONFIRM_TYPE` comes with `E03` as a finding (T006-07); `LEDGER_DIFFERENCE`, `CONFIRM_LEDGER_MAPPING`
  and ledger-cited bank lines with ledger import (T005-04).
- [x] **T009-02** `sync_review_items` node. (AC-009-1)

## Phase 2 — Actions

- [x] **T009-03** **TDD** every (kind, action) pair: allowed succeed, others `422`; amounts; reasons; double resolve `409`. (AC-009-5)
- [x] **T009-03a** **TDD** `CORRECT_VALUE` for an invoice's or receipt's total and date: the corrected value on the
  record (`correctedFields`, `correctedBy`, the reading kept), audited (`VALUE_CORRECTED`), its months re-run.
  (AC-009-5)
- [x] **T009-03b** `CORRECT_VALUE` for a bank line's amount and date, re-running the statement's arithmetic checks.
- [x] **T009-04** **TDD** decisions as reconciliation inputs; event; month dirty and run. (AC-009-6)

## Phase 3 — UI

- [x] **T009-05** `ReviewPage` and `ItemPanel` with the six bodies; stories per kind. (AC-009-2, AC-009-4)
- [x] **T009-06** Auto-advance and keyboard; phone layout; visual and axe tests. (AC-009-7) (the queue, the proposal drawer and a value correction at 390/834/1440 px with axe, keyboard and 360/1600 px checks: `frontend/tests/visual/review.spec.ts`, spec 019)
  Done: auto-advance, J/K/Enter/Esc, the phone layout (the panel above the queue when they stack), visual
  baselines at 390, 834 and 1440 (`tests/visual/review.spec.ts`). Open: axe tests (no axe library yet).

## Phase 4 — Scenarios and close

- [ ] **T009-07** Scenario tests S1 and S3 through the API. (AC-009-8, AC-009-9)
- [ ] **T009-08** Update `docs/20-implementation-status.md`.
