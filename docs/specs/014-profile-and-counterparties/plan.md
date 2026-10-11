# Plan 014 — Profile Suggestions and Counterparties

## Backend

| File | Content |
|---|---|
| `domain/counterparties.py` | grouping, role rules, buckets, accounts seen (with hashes from the repository) |
| `domain/profile_suggestions.py` | suggestion rules, confidence, deterministic IDs, conflicts |
| `agents/nodes/month_nodes.py` | `build_counterparties`, `suggest_profile` |
| `services/workspace_service.py` | `decide_suggestion(principal, id, decision)` |
| `api/counterparties.py`, `api/suggestions.py` | routes of [`docs/10`](../../10-api-contract.md) §2.7 |

## Frontend

| File | Content |
|---|---|
| `pages/CounterpartiesPage.tsx`, `pages/CounterpartyPage.tsx` | list and detail |
| `widgets/SuggestionCard.tsx` | dashboard card and settings list with evidence thumbnails |

## Constitution check

P2 ✔ (roles and suggestions by code) · P3 ✔ (evidence) · P5 ✔ (the user accepts or rejects)
