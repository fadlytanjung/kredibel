# Tasks 009 — Review Queue

## Phase 1 — Items

- [x] **T009-01** **TDD** `review_items.py`: creation and closing per kind; priority; keys; waiting-for-statement rule. (AC-009-1, AC-009-3)
  `CONFIRM_TYPE` comes with `E03` as a finding (T006-07); `LEDGER_DIFFERENCE`, `CONFIRM_LEDGER_MAPPING`
  and ledger-cited bank lines with ledger import (T005-04).
- [x] **T009-02** `sync_review_items` node. (AC-009-1)

## Phase 2 — Actions

- [x] **T009-03** **TDD** every (kind, action) pair: allowed succeed, others `422`; amounts; reasons; double resolve `409`. (AC-009-5)
- [ ] **T009-03a** **TDD** `CORRECT_VALUE`: the corrected value on the record (`correctedBy`, the reading kept), the
  document's checks re-run; then `LOW_CONFIDENCE_VALUE` items offer it. (AC-009-5)
- [x] **T009-04** **TDD** decisions as reconciliation inputs; event; month dirty and run. (AC-009-6)

## Phase 3 — UI

- [ ] **T009-05** `ReviewPage` and `ItemPanel` with the six bodies; stories per kind. (AC-009-2, AC-009-4)
- [ ] **T009-06** Auto-advance and keyboard; phone layout; visual and axe tests. (AC-009-7)

## Phase 4 — Scenarios and close

- [ ] **T009-07** Scenario tests S1 and S3 through the API. (AC-009-8, AC-009-9)
- [ ] **T009-08** Update `docs/20-implementation-status.md`.
