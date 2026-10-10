# Spec 012 — Evals & Results (P1)

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P1 (run the P0 suites on D6 regardless) |
| **Owner role** | A: Agents |
| **Depends on** | 002, 008 (P0 suites); 010, 011 (P1 suites) |
| **Requirements** | P1-08, NFR-01, NFR-04, NFR-05, NFR-07 |
| **Design** | [`docs/15`](../../15-testing-and-evaluation.md) §4–§6 |

## Summary

Run the full pipeline with real Gemini and Document AI OCR on scenario variants, compare with ground
truth, and publish a dated report whose numbers (and only those) appear in the README and proposal.

## User stories

- **AC-012-1** `make evals` runs S1–S3 (and S4–S6 when available) × seeds 1–5 against the dev project
  using a dedicated org `org_eval`, then writes `backend/evals/reports/<date>.md` and `.json`.
- **AC-012-2** The report contains the suites E-CLS, E-EXT, E-FOR, E-CAT, E-REC, E-DEC, E-MEMO, E-PERF
  (P0) and E-SEC, E-VIS, E-AST (P1 when built), each with the target and the measured value.
- **AC-012-3** Each case's run ID is listed so any number can be traced to its run.
- **AC-012-4** `tools/checks/readme_results.py` fails `make check` if the README "Results" table
  contains numbers not present in the latest report.
- **AC-012-5** Evals are never part of `make check` or Cloud Build.
- **AC-012-6** E-EXT reports, for S1–S3 digital and the scanned S1 variant: field accuracy of the AI
  reader, verifier agreement, box coverage, witness-only rows, and **cost per page and per case**
  measured from `runs.usage`; with `EXTRACTION_MODE=thorough` on S1–S3 seed-1 it reports the same
  numbers so adaptive and thorough can be compared (ADR-010).
- **AC-012-7** E-CPTY reports counterparty role accuracy and merge precision against
  `expectedCounterparties`, and suggestion precision/recall against `expectedSuggestions` (spec 014).
