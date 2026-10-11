# Tasks 007 — Categorization and Month Reconciliation

## Phase 1 — Categorization

- [ ] **T007-01** **TDD** `categorize.py` precedence and rules. (AC-007-1)
- [ ] **T007-02** Categorizer prompt and node; `PATCH /api/bank-lines/{txId}`. (AC-007-1, AC-007-2)

## Phase 2 — Reconciliation

- [ ] **T007-03** **TDD** scoring and windows (each component; net of tax; date window per pair). (AC-007-5)
- [ ] **T007-04** **TDD** assignment: ambiguity margin, `CONFLICT` values, splits and multi-invoice, tie-breaking, rejected proposals never return, manual matches fixed. (AC-007-3…6)
- [ ] **T007-05** **TDD** order independence property test. (AC-007-7)
- [ ] **T007-06** `figures.py` facts. (AC-007-9)
- [ ] **T007-07** **TDD** month checks `X01`, `X02`, `X08`, `X09`, `R01`, `R02`, `B01`, `B04`, `C02`, `D07`. (AC-007-10, AC-007-11)
- [ ] **T007-08** Month nodes and `finalize_month`; scenario tests S1 (≥ 85%, 0 wrong), S4, S5 = S1. (AC-007-8, AC-007-11)

## Phase 3 — API and UI

- [ ] **T007-09** Books, months and matches routes; manual match and unmatch. (AC-007-13)
- [ ] **T007-10** `MonthsPage`, `MonthPage`, `MatchPicker`; visual tests at three widths. (AC-007-12, AC-007-13)

## Phase 4 — Close

- [ ] **T007-11** Update `docs/20-implementation-status.md`.
