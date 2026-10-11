# Spec 009 — Review Queue

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 |
| **Owner role** | C: Frontend + B: Risk engine (item sync, actions) |
| **Depends on** | 005, 006, 007, 008 |
| **Requirements** | FR-012 (decisions), FR-033, FR-034, NFR-05, NFR-13, P0-10 |
| **Design** | [`docs/08`](../../08-risk-engine.md) §7; [`docs/10`](../../10-api-contract.md) §2.5, §4; [`docs/11`](../../11-frontend.md) §6 |

## Summary

AI does most of the matching; the rest lands in **one queue**. Each item says what is wrong, shows
the evidence, suggests a fix, and offers only the actions that make sense for it. Resolving an item
is audited and re-reconciles its month. The queue works well on a phone: one item at a time, big
targets, swipe-free.

## User stories

### US-009-1: One queue for every exception

- **AC-009-1** `sync_review_items` creates and closes items of the eight kinds of
  [`docs/08`](../../08-risk-engine.md) §7 with deterministic IDs, so a re-run never duplicates an item;
  an item whose cause disappeared (e.g. the missing invoice was uploaded) closes as `RESOLVED` with
  `resolvedBy: system`.
- **AC-009-2** `/review` lists open items, highest priority first (possible duplicates and items of
  `HIGH`/`CRITICAL` months first), with counts per kind and filters by kind and month; the navigation
  badge shows the open count.
- **AC-009-3** A month without a statement creates no `UNMATCHED_DOCUMENT` items; its documents show
  "Waiting for the bank statement".

### US-009-2: Fix an item

- **AC-009-4** `/review/:itemId` (a side panel on desktop, a full screen on phones) shows the subject
  records, the evidence (page crop with the value highlighted) and the suggestion: candidates with
  score and reasons for matches, both readings for a value, the proposed type or ledger mapping with
  parsed sample rows, both documents side by side for a possible duplicate.
- **AC-009-5** Only the actions allowed for the kind are offered ([`docs/10`](../../10-api-contract.md)
  §4); `POST /api/review-items/{id}/resolve` validates the action (`422 ACTION_NOT_ALLOWED` with
  `allowedActions`), amounts for a manual match (`422 MATCH_AMOUNT_MISMATCH`), and the reason for
  ignore (`422 REASON_REQUIRED`); a resolved item → `409 ITEM_ALREADY_RESOLVED`.
- **AC-009-6** A resolution stores the decision as an input to reconciliation, writes an event, marks
  the month dirty and enqueues a month run; the item shows "Updating March…" until the run finishes.
- **AC-009-7** After resolving, the next item opens automatically ("Next: 5 left"); keyboard: `J`/`K`
  next and previous, `Enter` for the primary action.

### US-009-3: The numbers that matter

- **AC-009-8** On S1 the queue holds only the items `truth.json` expects (the ambiguous February pair,
  the June deposit missing from the ledger, and the not-yet-due invoice shows no item); resolving them
  takes the months to `RECONCILED`.
- **AC-009-9** On S3, confirming the four possible duplicates leaves the figures equal to S1's;
  rejecting one adds its values back.

## Out of scope

Roles and sign-off (013 P1, 015), bulk actions (later), comments and assignment (later).

## Edge cases

- Two people resolve the same item at once: the second gets `409` and the UI refreshes the item.
- A correction that changes a statement amount re-runs the document's arithmetic checks too.
