# Spec 010 — Dashboard and Money Flow

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 |
| **Owner role** | C: Frontend (+ B for the flow builder) |
| **Depends on** | 007, 008 |
| **Requirements** | FR-050, FR-051, FR-052, FR-053, FR-075, NFR-03, NFR-13, NFR-14, P0-12 |
| **Design** | [`docs/08`](../../08-risk-engine.md) §4.1, §5.1, §5.2; [`docs/11`](../../11-frontend.md) §6.2; [`docs/12`](../../12-design-system.md) §2.3, §6.4; `contracts/policy/categories.v1.yaml` |

## Summary

The home screen answers four questions in one look: how much came in and went out, where the money
went, which months are done, and what needs me. It is a **dashboard**, separate from the tables:
every card links to the table behind it (Documents, Reconciliation, Review, Risk) instead of
repeating it. Below the lists, full-width charts show where the money went, grouped the way the
workspace's accounting framework (IFRS or US GAAP) groups a cash-flow statement: the **money flow**
(revenue by client → bank account → activity → statement line such as cost of sales, payroll or
finance costs), money in and out by month, and the cash-flow statement as a waterfall. Every band and
bar opens the bank lines it is made of.

## User stories

### US-010-1: The dashboard

- **AC-010-1** `/` shows, for a period picker (one month, a range of at most 12 months, or a year;
  default: the current month in the workspace's time zone; the choice is kept in the address as
  `?period=`):
  KPI cards for money in, money out, net, auto-match rate, open review items and documents waiting,
  each with the change against the previous period of equal length; the month strip; the money flow;
  up to 5 alerts; and a preview of the top 5 review items. Data from `GET /api/dashboard?period=`.
- **AC-010-2** Each KPI and card links to its table with the filter applied (e.g. "Open review items"
  → `/review?month=…`; a month in the strip → `/months/2026-03`; an alert → `/risk/:findingId`).
- **AC-010-3** Empty states guide the next action: no documents → "Upload a bank statement, invoices
  or a ledger export"; months collecting → "Add the bank statement for March to reconcile it".
- **AC-010-4** Layout per window class ([`docs/12`](../../12-design-system.md) §5): status sentence,
  figures, then "Needs you" and "Risk" (side by side from 980 px of content, stacked below), then the
  charts. **Charts never share a row:** each chart panel takes the full content width (next to the
  navigation, never under it) and panels stack in one column. Each chart has three drawings chosen by
  the panel's width (compact below 640 px, medium to 959 px, wide from 960 px), so its text stays 12 to
  15 px; on phones the money flow becomes ranked bars of the top sources and uses.

### US-010-2: Where did the money go?

- **AC-010-5** `GET /api/money-flow?period=&view=&framework=&accountId=&showTransfers=` returns nodes
  and links built by `build_money_flow` ([`docs/08`](../../08-risk-engine.md) §5.1). `view=STATEMENT`
  (default): top 5 clients + "Other clients" + "Cash sales deposited" and the other inflow lines →
  each bank account → activity under the framework (operating, investing, financing, kept) → statement
  line in the framework's wording. `view=COUNTERPARTIES`: sources → accounts → suppliers, payroll, rent
  and utilities, tax, loan payments, owner drawings, other spending and "Kept in the account". Held
  (possible duplicate) lines excluded; Σ in = Σ out + kept per account in both views.
- **AC-010-6** The Sankey (d3-sankey layout, our SVG) shows labels and amounts on every node; hovering
  or focusing a band shows its amount and line count; clicking a band or node opens a
  drawer (a sheet on phones) listing the bank lines behind it (`GET /api/bank-lines?flow=<linkId>`),
  with their total and a link from each line to its month.
- **AC-010-7** A table alternative ("Show as table") lists every link with source, target, amount and
  count (NFR-08); colours come from tokens; sources and uses are told apart by position and label,
  not colour alone.
- **AC-010-8** On S1 the top sources and uses equal `truth.json.expectedFlows`.
- **AC-010-12** The chart section has a framework switch (IFRS, US GAAP; default
  `profile.accountingFramework`) and the money flow has four views: **Flow** (the Sankey), **Bars**
  (statement lines grouped by activity), **Table** and **By client and supplier**. Switching the
  framework moves interest paid and received between activities, renames lines in that framework's
  wording and shows one sentence under the chart saying what moved; totals never change. Neither
  switch changes the workspace setting.

### US-010-3: The month strip

- **AC-010-9** One chip per month with: statement present per account (or "missing"), state
  (`COLLECTING`, `NEEDS_REVIEW`, `RECONCILED`), auto-match rate and risk level; it scrolls
  horizontally on phones with snap and fits in one row on desktop for 12 months.

### US-010-4: Fast

- **AC-010-10** `GET /api/dashboard` answers in ≤ 500 ms p95 for S1 (figures and flows are
  precomputed by the month workflow; the period is an aggregation of months).
- **AC-010-11** Lighthouse (mobile) on the dashboard: performance ≥ 85, accessibility ≥ 95.

### US-010-5: Months and the cash-flow statement

- **AC-010-13** "Money in and out by month" shows grouped bars per month with the net above each pair,
  and a second view "Net and balance" (net bars with the month-end balance as a dashed line); a month
  with a Critical or High risk is outlined. Data from `GET /api/cash-flow?period=&framework=`.
- **AC-010-14** "Cash-flow statement" draws opening balance → net operating → net investing → net
  financing → closing balance as a waterfall in the chosen framework, with a link to the month table.
  When `opening + Σ activities ≠ closing`, the chart is replaced by a sentence naming the missing
  statement or month.

## Out of scope

Custom dashboards, exports of charts, forecasting, budgets.
