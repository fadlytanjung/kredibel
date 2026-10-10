# Spec 008 — Scoring & Credit Memo

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 |
| **Owner role** | B: Risk engine (scorecard) + A: Agents (memo writer, guard) |
| **Depends on** | 006, 007 |
| **Requirements** | FR-030, FR-031, FR-032, NFR-05, P0-11, P0-12, constitution P2/P3 |
| **Design** | [`docs/08`](../../08-risk-engine.md) §7, [`docs/06`](../../06-agent-design.md) §4.2–§4.3, `contracts/policy/scorecard.v1.yaml` |

## Summary

Turn facts and findings into a transparent score, grade, hard stops and recommendation; then have
Gemini draft a credit memo from **facts only**, verified by the grounding guard; finalize the run.

## User stories

### US-008-1: Score

- **AC-008-1** Each component's metric value, band, points and contribution are stored; the score is
  `round(Σ weight × points / 100)`; the grade follows the policy bands.
- **AC-008-2** Hard stops are evaluated per policy; `metricBelow` never fires on a missing metric; the
  final recommendation is the most severe of the grade's and every hard stop's.
- **AC-008-3** Expected results: S1 → `APPROVE` or `APPROVE_WITH_CONDITIONS`, no hard stop; S2 →
  `DECLINE` with `TAMPERED_DOCUMENT`; S3 → `REFER` with `REVENUE_NOT_EVIDENCED`.
- **AC-008-4** `APPROVE_WITH_CONDITIONS` includes templated conditions for components below 60 points,
  with values formatted from facts.
- **AC-008-5** `analysis.recommendation` stores proposed installment, max supportable installment and
  amount.

### US-008-2: Draft the memo

- **AC-008-6** The memo writer receives the facts bundle of [`docs/06`](../../06-agent-design.md) §4.2
  (no document content; applicant summary and top counterparties included) and returns the 7 sections
  of `MemoSection.key`, written in English.
- **AC-008-7** Every figure in the memo carries a citation marker that resolves to a fact, finding or
  document page in the bundle.
- **AC-008-8** The tone is neutral; the memo states the recommendation and hard stops exactly as
  computed and does not invent conditions.
- **AC-008-9** If `MODEL_REASONING` errors or is unavailable, `MODEL_REASONING_FALLBACK` is used and the
  model actually used is recorded.

### US-008-3: Guard the memo

- **AC-008-10** The grounding guard passes a memo whose numbers all match facts cited in the same
  sentence (formats `IDR 1,250,000`, `1,250,000.00`, `IDR 1.25 million`, `1.42x`, `64%`).
- **AC-008-11** On failure it triggers one redraft with the problems listed; after `MEMO_MAX_ATTEMPTS`
  the memo is saved with `grounding.status = UNVERIFIED` and the problems.
- **AC-008-12** On S1–S3 (recordings), the memo is `VERIFIED`.

### US-008-4: Finalize

- **AC-008-13** `finalize_run` writes `memo/current`, `case.summary` (score, grade, recommendation,
  hard stops, worst verdict, open finding counts), sets the case `READY_FOR_REVIEW`, the run
  `SUCCEEDED` with usage totals, and records `RUN_SUCCEEDED`, only if `case.currentRunId == runId`.
- **AC-008-14** `GET /api/cases/{id}/analysis` includes the scorecard and recommendation;
  `GET /api/cases/{id}/memo` returns the memo with grounding status.
