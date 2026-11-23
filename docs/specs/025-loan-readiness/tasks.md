# Tasks 025 — Loan readiness report

## A. The report (P0)

- [x] **T025-01** **TDD** `readiness.v1.yaml` and `domain/readiness.py`: the six checks, the level,
  the totals, months and clients. (AC-025-1, AC-025-2, AC-025-3) Built 23 Nov 2026
  (`test_readiness.py`, 17 tests: each check's thresholds, the level, totals, clients, any order).
- [x] **T025-02** **TDD** `ReadinessService` and `GET /api/readiness`; OpenAPI and generated types.
  (AC-025-1, AC-025-2, AC-025-5) Built 23 Nov 2026 (`test_readiness_api.py`: one reconciled month
  is NOT_READY by HISTORY, an open CRITICAL finding fails with its link and next step, no
  statement gives an empty report, a bad period is a 422).

## B. The page (P0)

- [ ] **T025-03** Loan readiness page, nav item, print layout; fixture, mock, inventory and parity
  spec; shell baselines. (AC-025-4, AC-025-5)
- [ ] **T025-04** Plan and usage, the pricing page and `plans.v1.yaml`: no longer coming soon.
  (AC-025-6)

## C. Record (P1)

- [ ] **T025-05** ADR-028, `docs/03`, `docs/04`, `docs/11`, `docs/20`, README; deploy and check it
  on the demo account.
