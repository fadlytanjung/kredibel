# ADR-007 — Human-in-the-loop as a case state machine

**Status:** Accepted · **Date:** 2026-10-10

## Context

The analyst's decision can come minutes or days after analysis. ADK 2.x supports pausing a workflow
with `RequestInput`, but the Python resume contract is not fully documented, and a paused workflow
needs persistent sessions across Cloud Run instances.

## Decision

The **primary** human-in-the-loop mechanism is an explicit **case state machine** in the domain layer:
the pipeline ends at `READY_FOR_REVIEW`; decisions are guarded transitions (open criticals, role,
reason) executed by `ReviewService` and audited atomically. `RequestInput` is reserved for **in-run
clarifications** (own-account confirmation, P1) and only if spike S3 proves resume works with
Agent Platform Sessions.

## Alternatives considered

| Option | Why not |
|---|---|
| Pause the whole workflow for the decision | Days-long pauses, session persistence and resume semantics are risk we don't need for a demo |
| Decision outside any formal model (if-statements in the API) | Guards scattered; hard to test exhaustively |

## Consequences

- One table-driven test covers every transition and guard.
- The UI's rules are hints; the server is authoritative.
- If S3 passes, clarifications add a visible "agent asks the analyst" moment without changing the
  decision model.
