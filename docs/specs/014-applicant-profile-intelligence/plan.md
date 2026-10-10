# Plan 014 — Applicant Profile Intelligence

## Approach

Two pure modules do the thinking (`counterparties.py`, `profile_suggestions.py`); two nodes run them
after reconciliation; one service applies analyst decisions. The model's only new job is to return a
clean counterparty name and kind inside the categorization call it already makes, so there is **no
extra LLM call** and no extra cost per run beyond a few output tokens.

## Backend

| File | Content |
|---|---|
| `domain/counterparties.py` | name normalization, merge by `token_set_ratio ≥ 90`, role rules (docs/08 §4.3), totals, shares, facts `client_count`, `top_client_share` |
| `domain/profile_suggestions.py` | inputs: statement/invoice metadata with provenance, counterparties, profile, rejected suggestion IDs → suggestions with confidence, basis, evidence, deterministic IDs, `CONFLICT` detection |
| `domain/forensics/profile_checks.py` | `X05` (moved from cross-document checks, extended to aliases and declared holders), `X06`, `X07` (P1), `B07` (P1) |
| `domain/categorize.py` | related-party precedence step (P1) |
| `agents/llm/schemas.py` | `CategorizationItem` gains `counterparty_name`, `counterparty_kind` |
| `agents/prompts/categorize_transactions.md` | version bump; asks for the cleaned name and kind |
| `agents/nodes/case_nodes.py` | `build_counterparties`, `build_applicant_profile` |
| `services/applicant_service.py` | `decide_suggestion` (accept writes the profile + `orgPrivate` hash in one transaction; events; counters) |
| `api/applicants.py` | suggestions and events endpoints; `api/counterparties.py` |
| `adapters/firestore_repo.py` | counterparties (chunked upserts), suggestions (create-if-absent), applicant events, `orgPrivate/{orgId}/accountHashes` |
| `tasks/prefill.py` (P1) | upload-time page-1 read via the same `read_page` node and cache |

## Frontend

| File | Content |
|---|---|
| `widgets/ApplicantPanel/` | profile view + edit (reuses the onboarding form from 003) |
| `widgets/SuggestionsPanel/` + `shared/ui/SuggestionCard.tsx` | value, confidence, basis, evidence chip, Accept/Reject, conflict layout |
| `widgets/CounterpartiesPanel/` | role tabs, table, link to filtered Cash flow |
| `features/decide-suggestion/` | mutation + optimistic badge update; roles picker for related parties |
| `entities/suggestion/`, `entities/counterparty/` | hooks, mappers |
| `pages/CaseWorkspacePage.tsx` | new `applicant` tab with pending-count badge |
| `pages/ApplicantListPage.tsx`, `ApplicantDetailPage.tsx` (P1) | |

## Synthetic data (with spec 002)

`truth.json` gains `applicant` (profile as onboarded in the scenario), `expectedSuggestions` and
`expectedCounterparties`; a fixture adds an undeclared second account; S7 (P1) adds owner transfers
labelled as sales.

## Constitution check

P2 ✔ (roles, shares and suggestions are code; the model only cleans names) · P3 ✔ (every suggestion
has evidence) · P4 ✔ (documents cannot write the profile) · P5 ✔ (analyst accepts) · P8 ✔ · P10 ✔

## Risks

- Counterparty names in real descriptions are messy → the categorizer cleans the long tail; evals
  measure merge precision (E-CPTY in docs/15).
- Suggestion fatigue → at most 5 key-party suggestions per role per run; confidence shown; rejected
  values never return.
