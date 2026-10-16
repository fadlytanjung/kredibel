# Tasks 024 — Demo account, expectations and the transactions table

## A. Demo books that prove it (P0)

- [x] **T024-01** **TDD** `kredibel-synth demo --window`: keep the window's files and ledger rows.
  (AC-024-1) Built 17 Oct 2026: `--window 2026-08:2026-10` (window.py) and `--pack` (pack.py, one
  folder of 39 files with its upload order); the upload maps the bank account to ledger 1110.
- [ ] **T024-02** Rebuild the demo company from August–October with the bank account mapped to the
  ledger cash account; measure "Matched by Kredibel" per month. (AC-024-2)

## B. Demo account (P0)

- [x] **T024-03** **TDD** Demo account: create or reset by script, reset by API for the demo user;
  `docs/25-demo.md`. (AC-024-3) Built 17 Oct 2026: `POST /api/workspaces/demo/reset` (only
  `DEMO_ACCOUNT_EMAIL`), `make demo-account` (scripts/demo_account.py), docs/25.

## C. Goals and expectations (P1)

- [x] **T024-04** **TDD** Workspace goal and expectations; the comparison with reconciled months.
  (AC-024-4, AC-024-5) Built 17 Oct 2026: `goal`, `expectations` on the workspace (optional
  fields), `domain/expectations.py`, `GET /api/expectations`, tolerance in `reconciliation.v1`.
- [x] **T024-05** Welcome page after onboarding and the dashboard's expectations card; mocks.
  (AC-024-4, AC-024-5) Built 17 Oct 2026: `/welcome` (no navigation), the dashboard's "What you
  expected" panel, mocks welcome, welcome-expect and dashboard-expectations, parity in
  welcome.spec.ts at three widths.

## D. Transactions table (P1)

- [ ] **T024-06** Transactions page from the bank lines with their classes, subledger and confidence;
  mock. (AC-024-6)
- [ ] **T024-07** Update `docs/20`, `docs/24`, README.
