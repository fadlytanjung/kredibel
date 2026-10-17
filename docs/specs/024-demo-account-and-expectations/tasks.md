# Tasks 024 — Demo account, expectations and the transactions table

## A. Demo books that prove it (P0)

- [x] **T024-01** **TDD** `kredibel-synth demo --window`: keep the window's files and ledger rows.
  (AC-024-1) Built 17 Oct 2026: `--window 2026-08:2026-10` (window.py) and `--pack` (pack.py, one
  folder of 39 files with its upload order); the upload maps the bank account to ledger 1110.
- [x] **T024-02** Rebuild the demo company from August–October with the bank account mapped to the
  ledger cash account; measure "Matched by Kredibel" per month. (AC-024-2) Built 17 Oct 2026 with
  bank-to-ledger matching (spec 023, T023-12): August 91.7 % (CRITICAL: A01, A02, M01–M04, X09),
  September 100 % (R02 twice), October 100 % (X08 HIGH); the scanned copy held (D03).

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

- [x] **T024-06** Transactions page from the bank lines with their classes, subledger and confidence;
  mock. (AC-024-6) Built 17 Oct 2026: `GET /api/transactions?month=` (`domain/transactions.py`), the
  Transactions menu and tour step, the row drawer, mocks transactions and transaction, parity in
  transactions.spec.ts; every shell baseline refreshed for the new menu item.
- [x] **T024-07** Update `docs/20`, `docs/24`, README.
- [x] **T024-08** After the first demo (17 Oct 2026): an owner whose workspace has no goal (a new
  workspace, a fresh demo copy after a reset) is asked it before any page; Skip records Keep my
  books; Settings › Profile shows the goal and changes it; the expectations panel shows while the
  goal is Check what I expect; Transactions shows ten rows a page. (AC-024-4, AC-024-6)
- [x] **T024-09** The demo video and the submission pack (17 Oct 2026): `make video` voices
  `tools/video/narration.json` (ElevenLabs), records the story on production with the demo account
  (`frontend/tests/video/demo.spec.ts`: screencast frames, cursor and captions, loading cut) and cuts
  it (`tools/video/edit.py`): 3:13, as the 3–4 minute rule asks; `docs/submission/` holds the rules,
  the brief description, the pitch-deck content, the judges' walkthrough and the day-of checklist.
- [x] **T024-10** **TDD** The demo at a real business's volume: `kredibel-synth demo --per-month 100`
  (about 100 documents a month: more sales invoices, eight more clients, five more suppliers,
  receipts half photos; the planted cases unchanged; a bank journal keeps its distance from its line
  through the shift); the demo template rebuilt from 300 documents, 10 read at a time. (AC-024-1,
  AC-024-2) Built 17 Oct
  2026 (`test_volume.py`, `test_months_to_reconcile.py`, `test_workspace_copier_files.py`): the
  template holds 300 documents (117 sales and 77 purchase invoices, 102 receipts, three statements,
  the ledger), 295 of 310 bank lines matched automatically (95.2 %, 92.2 %, 98.0 %) and only the
  planted findings open; a reset copies it in about 40 s (records as stored, 64 file threads); a
  late July invoice reconciles August again; a model's guessed category gives way to its match.
