# ADR-001 — ADK 2.x workflows for orchestration

**Status:** Accepted (pending spike S2) · **Date:** 2026-10-10

## Context

The analysis is a multi-step pipeline with a variable number of documents, two parallel fan-outs per
document (extraction, forensics), a loop (memo redraft), and model calls mixed with deterministic
steps. Competition rules require Google's agent tooling; the team previously used LangGraph.

## Decision

Use **ADK 2.x** (`google-adk` 2.11.x). The root is a `Workflow` whose start node is a dynamic
`@node(rerun_on_resume=True)` orchestrator calling child nodes with `ctx.run_node(...)` and
`asyncio.gather` for fan-out; text reasoning steps are ADK `Agent` nodes with `output_schema`; the
assistant is a conversational `Agent` with tools.

## Alternatives considered

| Option | Why not |
|---|---|
| LangGraph | Not permitted by the competition rules we follow |
| Static ADK graph only (`edges` + `JoinNode`) | Can't express "one branch per uploaded document" without code; we keep static graphs as an option for fixed sub-flows |
| ADK 1.x `SequentialAgent`/`ParallelAgent` | Superseded by 2.x workflows; less control over data passing |
| Plain asyncio | Loses ADK tracing, agent nodes and resumability; kept only as a fallback if S2 fails |

## Consequences

- Node contracts (input/output summaries, idempotency keys) are designed so the orchestrator could be
  swapped for plain asyncio without touching node code.
- Large data never travels through workflow state; Firestore/GCS hold it ([`06`](../06-agent-design.md) §2.3).
- ADK minor upgrades require reading release notes (2.0 introduced breaking changes for custom agents).
