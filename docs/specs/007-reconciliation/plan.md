# Plan 007 — Categorization and Month Reconciliation

## Backend

| File | Content |
|---|---|
| `domain/categorize.py` | precedence chain and keyword rules |
| `agents/prompts/categorize_transactions.md` | categorizer prompt; `CategorizationBatch` schema |
| `domain/reconcile.py` | candidate windows, scoring, greedy deterministic assignment, subset sums (≤ 3), user decisions as inputs, payment and match states |
| `domain/figures.py` | month facts and period aggregation |
| `domain/checks/cross_document.py`, `reconciliation.py`, `behaviour.py` | `X0x`, `R0x`, `B0x`, `C02`, `D07` |
| `agents/nodes/month_nodes.py` | `load_month`, `reconcile`, `check_month`, `finalize_month` (writes) |
| `agents/nodes/doc_nodes.py` | `categorize_bank_lines` |
| `services/match_service.py` | manual match (tolerance check, `ALREADY_MATCHED`), unmatch |
| `api/books.py`, `api/months.py`, `api/matches.py` | routes of [`docs/10`](../../10-api-contract.md) §2.3–§2.4 |

## Frontend

| File | Content |
|---|---|
| `pages/MonthsPage.tsx`, `pages/MonthPage.tsx` | month list and month detail ([`docs/11`](../../11-frontend.md) §6) |
| `features/match/MatchPicker.tsx` | candidates with amounts and difference; confirm |
| `widgets/MatchReason.tsx` | reason codes as plain text |

## Constitution check

P2 ✔ (matching deterministic; the categorizer only labels) · P3 ✔ (reasons on every match) · P5 ✔
(ambiguity goes to a person) · P10 ✔ (property tests)
