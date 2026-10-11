# Spec 016 — Labels and learning from people

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P1 (labels written by the workflows are cheap and start with 005 and 007) · dataset export later |
| **Owner role** | A (writers, examples) · B (decisions, categories) · C (Labels page) |
| **Depends on** | 005, 007, 013 |
| **Requirements** | P1-11, FR-074, FR-075 |
| **Design** | [ADR-016](../../adr/ADR-016-human-verified-labels-and-learning-loop.md); [`docs/09`](../../09-data-model.md) §3.19; [`docs/10`](../../10-api-contract.md) §2.10; [`docs/11`](../../11-frontend.md) §6.11; [`contracts/policy/learning.v1.yaml`](../../../contracts/policy/learning.v1.yaml), [`categories.v1.yaml`](../../../contracts/policy/categories.v1.yaml) |

## Summary

Every classification and categorization Kredibel makes becomes a **label** with the AI's value and
confidence. On the **Labels** page a person sees what the AI decided, page by page and line by line,
opens the page's extraction, and confirms or corrects it. A person's decision is **verified by a
person** and never overwritten. Verified labels feed the next runs as examples and remembered rules,
measure the AI's accuracy, and later (with consent) become tuning data.

## User stories

### US-016-1: Every AI decision is a label

- **AC-016-1** The document workflow writes a `DOC_TYPE` label per document and a `PAGE_TYPE` label per
  page; the categorization step writes a `CATEGORY` label per bank line; reading writes a
  `FIELD_VALUE` label for each value the readings did not agree on. Each carries value, confidence,
  source, model, prompt version, `runId`, `traceId` and `spanId`.
- **AC-016-2** Label IDs are deterministic (`lbl_` + hash of task and subject): a re-run updates the AI
  value of the same label; a `VERIFIED` or `CORRECTED` label keeps its final value and gets
  `aiDisagreesWithPerson = true` when the new AI value differs (TDD, property test over re-runs).
- **AC-016-3** `needsCheck` follows `learning.v1.yaml` thresholds per task.

### US-016-2: The page's extraction as Markdown

- **AC-016-4** For every read page the workflow writes `extractions/{docId}/p{n}.md` (page type and
  confidence, reading method, witness text, line items as a table, each value with both readings);
  `GET /api/documents/{docId}/pages/{n}/extraction.md` serves it after a workspace check.

### US-016-3: A person checks labels

- **AC-016-5** `/labels` lists labels with filters (task, status, needs a check, document, month,
  dataset use), sorted by confidence (lowest first), with the status sentence "212 of 1,284 labels
  checked by people; the AI was right on 94.6% of them".
- **AC-016-6** Confirm sets `VERIFIED`; correct sets `CORRECTED` with the new value and an optional
  note; both record who and when, write an event and, for `CATEGORY` and `DOC_TYPE`, mark the months
  dirty. Bulk confirm handles up to 200 labels; corrections are one by one.
- **AC-016-7** "Apply to similar lines" on a category correction creates a workspace rule for that
  counterparty and direction; later lines get `source = RULE` with a link to the correction.

### US-016-4: Accounting framework

- **AC-016-8** Settings › Profile offers **IFRS** (default) or **US GAAP**. A bank line's cash-flow
  class comes from `categories.v1.yaml` for that framework (e.g. `INTEREST_PAID`: financing under IFRS,
  operating under US GAAP); changing the framework re-derives classes for every month (one month run
  each) without touching categories.

### US-016-5: Learning now, training later

- **AC-016-9** The categorizer and classifier prompts include up to 5 verified examples from the same
  workspace (vector search, similarity ≥ 0.80); the gateway rejects examples from another workspace.
- **AC-016-10** Evals report AI accuracy against person-checked labels and confidence calibration per
  bucket (E-LBL, [`docs/15`](../../15-testing-and-evaluation.md) §5).
- **AC-016-11** (later) `POST /api/dataset-exports` writes masked JSONL and a BigQuery table from
  `VERIFIED` and `CORRECTED` labels, only with `learning.shareVerifiedLabels = true` (else
  `403 CONSENT_REQUIRED`) and at least the minimum examples per task (else `422`).

## Out of scope

Training or tuning a model during the hackathon; labels for explanations or assistant answers (those
are covered by evals and the grounding guard); labels shared between workspaces.
