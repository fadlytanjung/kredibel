# Spec 017 — Agent observability: run history and the Runs page

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0: traces in Cloud Trace and the ADK dev UI (already in 001 and 004) · P1: run history in BigQuery and the Runs page |
| **Owner role** | A (plugin, events API) · D (infrastructure) · C (Runs page) |
| **Depends on** | 004, 016 (labels for feedback) |
| **Requirements** | P1-06, P1-12, FR-073, FR-076, NFR-10 |
| **Design** | [ADR-017](../../adr/ADR-017-agent-observability-on-google-cloud.md); [`docs/17`](../../17-observability.md) §2, §8–§10; [`docs/11`](../../11-frontend.md) §6.12 |

## Summary

See every agent run the way LangSmith shows it, with Google Cloud only: the waterfall in Cloud Trace,
a searchable history of every model and tool call in BigQuery, a local debugging view in the ADK dev
UI, and one **Runs** page in the product that ties a run's calls to the labels it produced and the
corrections people made.

## User stories

### US-017-1: Debug locally (P0)

- **AC-017-9** `make trace-up` starts a local, loopback-only OTLP/HTTP collector and Jaeger
  viewer at `http://localhost:16686`. `make dev-traced` exports the local application's workflow,
  node and Gemini request spans to it. `make trace-smoke` verifies ingestion and prints a trace URL;
  it needs no Google credentials and touches no workspace. Each direct Gemini SDK attempt records
  the model, prompt version, attempt number, token usage and sanitized error type/status, never
  document content, images or exception messages. Cloud Run continues to use Cloud Trace.

- **AC-017-10** `make langfuse-up` starts a loopback-only Langfuse with per-machine credentials that
  git ignores, and `make langfuse-smoke` proves a trace arrives. With `TRACE_EXPORT=langfuse` a
  document or month run appears as one trace whose Gemini calls are generations with model and
  tokens, grouped by the document or month (session) and the workspace (user); prompts and responses
  appear only with `AI_CONTENT_CAPTURE=synthetic` (ADR-026).
- **AC-017-1** `make dev-agents` starts the ADK dev UI (`adk web`) on `backend/app/agents/dev_apps/`
  with one app per LLM node (classifier, page reader, ledger mapper, categorizer, explainer) and the
  assistant, wired to recorded fixtures by default and to real Gemini with `LIVE=1`; the Trace view
  shows each call.

### US-017-2: Run history in BigQuery (P1)

- **AC-017-2** Both workflows and the assistant attach `BigQueryAgentAnalyticsPlugin` (dataset
  `kredibel_agent_analytics`, table `agent_events`, location `asia-southeast1`, views per event type);
  every event carries `trace_id` and `span_id`, and ADK `user_id` is `{orgId}:system` for workflows and
  `{orgId}:{uid}` for the assistant.
- **AC-017-3** Content follows `AI_CONTENT_CAPTURE`: `off` drops `content` and `content_parts`;
  `synthetic` keeps text with account and ID numbers masked, never page images. Settings validation
  refuses `synthetic` unless `DATA_CLASS=synthetic` (TDD).
- **AC-017-4** A plugin failure never fails a run (logged, counted in `kredibel/agent_events_dropped`).

### US-017-3: The Runs page (P1)

- **AC-017-5** `/runs` (owner only) lists runs with kind, target, status, start, duration, LLM calls,
  tokens, estimated cost, models, prompt versions and labels proposed, verified and corrected; filters
  by kind, status and "corrected by a person".
- **AC-017-6** A run opens as a waterfall of its nodes and calls (from run stages and
  `GET /api/runs/{runId}/events`) with latency, tokens and status; selecting a call shows its prompt
  and response when captured, else "Content is not captured in this deployment"; the labels it produced
  link to the Labels page with their status.
- **AC-017-7** Each run links to Cloud Trace (`traceUrl`) and to its rows in BigQuery.

### US-017-4: Dashboards (P1)

- **AC-017-8** A Looker Studio report on `agent_events` shows p50 and p95 latency, tokens, errors and
  estimated cost by node, model and prompt version, and AI agreement with people from the labels
  export view; linked from [`docs/17`](../../17-observability.md) §7.

## Out of scope

LangSmith or any other third-party tracing service; content capture with real data; a prompt
playground (Agent Platform Studio covers ad-hoc prompting).
