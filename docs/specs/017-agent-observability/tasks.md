# Tasks 017 — Agent observability

- [x] **T017-01** `make dev-agents` with one dev app per LLM node and the assistant; fixtures by default. (AC-017-1)
- [ ] **T017-02** **TDD** settings validator for `AI_CONTENT_CAPTURE` and `DATA_CLASS`; content formatter masks account and ID numbers. (AC-017-3)
- [ ] **T017-03** Attach the BigQuery Agent Analytics plugin to both workflows and the assistant; bootstrap dataset, bucket and IAM; plugin failures never fail a run. (AC-017-2, AC-017-4)
- [ ] **T017-04** `GET /api/runs/{runId}/events` with workspace filter and label join; run fields `traceUrl`, `models`, `promptVersions`, `labels`. (AC-017-6, AC-017-7)
- [ ] **T017-05** Runs list and run page with waterfall and event inspector; three widths. (AC-017-5, AC-017-6)
- [ ] **T017-06** Looker Studio report and its notes. (AC-017-8)
- [ ] **T017-07** Update `docs/20-implementation-status.md`.
