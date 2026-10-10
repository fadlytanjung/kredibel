# 15 — Testing & Evaluation

> Tests prove the code does what the spec says. Evals measure how well the models do their part.
> Tests gate merges; evals inform decisions (constitution P10).

---

## 1. Layers

| Layer | What | Runs | Gate? | Location |
|---|---|---|---|---|
| Unit | Domain functions, state machine, policy and plan loaders, entitlement checks, page triage, verifier, normalizers, counterparties, profile suggestions, grounding guard | every `make check` | ✔ | `backend/tests/unit` |
| Integration | API routes with fakes for every port; auth/org isolation; problem+json | every `make check` | ✔ | `backend/tests/integration` |
| Scenario | Full `case_pipeline` on synthetic scenarios with **recorded** Gemini, OCR (and parser, P1) outputs | every `make check` | ✔ | `backend/tests/scenarios` |
| Frontend unit/component | Formatters, citation parser, widgets with MSW | every `make check` | ✔ | `frontend/src/**/*.test.ts(x)` |
| Contract | Generated TS types compile; OpenAPI validates; backend response models match `openapi.yaml` (schemathesis-style smoke on fakes) | every `make check` | ✔ | both |
| E2E smoke | Playwright demo path against local or deployed env | before demo recording | manual | `frontend/e2e` |
| **Evals** | Real models on scenario variants | `make evals` | ✘ | `backend/evals` |

Coverage targets: `domain/` ≥ 90% lines, `services/` ≥ 80%. Coverage is a floor, not the goal.

---

## 2. Ground truth

The synthetic generator ([`18`](18-synthetic-data.md)) writes, next to every scenario, a
`truth.json` with:

- every statement row (date, description, debit, credit, balance) and invoice field **as generated**;
- the tampering applied (document, row, field, before/after, technique);
- expected finding codes per document and per case (P0 set and full set);
- expected verdict per document, expected recommendation, expected key metrics (±1 unit);
- category label per transaction;
- the applicant as onboarded, the expected profile suggestions and the expected counterparties with
  roles (spec 014).

Tests and evals read this file; nobody hand-writes expected values.

---

## 3. Unit and scenario test highlights

| Area | Must-have tests |
|---|---|
| Normalization | English amount format plus dot-grouped `1.250.000,00`; `CR/DB` suffixes; parentheses; English month names; year inference across December/January |
| Page triage | Usable text layer; `(cid:…)` glyphs → unusable; image-only → none; white page → blank |
| Verifier | AI = witness → agreement 1.0; AI drops a row → one witness-only row and no CRITICAL A01 across it; value in the wrong column → `CONFLICT`; white-out + overlay → `CONFLICT`, never `AGREED`; boxes from witness tokens |
| Consensus (P1) | Three sources: two agree → `AGREED`; all differ → `CONFLICT` |
| Plans | Every limit at, below and above the boundary; trial expiry by injected clock; overrides; all-cached run reserves 0 pages; concurrent creations at the limit |
| Applicant | Type blocks required; ownership ≤ 100%; account mask/hash; full numbers never in responses or logs (assert on captured logs) |
| Counterparties & suggestions | Role rules; merging spellings; unnamed buckets; deterministic suggestion IDs; rejected values never return; `CONFLICT` for single-valued fields |
| A01/A02 | Property test: any generated consistent statement → no A01; changing one credit without touching balances → exactly one A01 at that row |
| M03/M04 | Fixture PDFs: signed-only revision → MEDIUM; content-changed revision → HIGH; one value in a different font → M04 on that row |
| Reconciliation | Exact, net-of-withholding, split (2 and 3 parts), partial, not-due, greedy tie-breaking determinism |
| Metrics | ADB with carried-forward balances; months with no transactions; annuity with r = 0 |
| Scorecard | Each band boundary; hard stop precedence; conditions templating |
| State machine | Every (status, outcome, role, guard) combination in a table-driven test |
| Grounding guard | `IDR 1,250,000`, `IDR 1.25 million`, `1,250,000`, `1.42x`, `64%` all match their facts; `1.25M` is rejected as ambiguous; an unmatched number fails with the sentence quoted |
| Workspace isolation | Every route with a foreign `caseId` or `applicantId` → 404; no workspace → `403 WORKSPACE_REQUIRED` |
| Scenario | S1–S6 produce exactly the expected P0 codes, verdicts and recommendation |

---

## 4. Evals

Run on **5 seeds × each scenario** (30 cases, plus the scanned S1 variant) against real Gemini and
Document AI OCR (and Form/Invoice Parser for the `thorough` comparison). Results go to
`backend/evals/reports/<YYYY-MM-DD>.md` and a JSON twin for charts.

| Suite | Measures | Target (prototype) |
|---|---|---|
| **E-CLS** classification | Accuracy, confusion matrix by `docType` | ≥ 0.95 |
| **E-EXT** extraction | Row-level precision/recall/F1 on `(date, amount, direction)` for the AI reader alone and after verification; header field accuracy; agreement distribution; box coverage; witness-only rows; **cost per page**; digital vs scanned; `adaptive` vs `thorough` on S1–S3 seed-1 | Verified F1 ≥ 0.98 on digital PDFs, ≥ 0.95 on scans; ≤ USD 0.01 per page |
| **E-CPTY** counterparties & suggestions (spec 014) | Role accuracy and merge precision vs `expectedCounterparties`; suggestion precision/recall vs `expectedSuggestions` | Role accuracy ≥ 0.95; suggestion precision ≥ 0.9 |
| **E-FOR** forensics | Per-document verdict confusion matrix; recall per seeded technique; **false `TAMPERED` on clean docs** | Recall 100% for seeded P0 techniques; 0 false `TAMPERED` |
| **E-VIS** visual (P1) | Visual findings that overlap a seeded edit (IoU ≥ 0.3) vs total visual findings | Report only |
| **E-CAT** categorization | Macro-F1 vs labels; share by rule/model; `UNKNOWN` rate | Macro-F1 ≥ 0.85 |
| **E-REC** reconciliation | Invoice match status accuracy | ≥ 0.95 |
| **E-DEC** recommendation | Matches the expected recommendation per scenario | 30/30 |
| **E-MEMO** memo | Grounding pass rate on first attempt and after retries; rubric review of 5 memos by a team member (clarity, accuracy, tone) | ≥ 90% first attempt; 100% verified or labelled |
| **E-SEC** injection (P1) | S6 variants flagged by Model Armor; **zero model calls containing quarantined content** (asserted from gateway logs) | 100% / 0 |
| **E-AST** assistant (P1) | ADK eval sets: tool trajectory match and answer contains the expected fact IDs | ≥ 0.9 |
| **E-PERF** latency & cost | p50/p95 per stage and per case; pages read, cached, OCR'd, escalated; tokens; estimated USD | p50 ≤ 3 min; ≤ USD 0.50 per new case, ≤ USD 0.25 per re-run |

### 4.1 ADK evals for the assistant (P1)

- Eval sets in `backend/evals/assistant/*.evalset.json`, run with `adk eval`.
- Each case: a case fixture (scenario + seed), a question, the expected tool calls (names and key
  arguments) and the fact/finding IDs the answer must cite.
- Example: *"Why is the March statement flagged?"* → expects `list_findings(docId=…)` then
  `get_finding(...)`; answer must cite the `A01` finding ID.

### 4.2 Memo rubric (manual, 5 memos)

| Criterion | 1 | 3 | 5 |
|---|---|---|---|
| Accuracy | wrong figures | minor slips | every figure verified |
| Evidence | few citations | most claims cited | every claim cited |
| Clarity | hard to follow | clear | an analyst would sign it with light edits |
| Tone | alarmist or vague | neutral | precise, neutral, actionable |

---

## 5. Recordings (keeping CI offline)

`make record SCENARIO=S2 SEED=1` runs the real Gemini page reader, OCR (scanned variant) and, for P1,
the parsers once and stores their raw outputs **per page** under
`backend/tests/scenarios/recordings/<scenario>/<seed>/`. The scenario tests use `RecordedGemini`,
`RecordedOcr` and `RecordedParser` fakes that replay them by `(sha256, page, model or processor,
prompt version)`. The text-layer witness needs no recording (it runs locally on the PDF). Re-record
when a prompt version changes; the test fails loudly if a recording is missing.

---

## 6. What we publish

The README's **Results** section (and the proposal) quotes only numbers produced by the latest eval
report, with the date, the number of cases and the caveat that they are measured on synthetic data.
If an eval was not run, it is not quoted.
