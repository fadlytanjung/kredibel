# Plan 012 — Evals & Results

| File | Content |
|---|---|
| `backend/evals/run.py` | uploads each scenario's files through the **API** (end-to-end, as a user would), starts runs, waits, collects results via the API and Firestore |
| `backend/evals/metrics.py` | per-suite computations against `truth.json` (row F1, confusion matrices, recall per technique, macro-F1, match accuracy, grounding rates, latency percentiles, cost) |
| `backend/evals/report.py` | Markdown + JSON report with targets and pass/miss markers |
| `backend/evals/assistant/` | ADK eval sets (from 011) |
| `tools/checks/readme_results.py` | README numbers ⊆ latest report |
| `Makefile` | `evals` target with `EVAL_SEEDS`, `EVAL_SCENARIOS` |

Cost control: seeds default to 1–5; `EVAL_SEEDS=1` for a quick run. Each eval run records its usage.
