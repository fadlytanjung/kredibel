# Plan 010 — Dashboard and Money Flow

## Backend

| File | Content |
|---|---|
| `domain/money_flow.py` | `build_money_flow(lines, accounts, counterparties, period, view, framework, options)`; pure; link IDs stable |
| `domain/cash_flow.py` | `build_cash_flow(months, framework)`: months series, by activity, by line, opening-to-closing check |
| `domain/categories.py` | loads `categories.v1.yaml`: statement line, class and wording per framework |
| `domain/period.py` | a period (month, quarter, year, range, recent, all) and the previous one of equal length |
| `agents/nodes/month_nodes.py` | `build_flows` writes `months.flows` (≤ 40 links) |
| `services/insight_service.py` | dashboard (KPIs with previous period, alerts from findings, review preview), money flow and cash flow of a period rebuilt from its lines (a period's five largest clients are not the sum of each month's) |
| `api/insights.py`, `api/bank_lines.py` | the three routes; `flow=` on bank lines rebuilds the flow and returns the link's lines |

## Frontend

| File | Content |
|---|---|
| `pages/DashboardPage.tsx` | layout per window class |
| `widgets/KpiCard.tsx`, `MonthStrip.tsx`, `AlertList.tsx`, `ReviewPreview.tsx` | cards |
| `widgets/MoneyFlow/` | `SankeyChart.tsx` (d3-sankey layout → SVG), `StatementBars.tsx`, `FlowTable.tsx`, `FlowList.tsx` (phones), `FlowLinesDrawer.tsx` |
| `widgets/CashFlow/` | `MonthBars.tsx` (in and out, net and balance), `CashFlowWaterfall.tsx` |
| `shared/ui/ChartPanel.tsx`, `SegmentedControl.tsx` | full-width panel with compact, medium and wide drawings; view and framework switches |
| `shared/ui/PeriodPicker.tsx` | month, quarter, all |

## Dependencies

| Package | Version | Why |
|---|---|---|
| `d3-sankey` (frontend) | 0.12.3 | the Sankey layout only (node positions, band widths); we draw the SVG ourselves; it brings `d3-array` and `d3-shape` |
| `@types/d3-sankey` (frontend, dev) | 0.12.4 | its types |

The bar charts and the waterfall are plain SVG from tokens, with no chart library.

## Constitution check

P3 ✔ (every band opens its lines) · P2 ✔ (flows computed by code) · NFR-08 ✔ (table alternative)
