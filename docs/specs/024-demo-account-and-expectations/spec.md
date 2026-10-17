# Spec 024 — Demo account, expectations and the transactions table

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 (A, B), P1 (C, D) |
| **Owner role** | A: Synthetic data, B: Backend, C: Frontend |
| **Depends on** | 002 (synthetic data), 007 (reconciliation), 013 (workspaces), 021 (demo company) |
| **Requirements** | FR-007, FR-010, FR-013 |
| **Design** | [`docs/18`](../../18-synthetic-data.md), [`docs/24`](../../24-submission-checklist.md); mocks `welcome.html`, `transactions.html` |

## Summary

Testers on 16–17 Oct 2026 found the demo not convincing: the demo company and the uploaded demo pack
had "Matched by Kredibel" at 31–43% a month, because the bank account was never mapped to the
ledger's cash account (so no bank line could match a ledger entry) and many lines had no document;
and anyone who wanted to try Kredibel needed a Google account. This spec gives Kredibel a demo that
proves it: **new synthetic books for August–October 2026** with at least 85% of bank lines matched
automatically and a few planted findings; a **demo account** with a username and password whose
workspace a script or the API resets; a **first page after onboarding** that asks what the person
wants (bookkeeping, or checking what they expect against what the documents show) and, for the
second, compares their expected money in and out per month with the reconciled figures; and a
**transactions table**, one row per bank line with its classifications and confidence.

## Acceptance criteria

- **AC-024-1** `kredibel-synth demo --shift-months 5 --window 2026-08:2026-10 --pack` keeps the
  books' August–October 2026 (statements, invoices, receipts, the ledger rows of those months) and
  writes one folder to upload with the scenario files that fall in the window: an edited statement
  (August, CRITICAL), a scanned copy of an August invoice (held), two unpaid supplier invoices
  (September) and a diverted supplier payment (October, HIGH).
- **AC-024-2** The demo company built from them maps its bank account to the ledger's cash account,
  and each month has "Matched by Kredibel" of at least 85%.
- **AC-024-3** A demo account signs in with an email and password (no Google account); its
  workspace is a copy of the demo company; `make demo-account` creates or resets it and
  `POST /api/workspaces/demo/reset` lets the demo user reset it; `docs/25-demo.md` says how anyone can use it.
- **AC-024-4** After onboarding, a page with no navigation asks the person's goal: keep the books
  (goes to the dashboard) or check expectations, where they write the money in and out they
  expect for one or more months; the goal and expectations are stored on the workspace.
- **AC-024-5** For each expected month, the dashboard shows expected against reconciled money in
  and out (within 5%: as expected; otherwise the difference) with links to the month, its
  transactions and its documents; it never says the person's expectation is wrong or right.
- **AC-024-6** A Transactions page lists every bank line in a table: date, description,
  counterparty, amount, category, IFRS and US GAAP cash-flow class, P&L subledger, category
  confidence, reading agreement, match state and document.

## Out of scope

Finding which documents are missing from an expectation; changing a person's expectation; demo
accounts per visitor.
