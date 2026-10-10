# Tasks 004 — Analysis Orchestration

## Phase 0 — Spike

- [ ] **T004-01** Spike S2 (plan §Spike). Record results in docs/02 §6; update docs/06 §2.3 if the API differs.

## Phase 1 — Domain & ports

- [ ] **T004-02** Run models, stage-name constants (ordered), run status enum.
- [ ] **T004-03** **TDD** `case_state`: `DRAFT|INFO_REQUESTED|FAILED → PROCESSING` requires ≥1 document and no active run; `PROCESSING → READY_FOR_REVIEW|FAILED`. (AC-004-2, AC-004-3)
- [ ] **T004-04** `TaskQueue` port + `InlineTaskQueue` + fake that records enqueued tasks.

## Phase 2 — Services (TDD)

- [ ] **T004-05** **TDD** `AnalysisService.start_run`: run doc, case status, `currentRunId`, event, enqueue — in one transaction (enqueue after commit; on enqueue failure revert to previous status and raise). (AC-004-1, AC-004-2)
- [ ] **T004-06** **TDD** `run_case_pipeline` idempotency: finished run → skipped `finished`; stale run → skipped `stale`. (AC-004-6, AC-004-7)
- [ ] **T004-07** **TDD** failure mapping: case-level exception → run/case `FAILED`, event, error fields; document-level exception → document `FAILED`, run continues. (AC-004-8, AC-004-9)

## Phase 3 — Workflow skeleton

- [ ] **T004-08** `ProgressReporter` with debounce; `PipelineDeps`.
- [ ] **T004-09** Stub node factories for every node in docs/06 §3 (each: report started/finished, return summary).
- [ ] **T004-10** `build_case_pipeline(deps)` with semaphore-bounded per-document fan-out and the memo/guard loop (stubs). (AC-004-4, AC-004-5)
- [ ] **T004-11** Scenario test with fakes: S1 seed-1 documents → run `SUCCEEDED`, stages all `DONE`, case `READY_FOR_REVIEW`. (AC-004-4)

## Phase 4 — Adapters & API

- [ ] **T004-12** `CloudTasksQueue` adapter (OIDC token, task name, AlreadyExists ignored).
- [ ] **T004-13** `api/analysis.py` and `api/tasks.py`; worker-only mounting. (AC-004-1)
- [ ] **T004-14** Local inline mode end-to-end with `make dev`. (AC-004-13)
- [ ] **T004-22** **TDD** run quotas (per org per day in Firestore `orgs/{orgId}/usage/{yyyy-mm-dd}` counter, per user per minute in memory) and the `RUNS_ENABLED` kill switch. (AC-004-14, AC-004-15)
- [ ] **T004-23** **TDD** plan checks and page reservation in the run-creation transaction via `EntitlementService` (spec 013); usage actuals and reservation reconciliation in `finalize_run` and on failure. (AC-004-16, AC-004-17)

## Phase 5 — Frontend

- [ ] **T004-15** Firestore listener hooks with polling fallback and "paused" indicator. (AC-004-10, AC-004-11)
- [ ] **T004-16** Start-analysis feature with disabled reasons and 409 handling. (AC-004-1, AC-004-2)
- [ ] **T004-17** PipelineProgress widget (stepper + per-document rows with "Reading page n of m", aria-live). (AC-004-10, AC-004-18)
- [ ] **T004-18** FAILED banner + retry. (AC-004-12)

## Phase 6 — Verify on Cloud Run

- [ ] **T004-19** Deploy; run S1 on the deployed env; observe live progress; re-deliver the task manually (Cloud Tasks "run now" on a copy) to confirm idempotency.
- [ ] **T004-20** `backend/scripts/requeue_run.py --case … --run …` (re-enqueue an existing run; idempotent) for the runbook in docs/16 §9.
- [ ] **T004-21** Update `docs/20-implementation-status.md`.
