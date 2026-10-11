# Plan 017 — Agent observability

| Part | Files |
|---|---|
| Dev UI | `backend/app/agents/dev_apps/<node>/agent.py` (thin wrappers around the real node agents with fixture tools); `Makefile` target `dev-agents` |
| Plugin | `backend/app/observability/agent_analytics.py`: builds `BigQueryAgentAnalyticsPlugin(project_id, dataset_id="kredibel_agent_analytics", location="asia-southeast1", gcs_bucket_name=…, log_multi_modal_content=False, content_formatter=mask, payload_column_denylist=…)` from settings; attached in `agents/workflows/*.py` and `agents/assistant.py` |
| Settings | `core/settings.py`: `AI_CONTENT_CAPTURE` (`off`, `synthetic`), `DATA_CLASS`, `ANALYTICS_DATASET`, `AGENT_CONTENT_BUCKET`; validator |
| Events API | `adapters/bigquery_events.py` (parameterized query by `trace_id` and `user_id` prefix), `api/runs.py` `GET /api/runs/{runId}/events`, joins label IDs by `spanId` |
| Runs page | `pages/RunsPage.tsx`, `pages/RunPage.tsx`, `widgets/RunWaterfall/`, `widgets/EventInspector/` |
| Infra | `infra/bootstrap.sh`: dataset, bucket with 30-day lifecycle, IAM (`kredibel-worker`: `bigquery.dataEditor` on the dataset, `bigquery.jobUser`; `kredibel-web`: `bigquery.dataViewer`, `bigquery.jobUser`) |
| Dashboard | `infra/looker/agent-events.md` (data sources and charts; the report is shared from the team account) |

Dependency: `google-adk[bigquery-analytics]` at the version pinned in `uv.lock` (≥ 2.7 for event IDs).
