# Tasks 004 — Workflows

## Phase 1 — Runs and queues

- [x] **T004-01** Spike S2: ADK 2.11 `Workflow`, `@node`, `ctx.run_node`, `Runner` signatures; record findings in `docs/02` §2.2 and adjust the skeletons.
- [x] **T004-02** **TDD** `services/runs.py`: generation bump and task name in one transaction; debounce delay; quota counting. (AC-004-4, AC-004-11)
- [ ] **T004-03** `adapters/cloud_tasks_queue.py` (cloud + inline). (AC-004-4)
- [ ] **T004-04** `api/tasks.py` with OIDC-only mounting on the worker; idempotent re-delivery. (AC-004-3)

## Phase 2 — Workflows with stubs

- [ ] **T004-05** `stages.py` wrapper: stage record, log binding, span. (AC-004-1, AC-004-12)
- [ ] **T004-06** **TDD** `document_workflow` with stubs: node order, `NEEDS_INPUT` stop and resume, failure → `FAILED` + `E02`. (AC-004-1…3)
- [ ] **T004-07** **TDD** `month_workflow` with stubs: generation check → `SUPERSEDED`; `COLLECTING` vs `RECONCILED`. (AC-004-5, AC-004-7)
- [ ] **T004-08** **TDD** burst test: 10 changes → one effective run. (AC-004-6)

## Phase 3 — Live progress and ops

- [ ] **T004-09** Listeners and `ProgressLine`; runs API. (AC-004-8, AC-004-9)
- [ ] **T004-10** `RUNS_ENABLED`, quotas and the "paused until tomorrow" state. (AC-004-10, AC-004-11)
- [ ] **T004-11** Tracing setup; verify a document run shows as one trace in Cloud Trace. (AC-004-12)

## Phase 4 — Close

- [ ] **T004-12** Update `docs/20-implementation-status.md`.
