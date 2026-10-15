# Tasks 017 — Agent observability

- [x] **T017-01** `make dev-agents` with one dev app per LLM node and the assistant; fixtures by default. (AC-017-1)
- [x] **T017-01a** **TDD** local OTLP export, Jaeger Compose profile and verified smoke command; trace direct Gemini SDK requests and retries without document content. Document local and GCP URLs. (AC-017-9)
- [x] **T017-01b** **TDD** Langfuse locally (ADR-026): compose profile, `make langfuse-up` with generated credentials, `TRACE_EXPORT=langfuse`, session/user/tags on every span, prompts and responses only with synthetic capture, `make langfuse-smoke`, `make gemini-usage`. (AC-017-10)
- [x] **T017-02** **TDD** settings validator for `AI_CONTENT_CAPTURE` and `DATA_CLASS`; content formatter masks account and ID numbers. (AC-017-3) The validator is in `core/settings.py` (synthetic capture only with `DATA_CLASS=synthetic`); the content formatter comes with the BigQuery plugin (T017-03).
- [ ] **T017-03** Attach the BigQuery Agent Analytics plugin to both workflows and the assistant; bootstrap dataset, bucket and IAM; plugin failures never fail a run. (AC-017-2, AC-017-4)
- [x] **T017-04** `GET /api/runs/{runId}/events` with workspace filter and label join; run fields `traceUrl`, `models`, `promptVersions`, `labels`. (AC-017-6, AC-017-7) Built 16 Oct 2026 from the run's stages (`test_runs_events_api.py`): one event per stage and one per model call with latency, tokens and span, joined to the labels of the run; content is never stored, so `contentCaptured` is false until the BigQuery plugin lands.
- [x] **T017-05** Runs list and run page with waterfall and event inspector; three widths. (AC-017-5, AC-017-6) Built 16 Oct 2026: `/runs` and `/runs/:runId` (owner only), the mock `runs.html` from `contracts/design/fixtures/runs.json`, `runs.spec.ts`.
- [ ] **T017-06** Looker Studio report and its notes. (AC-017-8)
- [x] **T017-07** Update `docs/20-implementation-status.md`. (16 Oct 2026)
