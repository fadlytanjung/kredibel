# Plan 007 — Cash Flow & Reconciliation

## Modules

| File | Responsibility |
|---|---|
| `domain/taxonomy.py` | enums `CashflowClass`, `Category`, `RiskTag`; category → class map |
| `domain/categorize.py` | internal-transfer rule; keyword rule engine (compiled regexes from `categorization-rules.v1.yaml`); merge with model output; precedence |
| `agents/prompts/categorize_transactions.md` + `agents/llm/categorizer.py` | `txn_categorizer` Agent node (`MODEL_LITE`, `CategorizationBatch` output) |
| `domain/metrics.py` | per-month flows, EOD balances, ADB, negative days, aggregates, annuity, DSCR proxy, max supportable, liquidity buffer; `Fact` builder |
| `domain/reconciliation.py` | candidate windows, scoring, single/split/partial matching, greedy deterministic assignment, summary |
| `domain/forensics/casewide.py` | R01, R02, C01, C02, B01, B04 |
| `agents/nodes/case_nodes.py` | real `categorize_transactions`, `compute_cashflow_metrics`, `reconcile_invoices`, `check_behaviour` |
| `adapters/firestore_repo.py` | `update_transaction_categories` (chunked), `put_analysis(runId, partial)`, `update_invoice_match` |
| `api/analysis.py`, `api/transactions.py`, `api/invoices.py` | read endpoints |

## Notes

- Split-payment search is bounded: candidates with `party_score ≥ 0.8` only, combinations of size 2–3,
  max 30 candidates per invoice.
- The categorizer sends only `ref`, date, normalized description, signed amount and counterparty; no
  names of the borrower's owner beyond what is in descriptions; never account numbers.
- Facts are the **only** numbers later nodes (memo) may cite.

## Constitution check

P2 ✔ (all math in `domain/`) · P3 ✔ (facts with inputs; findings with transaction evidence) ·
P7 ✔ · P10 ✔ (metrics equal truth; reconciliation unit tests)
