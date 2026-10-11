# ADR-001 — ADK 2.x workflows for orchestration

**Status:** Accepted (pending spike S2) · **Date:** 2026-10-10

## Context

Kredibel runs two kinds of multi-step work: one per uploaded document (a variable number of pages
read in parallel, then verification, checks and duplicates) and one per month (reconcile, check,
score, explain, build flows and review items), with model calls mixed with deterministic steps.
Competition rules require Google's agent tooling; the team previously used LangGraph.

## Decision

Use **ADK 2.x** (`google-adk` 2.11.x). `document_workflow` is a `Workflow` whose start node is a
dynamic `@node(rerun_on_resume=True)` orchestrator calling child nodes with `ctx.run_node(...)` and
`asyncio.gather` for the per-page fan-out; `month_workflow` is a static graph of nodes (`edges`),
because its shape never changes; text steps are ADK `Agent` nodes with `output_schema`; the Finance
Assistant (P1) is a conversational `Agent` with tools.

## Alternatives considered

| Option | Why not |
|---|---|
| LangGraph | Not permitted by the competition rules we follow |
| Static ADK graph only (`edges` + `JoinNode`) | Can't express "one branch per page" without code; we use a static graph where the shape is fixed (the month) |
| ADK 1.x `SequentialAgent`/`ParallelAgent` | Superseded by 2.x workflows; less control over data passing |
| Plain asyncio | Loses ADK tracing, agent nodes and resumability; kept only as a fallback if S2 fails |

## Consequences

- Node contracts (input/output summaries, idempotency keys) are designed so the orchestrator could be
  swapped for plain asyncio without touching node code.
- Large data never travels through workflow state; Firestore/GCS hold it ([`06`](../06-agent-design.md) §2.2).
- ADK's OpenTelemetry spans give the run graph and Cloud Trace view for free ([`17`](../17-observability.md)).
- ADK minor upgrades require reading release notes (2.0 introduced breaking changes for custom agents).
