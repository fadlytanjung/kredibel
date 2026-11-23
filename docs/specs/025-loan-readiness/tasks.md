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

- [x] **T025-03** Loan readiness page, nav item, print layout; fixture, mock, inventory and parity
  spec; shell baselines. (AC-025-4, AC-025-5) Built 23 Nov 2026: `ReadinessPage.tsx`,
  `widgets/readiness`, `readiness.json` words, `readiness.html` mock, `ReadinessPage.test.tsx`,
  `readiness.spec.ts` (outline equal to the mock at 390/834/1440, 360/1600 px, axe, print hides the
  menus); 219 visual checks green after the shell baselines were recorded again.
- [x] **T025-04** Plan and usage, the pricing page and `plans.v1.yaml`: no longer coming soon.
  (AC-025-6) Built 23 Nov 2026: the free trial's first highlight names the report.

## C. Record (P1)

- [x] **T025-05** ADR-028, `docs/03`, `docs/04`, `docs/11`, `docs/20`, README; deploy and check it
  on the demo account. Deployed 23 Nov 2026 (`1b8544d`, Cloud Build green); `GET /api/readiness` on
  the demo account: Not ready yet (HISTORY and COVERAGE to settle, FINDINGS to fix, REVIEW 20).
