# 17 — Observability

> Know what every run did, how long it took, what it cost, and why it failed, without ever logging a
> customer's data.

---

## 1. Signals

| Signal | Tool | Content |
|---|---|---|
| Logs | Cloud Logging (structured JSON to stdout via `structlog`) | One line per request and per node start/finish/error |
| Traces | Cloud Trace via OpenTelemetry (`google-adk[otel-gcp]` extra, FastAPI instrumentation) | Request → task → workflow → node → external call spans |
| Run timeline | Firestore `runs/{runId}.stages` | Product-visible "agent trace": stage, duration, model, tokens, outcome |
| Metrics | Cloud Monitoring (log-based metrics) | Counts and latencies below |
| Errors | Error Reporting (from structured error logs) | Grouped exceptions |

---

## 2. Log schema

Every log line includes:

```json
{
  "severity": "INFO",
  "message": "node.finished",
  "service": "kredibel-worker",
  "version": "a1b2c3d",
  "caseId": "case_01J…",
  "runId": "run_01J…",
  "docId": "doc_01J…",
  "node": "read_page",
  "page": 2,
  "witness": "TEXT_LAYER",
  "durationMs": 4210,
  "model": "gemini-3.8-flash",
  "tokensIn": 1920,
  "tokensOut": 1310,
  "outcome": "ok",
  "logging.googleapis.com/trace": "projects/<PROJECT_ID>/traces/<traceId>"
}
```

**Never logged:** document text, transaction descriptions, names, account numbers, prompts with
document content, model outputs. Debugging content lives in the raw extractor JSON in GCS (access
controlled), referenced by path.

---

## 3. Log-based metrics

| Metric | Filter / extraction | Use |
|---|---|---|
| `kredibel/run_duration_ms` | `message="run.finished"` → `durationMs` (distribution) | NFR-01 |
| `kredibel/run_failed` | `message="run.finished" AND outcome="failed"` (counter) | alert |
| `kredibel/node_duration_ms` | `message="node.finished"`, label `node` | find slow stages |
| `kredibel/model_tokens` | `tokensIn + tokensOut`, label `model` | cost |
| `kredibel/pages_read` | `message="page.read"`, labels `witness` (`TEXT_LAYER`, `OCR`), `cached` | cost; share of scanned pages |
| `kredibel/ocr_pages` | `message="ocr.processed"` → `pages` | cost |
| `kredibel/pages_escalated` | `message="page.escalated"` (P1) | cost; extraction quality |
| `kredibel/page_agreement` | `message="page.verified"` → `agreement` (distribution) | extraction quality |
| `kredibel/plan_limit_hit` | `message="plan.denied"`, label `limit` | trial limits too tight or abuse |
| `kredibel/workspaces_created` | `message="workspace.created"` | sign-up volume vs `MAX_WORKSPACES` |
| `kredibel/suggestion_decided` | `message="suggestion.decided"`, labels `field`, `status` | suggestion usefulness (acceptance rate) |
| `kredibel/schema_retry` | `message="llm.schema_retry"` | prompt quality |

---

## 4. Alerts (email to the team)

| Alert | Condition |
|---|---|
| Run failures | `run_failed` ≥ 2 in 15 min |
| Slow runs | p95 `run_duration_ms` > 5 min over 30 min |
| Worker 5xx | Cloud Run `request_count` with 5xx > 5 in 10 min |
| Budget | 50% / 90% of budget |
| Sign-up surge | `workspaces_created` ≥ 5 in 1 hour |
| Low agreement | p50 `page_agreement` < 0.9 over 1 hour (reader or witness regression) |

---

## 5. Dashboards

One Cloud Monitoring dashboard "Kredibel": runs per hour, run duration p50/p95, failures, node
duration by stage (stacked), tokens by model, pages read by witness (text layer vs OCR), escalated
pages, page agreement, plan limit hits, workspaces created, Cloud Run instance count and latency for
both services.
