# Plan 004 — Analysis Orchestration

## Spike first (S2, ≤ 1.5 h)

Minimal FastAPI app on Cloud Run with ADK 2.11: a `Workflow` whose root is a dynamic `@node`
orchestrator calling two child nodes via `ctx.run_node` (one function node, one `Agent` with
`output_schema` on `MODEL_FAST`) and `asyncio.gather`. Confirm: import paths (`node`, `Context`,
`JoinNode`), `Runner`/`App` construction, how the input message reaches the root node, event
consumption, and Agent Platform auth via ADC on the global endpoint. Record the findings in
[`docs/02`](../../02-research.md) §6 and fix the skeleton in [`docs/06`](../../06-agent-design.md) §2.3.

**Fallback if ADK blocks:** keep the node factories and the `case_pipeline(deps)` interface; implement
the orchestrator with plain `asyncio`, and log a deviation in `docs/20`.

## Backend

| File | Content |
|---|---|
| `domain/models/run.py` | `Run`, `RunStage`, `RunStatus`, stage names constant (single source for UI order) |
| `ports/task_queue.py` | `TaskQueue.enqueue_analyze(org_id, case_id, run_id)` |
| `adapters/cloud_tasks_queue.py` | Cloud Tasks HTTP task, name `run-{runId}`, OIDC token (`service_account_email=TASKS_INVOKER_SA`, `audience=WORKER_URL`), ignore `AlreadyExists` |
| `adapters/inline_task_queue.py` | schedules `AnalysisService.run_case_pipeline` with `asyncio.create_task` (local only) |
| `services/analysis_service.py` | `start_run` (transactional status change + run doc + event + enqueue) and `run_case_pipeline` (idempotency/stale checks, runner, failure mapping) |
| `agents/deps.py` | `PipelineDeps` (repo, blob store, gateways, settings, clock, progress reporter) |
| `agents/progress.py` | `ProgressReporter`: `stage_started/finished/failed`, `doc_status`, `case_progress(pct, message)` writing to Firestore with a 300 ms debounce |
| `agents/workflows/case_pipeline.py` | `build_case_pipeline(deps)` per docs/06 §2.3 |
| `agents/nodes/case_nodes.py`, `doc_nodes.py` | **stub** factories for every node; each reports progress and returns a small summary |
| `api/analysis.py` | `POST /analysis-runs`, `GET /analysis-runs/{runId}` |
| `api/tasks.py` | `POST /tasks/analyze-case` (worker only) |

Progress percentages: documents phase 0–60% (weighted by document count), case phase 60–100% in fixed
steps per node.

## Frontend

| File | Content |
|---|---|
| `shared/firebase/listeners.ts` | `useCaseLive`, `useRunLive`, `useDocumentsLive` with polling fallback |
| `features/start-analysis/` | button with disabled reasons; mutation; error mapping (409s) |
| `widgets/PipelineProgress/` | `Stepper` of stages + per-document rows; `aria-live` announcements |
| `widgets/CaseHeader/` | status badge updates live; FAILED banner + retry |

## Constitution check

P2 ✔ (no model logic yet) · P4 ✔ (worker IAM-only; stale/idempotency guards) · P7 ✔ (Cloud Tasks,
Cloud Run, ADK) · P9 ✔ (end-to-end skeleton before real nodes)
