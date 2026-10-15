# Plan 017 — Agent observability

| Part | Files |
|---|---|
| Dev UI | `backend/app/agents/dev_apps/<node>/agent.py` (thin wrappers around the real node agents with fixture tools); `Makefile` target `dev-agents` |
| Local OTel (P0) | `TRACE_EXPORT=otlp`, traces-only OTLP/HTTP exporter in `observability/tracing.py`; existing locked OTel SDK/exporter dependencies. Jaeger 2.22.0 in an optional Docker Compose `tracing` profile, ports 16686 and 4318 on loopback, transient memory. `trace-up`, `trace-down`, `trace-smoke`, `dev-traced` Make targets; smoke checks collector ingestion. Direct Gemini reader attempts emit metadata spans, including retries, without installing a second SDK instrumentor. |
| Plugin | `backend/app/observability/agent_analytics.py`: builds `BigQueryAgentAnalyticsPlugin(project_id, dataset_id="kredibel_agent_analytics", location="asia-southeast1", gcs_bucket_name=…, log_multi_modal_content=False, content_formatter=mask, payload_column_denylist=…)` from settings; attached in `agents/workflows/*.py` and `agents/assistant.py` |
| Settings | `core/settings.py`: `AI_CONTENT_CAPTURE` (`off`, `synthetic`), `DATA_CLASS`, `ANALYTICS_DATASET`, `AGENT_CONTENT_BUCKET`; validator |
| Events API | `adapters/bigquery_events.py` (parameterized query by `trace_id` and `user_id` prefix), `api/runs.py` `GET /api/runs/{runId}/events`, joins label IDs by `spanId` |
| Runs page | `pages/RunsPage.tsx`, `pages/RunPage.tsx`, `widgets/RunWaterfall/`, `widgets/EventInspector/` |
| Infra | `infra/bootstrap.sh`: dataset, bucket with 30-day lifecycle, IAM (`kredibel-worker`: `bigquery.dataEditor` on the dataset, `bigquery.jobUser`; `kredibel-web`: `bigquery.dataViewer`, `bigquery.jobUser`) |
| Dashboard | `infra/looker/agent-events.md` (data sources and charts; the report is shared from the team account) |

Dependency: `google-adk[bigquery-analytics]` at the version pinned in `uv.lock` (≥ 2.7 for event IDs).
