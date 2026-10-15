# Tasks 019 — Current UI and mock parity

- [x] **T019-01** Audit screens and task claims; add route/status inventory to mock index. (AC-019-1, AC-019-5)
- [x] **T019-02** Refresh dashboard and assistant mocks, externalized words, accessible composer and
  preview states; add semantic parity and responsive browser checks. (AC-019-2, AC-019-4)
- [x] **T019-03** Refresh document/ledger, month, all-months and review/correction references; retain
  planned features with explicit status. Verify reference screenshots. (AC-019-3, AC-019-4)
- [x] **T019-04** Strengthen UI-sync rule, update docs/status and task gaps, run full gates and commit
  reviewed mocks and browser baselines. (AC-019-4, AC-019-5)
- [x] **T019-05** Risk page parity: `contracts/design/fixtures/risk.json` feeds `design/mocks/risk.html` and
  the browser check (`risk.spec.ts`, `/preview/risk`); `RiskPage` reuses the dashboard's `MonthStrip`, groups
  findings per month (worst month first) with the Where column, held copies read "Held", the clean months
  are named at the foot. Built 15 Oct 2026. (AC-019-4, AC-008-7, AC-008-10)
