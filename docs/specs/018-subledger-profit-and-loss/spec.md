# Spec 018 — Company classifications and profit and loss

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P1, requested continuation on 14 October 2026 |
| **Owner role** | B + C + A |
| **Depends on** | 010 dashboard, 011 assistant UI; ledger population follows 005 |
| **Requirements** | FR-054, FR-055, FR-070, NFR-08 |
| **Design** | [ADR-027](../../adr/ADR-027-subledgers-and-company-profit-loss.md) |

## Summary

A business can map its general-ledger accounts to company P&L lines and subledger families, see
an accrual management P&L on the dashboard, and ask the assistant for the same report. Subledger
families describe where the entries originated; income and expense accounts determine profit.
IFRS/US GAAP remain cash-flow presentation choices. This management report does not claim statutory
compliance. It reports only imported posted entries, never bank cash or invoice totals as profit.

## User stories

### US-018-1: Classify my company's accounts

- **AC-018-1** Given imported accounts, when an owner or accountant confirms a classification,
  then its P&L line and subledger family are saved for that workspace with actor, time and audit event.
  Suggestions and unclassified accounts have no effect on reported profit; no model writes a decision.
- **AC-018-2** Given identical account codes in different workspaces, when reports or classifications
  are requested, then the authenticated workspace alone supplies the data. Viewers cannot classify.

### US-018-2: Understand company performance

- **AC-018-3** Given posted GL entries and confirmed classifications, when a period is selected,
  then code computes revenue, cost of sales, gross profit, operating expenses, operating profit,
  other income, finance costs, income tax and net profit using Decimal. Credit balances increase
  revenue; debit balances increase expenses; reversals reduce their own line.
- **AC-018-4** Given balance-sheet accounts, held duplicates, draft entries, currency mismatches,
  unclassified accounts or an unbalanced ledger, when the report is built, then exclusions and
  gaps are explicit. No data means unavailable, not zero profit; incomplete data means partial.
  Each subtotal exposes the contributing entry IDs and source document rows. Input order is irrelevant.
- **AC-018-5** Given a report, when opened on the dashboard or its detail page, then the full-width
  chart, signed amounts and table alternative agree. Detail groups accounts by subledger and links
  to source documents. Loading, empty, error and partial states work from 360 to 1600 px.

### US-018-3: Ask about profit

- **AC-018-6** Given a P&L question scoped to a month (or an explicit month/quarter/year), when the
  assistant answers, then it uses the same read-only report and decimal strings, with fact IDs,
  coverage and a report link. Unavailable data produces no invented profit. P&L requests do not
  invoke the model to calculate or summarize ungrounded amounts.

### US-018-4: Keep design and code together

- **AC-018-7** Given a UI change, when the quality gates run, generated mocks and shared CSS must
  match their sources. The rule requires updating the affected mock, implementation, strings,
  stories and screenshots together; this release demonstrates it for dashboard, P&L and assistant.

## Out of scope

Posting journals, tax advice, consolidation, FX conversion, statutory IFRS/GAAP statements,
subledger-to-control-account certification, replacing the ledger import workflow of spec 005,
or completing Sessions/Memory Bank and retrieval from spec 011. Until ledger import is available,
production workspaces with no ledger entries show the unavailable state. Synthetic tests and stories
exercise populated reports; no demo amounts are inserted into live workspaces.

## Edge cases

Contra accounts and refunds retain their sign. Receivable collections and payable settlements affect
balance-sheet accounts only. Inventory purchases are assets until a cost-of-sales posting occurs.
Posting dates select the reporting period. Missing classifications never default to an expense.
A balanced imported subset alone does not prove that the company has supplied its complete books.
