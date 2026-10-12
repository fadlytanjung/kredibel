# Tasks 010 — Dashboard and Money Flow

## Phase 1 — Data

- [x] **T010-01** **TDD** `money_flow.py`: both views, framework classes and wording from `categories.v1.yaml`, balance per account, kept vs taken from balance, held lines excluded, top-5 grouping, transfers option, stable link IDs. (AC-010-5, AC-010-12)
- [x] **T010-01b** **TDD** `cash_flow.py`: months series, by activity, by line, the opening-to-closing check. (AC-010-13, AC-010-14)
- [x] **T010-02** Period aggregation; `InsightService`; routes; `flow=` filter. (AC-010-1, AC-010-5, AC-010-6)
  A period's flow is rebuilt from its lines (its five largest clients are not the sum of each
  month's). Open review items and the review preview wait for the review queue (spec 009).
- [ ] **T010-02a** `build_flows` node writes the month's own flow to `months.flows` (≤ 40 links), after
  the spec 009 changes to `month_nodes.py` land. (AC-010-10)
- [ ] **T010-03** Latency test on S1 data in the emulator. (AC-010-10)

## Phase 2 — UI

- [ ] **T010-04** `KpiCard`, `MonthStrip`, `AlertList`, `ReviewPreview` with stories. (AC-010-1, AC-010-9)
- [ ] **T010-05** `ChartPanel`, `SegmentedControl`, `SankeyChart`, `StatementBars`, `FlowTable`, `FlowList`, `MonthBars`, `CashFlowWaterfall`; keyboard focus on bands; three drawings per chart; stories at 390, 834 and 1440. (AC-010-6, AC-010-7, AC-010-12…14)
- [ ] **T010-06** `DashboardPage` at three widths; empty states; links with filters; visual tests and Lighthouse. (AC-010-2…4, AC-010-11)

## Phase 3 — Scenario and close

- [ ] **T010-07** Scenario test: S1 top sources and uses. (AC-010-8)
- [ ] **T010-08** Update `docs/20-implementation-status.md`.
