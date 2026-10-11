# Plan 009 — Review Queue

## Backend

| File | Content |
|---|---|
| `domain/review_items.py` | item rules per kind, priority, deterministic keys, kind → allowed actions |
| `agents/nodes/month_nodes.py` | `sync_review_items` |
| `services/review_service.py` | `resolve(principal, item_id, action)`: validation, decision storage, event, mark dirty, enqueue |
| `api/review_items.py` | routes of [`docs/10`](../../10-api-contract.md) §2.5 |

Decisions are stored where `reconcile_month` reads them: manual matches in `matches` (`MANUAL`),
rejections as `REJECTED` matches, corrections on the record (`correctedBy`, original in `raw`),
duplicate decisions on the document, ignores on the item.

## Frontend

| File | Content |
|---|---|
| `pages/ReviewPage.tsx` | queue with counts and filters; split view on expanded and larger |
| `features/review/ItemPanel.tsx` | per-kind bodies: `MatchCandidates`, `ValueCorrection`, `DuplicateCompare`, `TypeChoice`, `LedgerMappingForm`, `IgnoreWithReason` |
| `features/review/useNextItem.ts` | auto-advance and keyboard shortcuts |

## Constitution check

P5 ✔ (a person resolves exceptions) · P3 ✔ (evidence in every item) · P2 ✔ (items created by code)
