# ADR-007 — Human-in-the-loop as a review queue, not paused workflows

**Status:** Accepted · **Date:** 2026-10-10 · **Revised by:** [ADR-015](ADR-015-scope-finance-workspace-not-loan-review.md)
(replaces the loan case's decision state machine)

## Context

AI matches most bank lines, but not all: 15–20% need a person (an ambiguous payment, a missing
invoice, a possible duplicate, an uncertain value, a new ledger layout). These decisions come minutes
or days after a document is read, possibly from a phone. ADK 2.x can pause a workflow with
`RequestInput`, but a paused workflow needs persistent sessions across Cloud Run instances, and a
month would be blocked while it waits.

## Decision

The human-in-the-loop mechanism is a **review queue** of typed items, created and closed by code
(`sync_review_items`, [`08`](../08-risk-engine.md) §7). Workflows **never pause**: a document that
needs a type or a ledger mapping stops in `NEEDS_INPUT`; a month publishes its matches and open items.
A person resolves an item with an action allowed for its kind ([`10`](../10-api-contract.md) §4); the
decision is stored as an **input** to reconciliation, audited atomically, and the month runs again.
`RequestInput` is not used.

## Alternatives considered

| Option | Why not |
|---|---|
| Pause the month workflow until a person answers | Long pauses, session persistence and resume semantics; one open item would block the whole month |
| Fix data by editing records directly | No audit, and the next re-run would overwrite the fix |
| A free-form task list | No allowed-actions table, so wrong fixes and untestable rules |

## Consequences

- One table-driven test covers every (kind, action) pair; the UI only offers allowed actions.
- Re-runs are safe: user decisions are inputs, never side effects, so order independence holds.
- The queue is the place where roles matter (P1): accountants fix, reviewers decide duplicates and
  dismissals ([`14`](../14-security-and-compliance.md) §4.2).
