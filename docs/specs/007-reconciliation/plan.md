# Plan 007 — Categorization and Month Reconciliation

## Backend

First deliver policy-driven candidate scoring as pure value objects in
`domain/reconciliation_policy.py` and `domain/reconcile_scoring.py`, loaded by
`adapters/policy_files.py`. These are transient inputs/results, not Firestore documents. Existing
`rapidfuzz` supplies party similarity; no new dependency. Currency is explicit because the extracted
bank-line model obtains it from the parent statement. The scorer takes the fixed workspace currency
and explicit per-record confirmation of a printed-currency override. A different/unknown printed
currency means no candidate until accepted; amounts are never converted. Overrides are decision
inputs, never inferred from model output. Persistence and the confirmation flow remain T007-06a.
Scoring does not assign, write matches, decide payment states or enable the production pipeline.

ADR-025 adds bank evidence/support and manual attestations. T007-06a must define their OpenAPI
shapes and versioned persistence using `/data-migration` before any write. Keep payment confirmation
and document approval distinct; preserve audit history and never synthesize bank cash. The
temporary skeleton guard keeps months collecting with a note, never falsely reconciled.

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

T007-00 adds `reconciliation.html` via `tools/design/mocks/screens.py`, using the existing kit and
synthetic illustrative amounts independent of the Jan–Jun demo totals. It previews statement-first,
document-first, grouped and split payments, plus manual decision states. The existing edited-March
mock remains the integrity example. React implementation and state stories remain T007-10.

| File | Content |
|---|---|
| `pages/MonthsPage.tsx`, `pages/MonthPage.tsx` | month list and month detail ([`docs/11`](../../11-frontend.md) §6) |
| `features/match/MatchPicker.tsx` | candidates with amounts and difference; confirm |
| `widgets/MatchReason.tsx` | reason codes as plain text |

## Constitution check

P2 ✔ (matching deterministic; the categorizer only labels) · P3 ✔ (reasons on every match) · P5 ✔
(ambiguity goes to a person) · P10 ✔ (property tests)

P1 ✔ (spec precedes implementation) · P4/P6 ✔ (bank evidence does not authenticate uploaded files)
· P7 ✔ (no new service) · P8 ✔ (synthetic examples) · P9 ✔ (P0 only).
