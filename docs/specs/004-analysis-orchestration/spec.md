# Spec 004 — Analysis Orchestration

| | |
|---|---|
| **Status** | Ready (after spike S2) |
| **Priority** | P0 |
| **Owner role** | A: Agents (backend) + C: Frontend (progress UI) |
| **Depends on** | 001, 003, 013 (entitlements) |
| **Requirements** | FR-020, FR-021, FR-033, NFR-02, NFR-07, NFR-09, P0-04 |

## Summary

Starting an analysis creates a run, enqueues a Cloud Task, and the worker executes the ADK
`case_pipeline` workflow. In this spec every pipeline node is a **stub** that only records progress;
later specs replace stubs with real nodes without touching orchestration. The UI shows progress live.

## User stories

### US-004-1: Start an analysis

- **AC-004-1** Given a `DRAFT` case with ≥1 document, when I click **Run analysis**, then
  `POST /api/cases/{id}/analysis-runs` returns `202 {runId, status: QUEUED}`, the case becomes
  `PROCESSING`, `case.currentRunId = runId`, a `RUN_QUEUED` event is recorded, and one Cloud Task named
  `run-{runId}` targets `POST {WORKER_URL}/tasks/analyze-case` with an OIDC token for
  `kredibel-tasks-invoker`.
- **AC-004-2** With no documents → `409 NO_DOCUMENTS`; while a run is `QUEUED`/`RUNNING` →
  `409 ANALYSIS_ALREADY_RUNNING` with that `runId`.
- **AC-004-3** From `INFO_REQUESTED` and `FAILED` the same action is allowed (new run).

### US-004-2: Run the pipeline

- **AC-004-4** The worker loads the case and runs `case_pipeline`; the run goes `QUEUED → RUNNING →
  SUCCEEDED`; `runs/{runId}.stages` lists every node of [`docs/06`](../../06-agent-design.md) §3
  with status and timings; the case ends in `READY_FOR_REVIEW` with a `RUN_SUCCEEDED` event.
- **AC-004-5** Each document's `status` passes through the document stages in order.
- **AC-004-6** If the task is delivered twice, the second delivery returns `200 {"skipped":"finished"}`
  and changes nothing.
- **AC-004-7** If `case.currentRunId != runId` (a newer run exists), the worker returns
  `200 {"skipped":"stale"}`.
- **AC-004-8** An exception in a case-level node marks the run and case `FAILED` with
  `error.code/message`, records `RUN_FAILED`, and returns `500` only if attempts remain, else `200`.
- **AC-004-9** A failure inside one document marks that document `FAILED` and the run continues.

### US-004-3: Watch it live

- **AC-004-10** While `PROCESSING`, the Overview tab shows a stepper of case stages and one row per
  document with its current status; updates appear within 2 s of the Firestore write (listener).
- **AC-004-11** If the listener fails, the UI polls every 3 s and shows "live updates paused".
- **AC-004-12** On `FAILED`, a banner shows the error message and **Retry analysis**.

### US-004-4: Local development

- **AC-004-13** With `APP_ROLE=all` and `TASK_QUEUE_MODE=inline`, starting a run executes the pipeline
  in-process (background task) with the same code path.
- **AC-004-14** When the org has started `RUN_QUOTA_PER_ORG_PER_DAY` runs today (UTC) or the user exceeds 5
  starts per minute, `POST …/analysis-runs` returns `429 RUN_QUOTA_EXCEEDED` with `retryAfterSeconds`.
- **AC-004-15** With `RUNS_ENABLED=false`, `POST …/analysis-runs` returns `503 RUNS_DISABLED`; all read
  endpoints keep working.

### US-004-5: Plan-aware runs and page progress

- **AC-004-16** Starting a run checks the trial, `min(runsPerDay, RUN_QUOTA_PER_ORG_PER_DAY)`,
  `aiSpendUsdPerMonth`, and reserves the case's uncached, non-blank pages against
  `extractedPagesPerMonth`, all in the transaction that creates the run; failures return
  `403 PLAN_LIMIT_REACHED` (with `limit`, `used`, `max`) or `403 TRIAL_EXPIRED` and create nothing.
- **AC-004-17** When the run ends (succeeded or failed), `runs.usage` and the daily and monthly usage
  documents receive the actuals (`pagesRead`, `pagesCached`, `ocrPages`, `parserPages`, tokens,
  `estimatedUsd`) and the reservation is reconciled (spec 013 AC-013-11).
- **AC-004-18** Per-page progress: the page nodes update `documents.pages[n].status`; the document row
  in the progress widget shows "Reading page 4 of 18" within 2 s.

## Out of scope

Real node logic (005–008). Clarification interrupts (010/spike S3).
