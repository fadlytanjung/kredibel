# Spec 004 — Workflows: documents and months

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 |
| **Owner role** | A: Agents (+ D for queues) |
| **Depends on** | 001, 003, 013 |
| **Requirements** | FR-030 (incremental, order-independent), NFR-01, NFR-02, NFR-09, NFR-10 |
| **Design** | [`docs/06`](../../06-agent-design.md) §1–§4, §8; [`docs/05`](../../05-architecture.md) §5.2, §6; [ADR-001](../../adr/ADR-001-adk-graph-workflows.md), [ADR-006](../../adr/ADR-006-async-jobs-cloud-tasks.md) |

## Summary

Two ADK workflows run in `kredibel-worker`, fed by two Cloud Tasks queues: `document_workflow` turns
one upload into checked records, and `month_workflow` recomputes one month from all its data. Every
change to a month's data (a document read or deleted, a fix in the review queue) increments the
month's **generation** and enqueues one debounced month run; only the latest generation writes. This
spec builds the skeletons with stub nodes, the queues, the run records and live progress; the real
nodes arrive in specs 005–008.

## User stories

### US-004-1: Each upload is processed on its own

- **AC-004-1** `POST /tasks/process-document {orgId, docId, runId}` (OIDC, worker only) runs
  `document_workflow` with the node order of [`docs/06`](../../06-agent-design.md) §2; each node
  appends a stage to `runs/{runId}.stages` (node, parent, status, times, model, tokens, summary) and
  updates `documents/{docId}.status`.
- **AC-004-2** A document that needs a person (type or ledger mapping to confirm) ends in
  `NEEDS_INPUT` without failing; resolving its review item (spec 009) enqueues a new attempt that
  resumes after the confirmed step.
- **AC-004-3** Re-delivering the same task (`doc-{docId}-{attempt}`) is a no-op once the run is
  `DONE`; a node failure with a retryable error returns `5xx` so Cloud Tasks retries; after the last
  attempt the document is `FAILED` with `E02_EXTRACTION_FAILED`.

### US-004-2: Every month is recomputed when its data changes

- **AC-004-4** `finalize_document` marks each month in `documents.months` dirty, increments its
  `generation` in a transaction and creates the task `month-{orgId}-{yyyy-mm}-{generation}` with a
  20-second delay (`MONTH_RUN_DELAY_SECONDS`); the same happens after any review resolution, manual
  match, category change or deletion (from `kredibel-web`).
- **AC-004-5** `POST /tasks/reconcile-month` runs `month_workflow` (static graph of
  [`docs/06`](../../06-agent-design.md) §3); `finalize_month` writes only if the month's generation is
  still the run's generation; otherwise the run ends `SUPERSEDED` and writes nothing.
- **AC-004-6** Ten uploads for March within 20 seconds produce exactly one month run that finishes
  `DONE` (the others `SUPERSEDED` or never started).
- **AC-004-7** A month without a statement ends `COLLECTING`; with a statement it ends `NEEDS_REVIEW`
  or `RECONCILED` ([`docs/05`](../../05-architecture.md) §6).

### US-004-3: Live progress

- **AC-004-8** The SPA shows document status and "page n of m" from the document listener, and month
  state from the month listener, within 2 seconds of the change (NFR-02).
- **AC-004-9** `GET /api/runs/{runId}` returns the run with its stages; `GET /api/runs?target=` lists
  a document's or a month's runs.

### US-004-4: Safe operations

- **AC-004-10** `RUNS_ENABLED=false` stops new tasks from being created (`503 RUNS_DISABLED` on upload
  and re-run); tasks already queued finish.
- **AC-004-11** Month re-runs requested by a user are limited by `monthRunsPerDay` and
  `RUN_QUOTA_PER_ORG_PER_DAY` (`429 RUN_QUOTA_EXCEEDED`); automatic runs count too but are never
  dropped: past the limit they are delayed to the next day and the month shows "Reconciliation paused
  until tomorrow (daily limit)".
- **AC-004-12** Every log line and span carries `orgId`, `runId`, `node`; the run stores `traceId`
  ([`docs/17`](../../17-observability.md)). Both `document_workflow` and `month_workflow` graphs and state deltas are inspectable in the ADK dev UI (`make dev-agents`).

## Out of scope

The node logic itself (005–008), the run graph UI (015), sign-off locks (015).

## Edge cases

- A document deleted while its run is in progress: nodes check that the document still exists before
  writing and stop with `SKIPPED`.
- A month run fails after retries: the month stays `dirty`, shows "Could not reconcile — retry", and a
  manual re-run is allowed.
- Months span the workspace's time zone; a bank line dated 31 Jan 23:30 UTC+7 is January.
