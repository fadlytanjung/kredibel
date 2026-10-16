# Tasks 018 — Company classifications and profit and loss

- [x] **T018-01** Research, ADR, PRD/traceability, reporting and classification contracts. (AC-018-1…7)
- [x] **T018-02** **TDD** pure classification policy and signed P&L aggregation, exclusions,
  order independence and provenance. (AC-018-3, AC-018-4)
- [x] **T018-03** **TDD** versioned scoped repository, audited classification, API and period
  validation, role/isolation tests. (AC-018-1, AC-018-2, AC-018-4)
- [x] **T018-04** **TDD** deterministic assistant P&L path with period scope and unavailable state.
  (AC-018-6)
- [x] **T018-05** Mocks first, dashboard panel, report/detail and classification UI, assistant links,
  strings, stories, responsive screenshots, visual and behaviour checks. (AC-018-5, AC-018-6)
- [x] **T018-06** UI synchronization rule and generated-mock gate; full checks and status. (AC-018-7)
- [x] **T018-07** **TDD** Correct flow/table drift: preserve signed amounts and cents in the report and assistant chart, separate
  revenue from other income, show losses/reversals with a signed alternative, and make flow nodes
  open their exact contributing entries. Refresh populated/empty/partial mocks, shared synthetic
  fixture, source drawer and responsive visual baselines. (AC-018-3…7) 16 Oct 2026: a net loss is drawn in the flow as a source
  that funds the expenses (the middle is the total expenses, mock `profit-loss-loss.html`,
  `flowData.test.ts`); only reversals keep the signed rows; the panel's tab follows the report shown.
- [x] **T018-08** **TDD** Cash basis from categorized bank lines while no ledger export exists:
  category P&L line and subledger labels in `categories.v1.yaml`, `build_cash_profit_loss`, the
  service's fallback and precedence, the accounts catalog read-only, the assistant's wording.
  (AC-018-8, AC-018-9) Built 16 Oct 2026.
- [x] **T018-09** Cash-basis wording on the dashboard panel, the page and the category table; the
  `profit-loss-cash.html` mock from `contracts/design/fixtures/profit-loss-cash.json`, story and
  browser parity check. (AC-018-8, AC-018-5) Built 16 Oct 2026.
- [x] **T018-10** ADR-027 amendment, PRD (FR-056), traceability, `docs/08` §4.1, `docs/10`, `docs/11`
  and the status. Built 16 Oct 2026.
