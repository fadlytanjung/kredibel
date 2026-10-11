# Plan 004 — Workflows

## Backend

| File | Content |
|---|---|
| `agents/workflows/document_workflow.py` | dynamic `@node` orchestrator ([`docs/06`](../../06-agent-design.md) §2.2) with stub nodes |
| `agents/workflows/month_workflow.py` | static graph ([`docs/06`](../../06-agent-design.md) §3) with stub nodes |
| `agents/nodes/doc_nodes.py`, `month_nodes.py` | node factories; stubs return fixed summaries until 005–008 |
| `agents/deps.py` | `PipelineDeps` (repositories, gateways, clock, settings) |
| `agents/stages.py` | node wrapper that records a stage, binds log context and opens a span |
| `services/runs.py` | `start_document_run`, `start_month_run(month)`: generation bump + enqueue in one transaction |
| `services/month_service.py` | `mark_dirty(months, reason)` used by every service that changes month data |
| `adapters/cloud_tasks_queue.py` | named tasks, schedule time, OIDC token; `inline` mode for local dev and tests |
| `api/tasks.py` | the two worker endpoints; idempotency and generation checks |
| `observability/tracing.py` | ADK OTel exporters to Cloud Trace ([`docs/17`](../../17-observability.md) §2) |

## Frontend

| File | Content |
|---|---|
| `entities/document/useDocumentLive.ts`, `entities/month/useMonthLive.ts` | Firestore listeners |
| `shared/ui/ProgressLine.tsx` | "Reading page 3 of 18" and month states |

## Constitution check

P2 ✔ (orchestration deterministic) · P7 ✔ (Cloud Tasks, Cloud Run, ADK) · P9 ✔ · P10 ✔ (skeleton tests)

## Risks

- ADK 2.x dynamic workflow API details (spike S2): keep the orchestrator thin so a fallback to a plain
  async function with the same stage wrapper is a one-file change.
