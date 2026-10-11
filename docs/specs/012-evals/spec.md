# Spec 012 — Evals and Results

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 suites run on D6 regardless · P1 suites when their features exist |
| **Owner role** | A: Agents |
| **Depends on** | 002, 005–009 (P0 suites); 011, 015 (P1 suites) |
| **Requirements** | NFR-01, NFR-04, NFR-05, NFR-07, P1-08 |
| **Design** | [`docs/15`](../../15-testing-and-evaluation.md) §5–§7 |

## Summary

Run both workflows with real Gemini and Document AI OCR on the synthetic scenarios, compare with
`truth.json`, and publish a dated report whose numbers (and only those) appear in the README and the
proposal. The headline numbers are the ones the product promises: **auto-match rate**, **wrong
automatic matches**, duplicates caught, edited documents caught, and cost per page.

## User stories

- **AC-012-1** `make evals` uploads each scenario's files in its `upload-order.txt` into a dedicated
  workspace `org_eval` (reset per case), waits for the months to settle, and writes
  `backend/evals/reports/<date>.md` and `.json`.
- **AC-012-2** P0 suites: E-CLS, E-EXT, E-MAP, E-DUP, E-FOR, E-REC, E-RSK, E-CAT, E-CPTY, E-EXP,
  E-PERF, each with its target and measured value ([`docs/15`](../../15-testing-and-evaluation.md) §5).
- **AC-012-3** E-REC reports for S1–S5 × seeds 1–5: auto-match rate, wrong automatic matches (an
  `AUTO` match not in `truth.json`), `PROPOSED` pairs never auto-matched, and S5 = S1 by
  deterministic ID.
- **AC-012-4** E-DUP reports recall and precision per technique (T7–T11 and the `double-payment`
  fixture) and confirms that no held value was counted in month figures.
- **AC-012-5** E-EXT reports field accuracy of the AI reader, agreement, box coverage and **cost per
  page and per scenario** from `runs.usage`, for digital, scanned and photo inputs, and `adaptive` vs
  `thorough` on S1 seed 1.
- **AC-012-6** P1 suites when built: E-AST (DeepEval + ADK trajectories, spec 011), E-SEC (S6), E-VIS.
- **AC-012-7** Each case lists its run IDs so any number can be traced to a run and its trace.
- **AC-012-8** `tools/checks/readme_results.py` fails `make check` if the README "Results" table
  contains numbers not present in the latest report.
- **AC-012-9** Evals are never part of `make check` or Cloud Build.
