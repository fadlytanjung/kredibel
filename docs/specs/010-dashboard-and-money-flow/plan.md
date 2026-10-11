# Plan 010 — Dashboard and Money Flow

## Backend

| File | Content |
|---|---|
| `domain/money_flow.py` | `build_money_flow(lines, accounts, counterparties, period, view, framework, options)`; pure; link IDs stable |
| `domain/cash_flow.py` | `build_cash_flow(months, framework)`: months series, by activity, by line, opening-to-closing check |
| `domain/categories.py` | loads `categories.v1.yaml`: statement line, class and wording per framework |
| `domain/figures.py` | period aggregation from months (sum or recompute) |
| `agents/nodes/month_nodes.py` | `build_flows` writes `months.flows` (≤ 40 links) |
| `services/insight_service.py` | dashboard (KPIs with previous period, alerts from findings, review preview), money flow for a period (merge of months' flows) |
| `api/dashboard.py`, `api/money_flow.py`, `api/cash_flow.py` | routes of [`docs/10`](../../10-api-contract.md) §2.7 |
| `api/books.py` | `flow=` filter on bank lines resolves a link ID to its query |

## Frontend

| File | Content |
|---|---|
| `pages/DashboardPage.tsx` | layout per window class |
| `widgets/KpiCard.tsx`, `MonthStrip.tsx`, `AlertList.tsx`, `ReviewPreview.tsx` | cards |
| `widgets/MoneyFlow/` | `SankeyChart.tsx` (d3-sankey layout → SVG), `StatementBars.tsx`, `FlowTable.tsx`, `FlowList.tsx` (phones), `FlowLinesDrawer.tsx` |
| `widgets/CashFlow/` | `MonthBars.tsx` (in and out, net and balance), `CashFlowWaterfall.tsx` |
| `shared/ui/ChartPanel.tsx`, `SegmentedControl.tsx` | full-width panel with compact, medium and wide drawings; view and framework switches |
| `shared/ui/PeriodPicker.tsx` | month, quarter, all |

## Constitution check

P3 ✔ (every band opens its lines) · P2 ✔ (flows computed by code) · NFR-08 ✔ (table alternative)
