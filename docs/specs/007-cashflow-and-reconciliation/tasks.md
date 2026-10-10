# Tasks 007 — Cash Flow & Reconciliation

## Phase 1 — Categorization

- [ ] **T007-01** Taxonomy enums and class map (mirror `contracts/openapi.yaml` enums).
- [ ] **T007-02** **TDD** keyword rule engine from YAML (order, direction, tags-only rules). (AC-007-1, AC-007-2)
- [ ] **T007-03** **TDD** internal-transfer rule and precedence incl. analyst override protection. (AC-007-1, AC-007-4)
- [ ] **T007-04** `categorize_transactions.md` prompt + categorizer Agent node; batching; low-confidence → UNKNOWN. (AC-007-3)

## Phase 2 — Metrics (TDD)

- [ ] **T007-05** **TDD** EOD balance series with carry-forward; ADB; min balance; negative days. (AC-007-5)
- [ ] **T007-06** **TDD** monthly flows by class/category; NOCF, CADS. (AC-007-5)
- [ ] **T007-07** **TDD** aggregates: means, CV, OLS trend, annuity (incl. r = 0), DSCR proxy, max supportable installment/amount, liquidity buffer; facts with IDs and inputs. (AC-007-6, AC-007-7)

## Phase 3 — Reconciliation (TDD)

- [ ] **T007-08** **TDD** scoring components and single match (EXACT, NET_OF_TAX).
- [ ] **T007-09** **TDD** split (2 and 3 parts), partial, not-due, greedy deterministic assignment. (AC-007-8, AC-007-10)
- [ ] **T007-10** **TDD** summary and ratios.

## Phase 4 — Case-wide findings (TDD)

- [ ] **T007-11** R01, R02 with invoice evidence. (AC-007-9)
- [ ] **T007-12** C01, C02, B01, B04 with evidence. (AC-007-11, AC-007-12)

## Phase 5 — Nodes, persistence, API

- [ ] **T007-13** Real nodes + repository methods.
- [ ] **T007-14** Read endpoints with filters and pagination. (AC-007-13)
- [ ] **T007-15** Scenario tests: S1 metrics == truth; S1 reconciliation statuses; S3 R01/R02; S1 no case-wide findings. (AC-007-6, AC-007-8, AC-007-9, AC-007-12)

## Phase 6 — Close

- [ ] **T007-16** Update `docs/20-implementation-status.md`.
