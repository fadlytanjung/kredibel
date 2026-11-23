# Spec 025 — Loan readiness report

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 (A, B), P1 (C) |
| **Owner role** | B: Backend, C: Frontend |
| **Depends on** | 007 (reconciliation), 008 (risk), 009 (review queue), 010 (cash flow), 013 (plans) |
| **Requirements** | FR-005, FR-077 |
| **Design** | [ADR-028](../../adr/ADR-028-loan-readiness-is-the-owners-check.md); mock `readiness.html`; policy `contracts/policy/readiness.v1.yaml` |

## Summary

A small business that asks for a loan is asked for its bank statements, its sales and what it owes,
and then waits while someone checks them by hand. Kredibel has already checked them: every page is
read with its evidence, every month reconciled, every risk explained. The **loan readiness report**
turns that into one page the owner can print or save as a PDF for a lender, and, before that, tells
the owner what to fix first: a missing statement, an open risk, decisions still in the review queue.

The report is **the owner's own check of their books, not a credit decision** (ADR-028). Its level
(Ready, Almost ready, Not ready yet) says whether the books are ready to show, never whether a loan
should be given. Every figure and every check is computed by code from the reconciled months and the
policy file; the only model-written words are each month's risk explanation, already grounded by the
month run (spec 008), and shown only when the grounding guard verified it.

## Acceptance criteria

- **AC-025-1** `GET /api/readiness?period=` returns, for the period's months with read bank
  statements (default `recent`, at most `readiness.v1.yaml` `period.maxMonths`), a level
  `READY`, `ALMOST_READY` or `NOT_READY` and six checks (`HISTORY`, `COVERAGE`, `RECONCILED`,
  `FINDINGS`, `REVIEW`, `CASH`), each `PASS`, `WARN` or `FAIL` with its facts. Any `FAIL` makes
  the report `NOT_READY`; otherwise any `WARN` makes it `ALMOST_READY`; otherwise it is `READY`.
  Thresholds come from `contracts/policy/readiness.v1.yaml`, never from code. The same books give
  the same report (pure domain function).
- **AC-025-2** The report's figures are code's: per month money in, money out, net, the closing
  balance, the share matched by Kredibel, the risk level and, when the month run's explanation was
  verified by the grounding guard, that explanation; for the period, the totals, the monthly
  averages, the overall share matched, the largest clients' share of money in, and the read
  documents by type. No figure comes from a model.
- **AC-025-3** Every `WARN` and `FAIL` names its evidence: the months it concerns, and for
  `FINDINGS` each open finding (code, severity, title, month, its next step) with a link to it.
- **AC-025-4** The Loan readiness page (`/readiness`, in the Insight menu) shows the level with one
  sentence, the checks with what to do next, the period's figures, the largest clients and the
  months, and a **Print or save as PDF** action whose print layout leaves out the app's menus. The
  page says it is not a credit decision. It works from 360 to 1600 px and matches the mock
  `readiness.html` (parity spec `readiness.spec.ts`).
- **AC-025-5** A workspace without a read bank statement sees an empty state pointing to Documents.
- **AC-025-6** Plan and usage and the pricing page no longer list the loan readiness report as
  coming soon; it is part of the free trial.

## Out of scope

A link shared with a lender, lender accounts, credit scores or any loan decision, a server-side PDF,
a model-written cover letter, more than one currency in one report.
