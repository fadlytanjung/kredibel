# 15 — Testing & Evaluation

> Tests prove the code does what the spec says. Evals measure how well the models do their part.
> Tests gate merges; evals inform decisions (constitution P10).

---

## 1. Layers

| Layer | What | Runs | Gate? | Location |
|---|---|---|---|---|
| Unit | Domain functions: duplicate keys, checks, `reconcile_month`, risk levels, money flow, verifier, normalizers, ledger parser, policy and plan loaders, access rules, grounding guard, upcasters | every `make check` | ✔ | `backend/tests/unit` |
| Integration | API routes with fakes for every port; workspace isolation; roles; problem+json; review actions | every `make check` | ✔ | `backend/tests/integration` |
| Scenario | Both workflows on synthetic scenarios with **recorded** Gemini and OCR outputs (parsers P1) | every `make check` | ✔ | `backend/tests/scenarios` |
| Migration | Every migration on a fixture database in the Firestore emulator: dry run, run, re-run (idempotent), resume after a crash | every `make check` | ✔ | `backend/tests/migrations` |
| Frontend unit/component | Formatters, citation parser, Sankey layout adapter, widgets with MSW | every `make check` | ✔ | `frontend/src/**/*.test.ts(x)` |
| Stories and visual | Storybook interaction + axe; Playwright screenshots at 390/834/1440 px | every `make check` | ✔ | `frontend/src/**/*.stories.tsx`, `frontend/e2e/visual` |
| Contract | Generated TS types compile; OpenAPI validates; backend response models match `openapi.yaml` | every `make check` | ✔ | both |
| E2E smoke | Playwright demo path against local or deployed env | before demo recording | manual | `frontend/e2e` |
| **Evals** | Real models on scenario variants; DeepEval for the assistant (P1) | `make evals` | ✘ | `backend/evals` |

Coverage targets: `domain/` ≥ 90% lines, `services/` ≥ 80%. Coverage is a floor, not the goal.

---

## 2. Gates per change (`make check`)

### 2.1 Lint and types

`ruff` (lint + format), `pyright` (strict) on `app/`; ESLint (with
`i18next/no-literal-string`) and `tsc --noEmit` in the frontend.

### 2.2 Architecture

`import-linter` contracts: `domain` imports nothing from other layers; `api` never imports
`adapters`; LLM-facing code imports no repository write methods
([`13`](13-design-patterns-and-conventions.md) §2).

### 2.3 Contracts

`openapi.yaml` validates; `npm run gen:api` produces no diff; Firestore indexes and rules files
parse; the rules tests run in the emulator (a user of workspace A reads nothing of workspace B).

### 2.4 Policy and plans

`contracts/policy/*.yaml` and `plans.v1.yaml` load into their Pydantic models; every check code in
`forensics.v1.yaml` is registered; every finding code has a next-step entry in `risk.v1.yaml`.

### 2.5 Data schema drift

`tools/checks/schema_snapshot.py` compares the repository models with
`contracts/data/schema-snapshot.json`; a changed model without a `schemaVersion` bump, an upcaster
and a migration (or an "additive" note) fails ([`22`](22-data-migrations.md) §7).

### 2.6 UI quality gates

| Gate | Tool | Fails when |
|---|---|---|
| Tokens current | `make tokens-check` (`tools/design/build_tokens.py --check`) | generated CSS differs from `contracts/design/tokens.json`, or a declared contrast pair is below WCAG AA |
| No raw styles | `tools/checks/no_raw_styles.py` | a hex or `rgb()` colour, an arbitrary Tailwind value (`p-[13px]`) or an inline `style=` appears outside the allow-list (charts' computed geometry) |
| Component states | Storybook test runner | an interaction test fails, or axe reports a serious or critical violation in any story |
| Visual regression | Playwright `toHaveScreenshot` at 390, 834 and 1440 px, fixed data and fonts | a pixel diff above 0.1% on a key story or screen; baselines change only in a reviewed PR with screenshots |
| Accessibility E2E | `@axe-core/playwright` | any screen at any width has a serious or critical violation |
| Performance | Lighthouse CI (mobile profile) on the dashboard and the review queue | performance < 85, accessibility < 95, best practices < 95, or first-load JS > 250 KB gzip |
| Responsive | Playwright at 360 px | horizontal page scroll, or a touch target smaller than 44 px |

---

## 3. Ground truth

The synthetic generator ([`18`](18-synthetic-data.md)) writes, next to every scenario, a
`truth.json` with:

- every statement row, invoice, receipt and ledger row **as generated**, with a stable `key`;
- the tampering and duplication applied (technique, document, row, field, before and after);
- the intended matches (`AUTO` or `PROPOSED`) and the rows that must stay unmatched;
- expected verdict, risk level, finding codes and duplicate state per document;
- expected state, risk level, minimum auto-match rate, month findings, review items by kind and key
  figures per month;
- category label per bank line;
- the workspace as onboarded, the expected profile suggestions, counterparties and top money flows.

Tests and evals read this file; nobody hand-writes expected values.

---

## 4. Unit and scenario test highlights

| Area | Must-have tests |
|---|---|
| Normalization | English and dot-grouped amounts; `CR/DB` suffixes; parentheses; month names; year inference across December/January; receipt payment methods |
| Page triage | Usable text layer; `(cid:…)` glyphs → unusable; image-only → none; white page → blank |
| Verifier | AI = witness → agreement 1.0; AI drops a row → one witness-only row and no CRITICAL A01 across it; value in the wrong column → `CONFLICT`; white-out + overlay → `CONFLICT`, never `AGREED`; boxes from witness tokens |
| Ledger import | Sniffed delimiter and encoding; debit/credit and signed-amount layouts; date formats; bad rows listed with numbers; > 2% bad rows reopens the mapping; same header → same layout signature |
| Duplicates | `D01` by hash; `D02` overlap by 1 day vs adjacent periods (no overlap); `D03` vs `D04` (same number, different total); `D05` by pHash at distance 8 and 9; `D06`; `D07` with two debits for one invoice; held values excluded from figures and matching; confirm/reject changes the month |
| A01/A02 | Property test: any generated consistent statement → no A01; changing one credit without touching balances → exactly one A01 at that row |
| M03/M04 | Fixture PDFs: signed-only revision → MEDIUM; content-changed revision → HIGH; one value in a different font → M04 on that row |
| Reconciliation | Exact, net-of-withholding, split (2 and 3 parts), one credit for two invoices, not-due, waiting for statement; ambiguity margin → `PROPOSED` never `AUTO`; a `CONFLICT` value never auto-matches; rejected proposals not proposed again; manual matches kept across re-runs |
| **Order independence** | Property test (hypothesis): for random permutations of a month's inputs, `reconcile_month` returns identical matches, items and figures; S5 equals S1 by deterministic ID |
| Month runs | Generation check: an older run ends `SUPERSEDED` and writes nothing; burst of 10 uploads → one effective run |
| Risk | Each document and month rule of `risk.v1.yaml`; `TAMPERED` → month `CRITICAL`; next steps come from the catalog in order |
| Money flow | Σ sources = Σ uses per account; "Kept in the account" vs "Taken from balance"; held lines excluded; transfers hidden by default |
| Counterparties & suggestions | Role rules; merging spellings; unnamed buckets; accounts seen per supplier; deterministic suggestion IDs; rejected values never return |
| Review actions | Every (kind, action) pair: allowed ones succeed and mark the month dirty; others → `422 ACTION_NOT_ALLOWED`; resolved twice → `409` |
| Access (P1 roles) | Table-driven: every endpoint × role from [`10`](10-api-contract.md) §5 |
| Plans | Every limit at, below and above the boundary; exact duplicates not counted; trial expiry by injected clock; concurrent uploads at the limit |
| Grounding guard | `IDR 1,250,000`, `IDR 1.25 million`, `1,250,000`, `64%` all match their facts; `1.25M` is rejected as ambiguous; an unmatched number fails with the sentence quoted; turn-scoped `fact:q_…` IDs valid only in their answer |
| Workspace isolation | Every route with a foreign record ID → 404; no workspace → `403 WORKSPACE_REQUIRED` |
| Scenario | S1–S5 produce exactly the expected P0 codes, verdicts, duplicates, matches, review items and risk levels |

---

## 5. Evals

Run on **5 seeds × each scenario** (25 P0 cases, plus the scanned S1 variant) against real Gemini
and Document AI OCR (and Form/Invoice Parser for the `thorough` comparison). Results go to
`backend/evals/reports/<YYYY-MM-DD>.md` and a JSON twin for charts.

| Suite | Measures | Target (prototype) |
|---|---|---|
| **E-CLS** classification | Accuracy, confusion matrix by `docType` (incl. receipts and ledger files) | ≥ 0.95 |
| **E-EXT** reading | Row-level precision/recall/F1 on `(date, amount, direction)` for the AI reader alone and after verification; header and receipt field accuracy; agreement distribution; box coverage; **cost per page**; digital vs scanned vs photo; `adaptive` vs `thorough` on S1 seed 1 | Verified F1 ≥ 0.98 on digital PDFs, ≥ 0.95 on scans and photos; ≤ USD 0.01 per page |
| **E-MAP** ledger mapping | Proposed mapping equals the truth for the CSV and XLSX layouts | 10/10 |
| **E-DUP** duplicates | Recall and precision per technique (T7–T11, `D07` fixture); duplicates counted in figures | Recall 100%; 0 false holds on S1; 0 counted twice |
| **E-FOR** forensics | Per-document verdict confusion matrix; recall per seeded technique; **false `TAMPERED` on clean docs** | Recall 100% for seeded P0 techniques; 0 false `TAMPERED` |
| **E-REC** reconciliation | **Auto-match rate** on S1; **wrong automatic matches** (an `AUTO` match not in truth); `PROPOSED` cases never auto-matched; S5 = S1 | ≥ 85%; **0**; 100%; identical |
| **E-RSK** risk | Month and document risk levels vs truth; next steps include the expected catalog entries | 100% |
| **E-CAT** categorization | Macro-F1 vs labels; share by rule, match, model; `UNKNOWN` rate | Macro-F1 ≥ 0.85 |
| **E-CPTY** counterparties & suggestions | Role accuracy and merge precision; suggestion precision/recall | Role accuracy ≥ 0.95; suggestion precision ≥ 0.9 |
| **E-EXP** month explanations | Grounding pass rate on first attempt and after a retry; rubric review of 6 explanations (§5.3) | ≥ 90% first attempt; 100% verified or template |
| **E-VIS** visual (P1) | Visual findings that overlap a seeded edit (IoU ≥ 0.3) vs total visual findings | Report only |
| **E-SEC** injection (P1) | S6 variants flagged by Model Armor; **zero model calls containing quarantined content** (asserted from gateway logs) | 100% / 0 |
| **E-AST** assistant (P1) | DeepEval metrics and ADK tool trajectories (§5.1, §5.2) | see §5.1 |
| **E-LBL** labels (P1) | AI agreement with person-checked labels per task (`DOC_TYPE`, `PAGE_TYPE`, `CATEGORY`); calibration: accuracy per confidence bucket of `learning.v1.yaml` vs the bucket's confidence; `aiDisagreesWithPerson` after re-runs; same results under IFRS and US GAAP except the documented cash-flow classes. On synthetic data the "person" is `truth.json` | Report; calibration gap ≤ 0.10 per bucket; 0 person labels overwritten |
| **E-PERF** latency & cost | p50/p95 per node, per document and per month run; pages read, cached, OCR'd, escalated; tokens; estimated USD | NFR-01; ≤ USD 0.40 for S1's statements and invoices |

### 5.1 DeepEval for the Finance Assistant (P1)

[DeepEval](https://deepeval.com) is an open-source (Apache-2.0) pytest-style evaluation library. We
run it locally and in CI jobs only, with **Gemini on Agent Platform as the judge** (DeepEval's
`GeminiModel` with `project` and `location`, or `deepeval set-gemini --model … --project …
--location …`); no third-party evaluation cloud is used.

```python
# backend/evals/assistant/test_assistant_deepeval.py — sketch
from deepeval import assert_test
from deepeval.models import GeminiModel
from deepeval.metrics import (AnswerRelevancyMetric, FaithfulnessMetric,
                              ContextualRecallMetric, ToolCorrectnessMetric, GEval)
from deepeval.test_case import LLMTestCase, LLMTestCaseParams, ToolCall

judge = GeminiModel(model=settings.eval_judge_model, project=settings.gcp_project,
                    location="global", temperature=0)

grounded = GEval(
    name="Cites only Kredibel facts",
    criteria="Every amount in the answer is followed by a [[…]] marker and equals a value in the retrieval context.",
    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.RETRIEVAL_CONTEXT],
    model=judge, threshold=0.9)

def test_march_payments(case):                      # case loaded from assistant_cases.yaml
    answer, tool_calls, context = run_assistant(case)  # real agent, S1 seed 1 workspace in the emulator
    tc = LLMTestCase(input=case.question, actual_output=answer.text,
                     expected_output=case.expected_answer,
                     retrieval_context=context,          # tool results + retrieved chunks, as text
                     tools_called=[ToolCall(name=t.name, input_parameters=t.args) for t in tool_calls],
                     expected_tools=[ToolCall(name=n) for n in case.expected_tools])
    assert_test(tc, [FaithfulnessMetric(model=judge, threshold=0.9),
                     AnswerRelevancyMetric(model=judge, threshold=0.8),
                     ContextualRecallMetric(model=judge, threshold=0.8),
                     ToolCorrectnessMetric(threshold=1.0),
                     grounded])
```

| Metric | What it catches | Threshold |
|---|---|---|
| Faithfulness | Claims not supported by the tool results and retrieved chunks | ≥ 0.9 |
| Answer relevancy | Answers that drift from the question | ≥ 0.8 |
| Contextual recall | Retrieval or tools that miss what the expected answer needs | ≥ 0.8 |
| Tool correctness | Wrong or missing tools (e.g. answering a total from retrieval instead of `get_period_summary`) | 1.0 |
| G-Eval "cites only Kredibel facts" | Numbers without markers or markers that do not match | ≥ 0.9 |

The grounding guard is deterministic and already blocks unsupported numbers at runtime; DeepEval
measures the quality around it (relevance, completeness, tool choice). The case file
`backend/evals/assistant/assistant_cases.yaml` holds 20 questions over S1–S4: totals, a counterparty's
payments, "why is March critical?", unpaid invoices, a duplicate explanation, a money-flow question
(expects a chart part), a preference ("show amounts in thousands") and two out-of-scope questions
that must be declined.

### 5.2 ADK tool trajectories

The same cases are also exported as an ADK eval set (`backend/evals/assistant/*.evalset.json`) and
run with `adk eval` to compare the tool trajectory (names and key arguments) and the final response.
This keeps the check inside the ADK tooling the team already uses, and the run graph
([`17`](17-observability.md) §5) shows each case's trace for debugging.

### 5.3 Explanation rubric (manual, 6 month explanations)

| Criterion | 1 | 3 | 5 |
|---|---|---|---|
| Accuracy | wrong figures | minor slips | every figure verified |
| Evidence | few citations | most claims cited | every claim cited |
| Usefulness | no clear next step | generic steps | the steps a bookkeeper would take, in order |
| Tone | alarmist or vague | neutral | precise, calm, actionable |

---

## 6. Recordings (keeping CI offline)

`make record SCENARIO=S2 SEED=1` runs the real Gemini readers, the ledger mapper, OCR (scanned and
photo variants) and, for P1, the parsers once and stores their raw outputs **per page** under
`backend/tests/scenarios/recordings/<scenario>/<seed>/`. The scenario tests use `RecordedGemini`,
`RecordedOcr` and `RecordedParser` fakes that replay them by `(sha256, page, model or processor,
prompt version)`. The text-layer witness and the ledger parser need no recording (they run locally).
Re-record when a prompt version changes; the test fails loudly if a recording is missing.

---

## 7. What we publish

The README's **Results** section (and the proposal) quotes only numbers produced by the latest eval
report, with the date, the number of cases and the caveat that they are measured on synthetic data.
If an eval was not run, it is not quoted.
