# Plan 012 — Evals and Results

| File | Content |
|---|---|
| `backend/evals/runner.py` | per scenario and seed: reset `org_eval`, upload in order through the API client, wait for months to settle (listener or polling of `months.dirty`), collect records |
| `backend/evals/mapping.py` | map `truth.json` keys to Kredibel's deterministic IDs |
| `backend/evals/suites/*.py` | one module per suite; each returns rows and a summary vs target |
| `backend/evals/report.py` | Markdown and JSON writer; run IDs and trace links |
| `backend/evals/assistant/` | DeepEval and ADK eval set (spec 011) |
| `tools/checks/readme_results.py` | README numbers must exist in the latest report |

Judge model for DeepEval: `EVAL_JUDGE_MODEL` on Agent Platform; no third-party evaluation cloud.
