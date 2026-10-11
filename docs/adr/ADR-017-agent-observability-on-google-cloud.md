# ADR-017 — Agent observability on Google Cloud instead of LangSmith

**Status:** Accepted (Cloud Trace P0; run history and Runs page P1) · **Date:** 2026-10-11 ·
**Related:** [ADR-001](ADR-001-adk-graph-workflows.md), [ADR-002](ADR-002-cloud-run-not-agent-runtime.md),
[ADR-016](ADR-016-human-verified-labels-and-learning-loop.md)

## Context

While building and judging Kredibel we need what LangSmith gives LLM teams: every run as a tree of
model and tool calls with inputs, outputs, tokens, latency and errors; a searchable run history; a
local debugging view; feedback from people attached to the exact call that made a decision; datasets
and evals; dashboards and alerts. The project rule is Google Cloud for managed services (P7). The
question is whether Google's stack covers this or we should add LangSmith.

## Decision

Use Google Cloud for every part. No LangSmith.

| What LangSmith gives | Kredibel on Google Cloud | When |
|---|---|---|
| Trace tree of a run (waterfall of LLM and tool calls) | ADK's OpenTelemetry spans (`invoke_agent`, `call_llm`, `generate_content`, `execute_tool`) plus our `workflow:` and `node:` spans, exported to **Cloud Trace**; Trace Explorer shows the waterfall and generative-AI events | P0 |
| Run history table with inputs, outputs, tokens, latency, errors | ADK **BigQuery Agent Analytics plugin** on both workflows and the assistant: one `agent_events` table (LLM requests and responses, tool calls, node outputs, errors, with trace and span IDs) and a view per event type | P1 |
| Viewing prompts and responses | Trace Explorer and the `content` column, **only where content capture is allowed** (below); large content offloaded to Cloud Storage | P1 |
| Local debugging UI | **ADK dev UI** (`adk web`) on a single node or the assistant: events, state and the Trace view; `make dev-agents` | P0 |
| Feedback and annotations | **Labels** (ADR-016): a person's confirm or correct is stored with the `traceId` and `spanId` of the call that proposed the value, so BigQuery joins feedback to the exact LLM call | P1 |
| Datasets and experiments | Verified labels as eval sets and, later, tuning datasets (ADR-016); evals with DeepEval and a Gemini judge ([`15`](../15-testing-and-evaluation.md) §5) | P0 / P1 |
| Dashboards and alerts | Looker Studio on the BigQuery dataset (latency, tokens, cost, errors by node, model and prompt version); Cloud Monitoring log-based metrics and alerts ([`17`](../17-observability.md) §4, §6) | P1 |
| Prompt versions | Prompts in `backend/app/agents/prompts/*.md` with a version header; the version is recorded on every span and event | P0 |
| One place to look, in the product | **Runs page** (`/runs`, owner only): run list and a run's waterfall with events, tokens, cost, the labels it produced and their corrections, and links to Cloud Trace and BigQuery ([`11`](../11-frontend.md) §6.12) | P1 |

**Content capture follows the data, not the environment name.** Setting `AI_CONTENT_CAPTURE`:

- `off` (the default, and the only value allowed with real data): `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false`;
  the plugin drops the `content` and `content_parts` columns (`payload_column_denylist`); events keep
  model, tokens, latency, status and IDs only.
- `synthetic` (the prototype project and local development, where `DATA_CLASS=synthetic`): spans carry
  payloads; the plugin logs text content through a `content_formatter` that masks account and ID
  numbers anyway; page images are never logged (`log_multi_modal_content=false`); large content goes
  to the `kredibel-agent-content` bucket with a 30-day lifecycle. Settings validation refuses
  `synthetic` unless `DATA_CLASS=synthetic`.

## Why not LangSmith

It would work: ADK emits OpenTelemetry, and LangSmith accepts it. But it is a third-party managed
service outside Google Cloud (P7), it would hold prompts and page text outside the project's region and
IAM, and every capability we need above exists in Cloud Trace, BigQuery and the ADK dev UI. The one
thing LangSmith does better out of the box, a polished annotation and run UI, we need inside the
product anyway: the Labels page and the Runs page.

## Consequences

- One extra dependency: `google-adk[bigquery-analytics]` (plugin on the ADK `App`), and one BigQuery
  dataset `kredibel_agent_analytics` in `asia-southeast1` ([`16`](../16-infrastructure-and-deployment.md)).
- BigQuery Storage Write API and storage are billed; at prototype volume this is cents
  ([`21`](../21-cost-analysis.md) §3).
- The Runs page reads Firestore `runs` (stages) and, for event detail, BigQuery through the API, filtered
  to the workspace (every run's ADK `user_id` starts with `{orgId}:`; workflows use `{orgId}:system`);
  nothing is queried from the browser.
- Developers debug a node with `adk web` locally before deploying, and a failed run in production from
  its Cloud Trace link.
- If a production deployment ever needs content for debugging, it is a separate decision with consent
  and redaction, not a flag flip.

## Sources

- [BigQuery Agent Analytics plugin for ADK](https://adk.dev/integrations/bigquery-agent-analytics/)
- [ADK and Cloud Trace](https://adk.dev/integrations/cloud-trace/)
- [Observability for AI agent developers (Google Cloud)](https://docs.cloud.google.com/stackdriver/docs/instrumentation/ai-agent-overview)
