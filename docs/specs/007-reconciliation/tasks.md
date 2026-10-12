# Tasks 007 — Categorization and Month Reconciliation

## Phase 0 — Bank evidence and support (ADR-025)

- [x] **T007-00** Align the SDD and ordinary-flow mocks: statement-only rows, documents first,
  grouped/split payments and separate manual approval/payment confirmation. Screenshot three widths.
  (AC-007-14…19)
- [x] **T007-00a** **TDD** stop the skeleton month workflow claiming reconciliation from statement
  presence; keep collecting with an availability note until computed results exist. (AC-007-14)

## Phase 1 — Categorization

- [x] **T007-01** **TDD** `categorize.py` precedence and rules. (AC-007-1)
- [x] **T007-02** Categorizer prompt and node, including batch cache. (AC-007-1)
  Category correction (`PATCH /api/bank-lines/{txId}`, AC-007-2) is tracked in T007-09.

## Phase 2 — Reconciliation

- [x] **T007-03** **TDD** scoring and windows (each component; possible net of tax; date window per
  pair; currency floors, direction, whole references, incomplete evidence). Return contributions
  and reasons; fixed workspace currency and explicit override eligibility; do not assign or persist
  matches. (AC-007-5, AC-007-17, AC-007-19)
- [x] **T007-04** **TDD** assignment: ambiguity margin, `CONFLICT` values, splits and multi-invoice, tie-breaking, rejected proposals never return, manual matches fixed. (AC-007-3…6)
  `domain/reconcile.py`: allocations only; payment and support states from allocations plus
  statement coverage are derived in T007-06a.
- [x] **T007-05** **TDD** order independence property test. (AC-007-7)
- [x] **T007-06** `figures.py` facts. (AC-007-9)
- [ ] **T007-06a** **TDD** versioned evidence/support states and manual attestations: OpenAPI first,
  schema versions/upcasters/migration/snapshot, audited approval and payment confirmation endpoints,
  partial payments, statement coverage by account/date, later bank evidence without double counting.
  Bank-only rows are informational unless another rule creates a blocker. Include printed/effective
  currency, audited agreement to use unchanged amounts in workspace currency and pending exclusion.
  (AC-007-14…16, AC-007-19)
  Done: pure derivation of payment evidence, coverage and bank support (`domain/evidence.py`);
  contract and audited decisions (`/api/decisions`, `decisions` collection); the month run writes
  `evidence` and `support`.
- [ ] **T007-07** **TDD** month checks `X01`, `X02`, `X08`, `X09`, `R01`, `R02`, `B01`, `B04`, `C02`, `D07`. (AC-007-10, AC-007-11)
  `domain/checks/month.py`: all but `X09` done and tested; `X09` needs ledger import (T005-04/09).
- [ ] **T007-08** Month nodes and `finalize_month`; scenario tests S1 (≥ 85%, 0 wrong), S4, S5 = S1. (AC-007-8, AC-007-11)
  Done: `reconcile`, `check_month`, `finalize_month` write matches, evidence, support, figures,
  findings and the state; statement + invoice end-to-end test. Open: the S1/S4/S5 scenario gates.
  Align generator expectations for tax shortfalls with explicit adjustment decisions (ADR-025);
  the legacy generator scorer alone is not proof of runtime assignment quality.

## Phase 3 — API and UI

- [ ] **T007-09** Books, months and matches routes; manual match and unmatch; category correction
  `PATCH /api/bank-lines/{txId}` preserving the user's choice. (AC-007-2, AC-007-13)
- [ ] **T007-10** `MonthsPage`, `MonthPage`, `MatchPicker`, approval and payment confirmation;
  all evidence/support states, currency agreement and grouped allocations; visual tests at three
  widths. (AC-007-12…19)

## Phase 4 — Close

- [ ] **T007-11** Update `docs/20-implementation-status.md`.
