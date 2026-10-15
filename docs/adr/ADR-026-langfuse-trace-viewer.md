# ADR-026 — Langfuse as the trace viewer for model calls

**Status:** Accepted for local development (T017-01b) · production **Proposed** (needs a decision) ·
**Date:** 2026-10-13 · **Amends:** [ADR-017](ADR-017-agent-observability-on-google-cloud.md)

## Context

ADR-017 keeps observability on Google Cloud: spans to Cloud Trace, and locally to Jaeger or the ADK
dev UI. In practice the team could not find the model calls: Gemini on Vertex AI does not show up
under an AI Studio key, and the console moved Vertex AI under a new name. Jaeger shows the span
tree but not what an LLM team looks for: each generation with its model, tokens, prompt and
response, grouped by the document or month it belongs to. Langfuse is open source (MIT core),
self-hostable, and accepts OpenTelemetry over HTTP, which `app/observability/tracing.py` already
emits.

## Decision

**Local development: Langfuse v4 in Docker** (`make langfuse-up`, http://localhost:3000).

- A compose profile `langfuse` runs Langfuse web and worker with Postgres, ClickHouse, Redis and
  MinIO, every port bound to 127.0.0.1, Langfuse's own telemetry off, images pinned.
- `make langfuse-up` writes per-machine credentials (database passwords, the project's public and
  secret key, the admin login) to `infra/langfuse/.env`, which git ignores; nothing secret is in
  the repository.
- `TRACE_EXPORT=langfuse` (with `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`)
  exports the same spans over OTLP/HTTP to `/api/public/otel/v1/traces` with Basic auth.
  `make dev-langfuse` sets them from that file.
- Every span of a run carries `langfuse.session.id` (the document or `month:yyyy-mm`),
  `langfuse.user.id` (the workspace) and `langfuse.trace.tags` (the workflow), so Langfuse groups
  and filters runs. Gemini calls are generations already (`gen_ai.request.model`,
  `gen_ai.usage.*`).
- **Content follows the data, as in ADR-017:** prompts and responses go into
  `langfuse.observation.input` and `output` only when `AI_CONTENT_CAPTURE=synthetic`, which settings
  allow only with `DATA_CLASS=synthetic`. Page images are never exported. With real data Langfuse
  shows the run tree, models, tokens, latency and errors.

**Production: proposed, not decided.** Langfuse v4 needs Postgres, ClickHouse, Redis and object
storage. On Google Cloud that is Cloud Run for web and worker (worker always on), Cloud SQL for
Postgres, Memorystore for Redis, Cloud Storage, and ClickHouse on a Compute Engine VM (there is no
managed ClickHouse on Google Cloud), joined by a VPC connector; roughly USD 130–180 a month at
prototype size. Because real documents forbid content capture, production Langfuse would show the
same metadata Cloud Trace already holds. The alternative within ADR-017 is the in-app Runs page
(T017-04, T017-05) linking each run to its Cloud Trace waterfall.

## Consequences

- Local runs get a LangSmith-like view without any account outside our machine or Google Cloud.
- The same `TRACE_EXPORT=langfuse` switch serves a production Langfuse if one is decided; its keys
  would live in `kredibel-env` (ADR-024).
- Cloud Trace stays the production default; nothing in a deployed service changes.
