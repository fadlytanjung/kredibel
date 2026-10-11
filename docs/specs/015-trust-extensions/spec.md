# Spec 015 — Trust Extensions (P1)

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P1 (after the P0 cut line) |
| **Owner role** | A, B, C (one story each) |
| **Depends on** | 004, 006, 008, 009 |
| **Requirements** | FR-072, FR-073, P1-03 … P1-07, P1-09 |
| **Design** | [`docs/07`](../../07-document-intelligence.md) §3.2; [`docs/08`](../../08-risk-engine.md) §2.4–§2.5; [`docs/17`](../../17-observability.md) §5 |

## Summary

Independent additions that make the product harder to fool and easier to trust, each behind a flag:
Model Armor screening, visual forensics, revision diffs, the run graph, month sign-off, exports, and
"split and upload" for long PDFs.

## User stories

### US-015-1: Hidden instructions are quarantined (`FEATURE_MODEL_ARMOR`)

- **AC-015-1** `screen_document` sends the original file to Model Armor (template `kredibel-docs`);
  a prompt-injection match quarantines the document: finding `S01_EMBEDDED_INSTRUCTIONS` (CRITICAL),
  no model call ever contains its content (gateway refuses), the witness still reads it, verdict at best
  `UNVERIFIABLE`. S6 passes with Model Armor on and off ([`docs/18`](../../18-synthetic-data.md) §5).

### US-015-2: Visual forensics (`FEATURE_VISUAL_FORENSICS`)

- **AC-015-2** `visual_examiner` reviews statement pages with key value regions; `V01` is MEDIUM, HIGH
  only when corroborated by `A01`, `M04` or `M05` on the same row or an overlapping box, never
  CRITICAL.

### US-015-3: What changed in the PDF (`FEATURE_REVISION_DIFF`)

- **AC-015-3** For a PDF with several revisions, the earliest revision's text is compared with the
  latest; a changed number makes `M03` CRITICAL with the before and after values shown in the
  evidence viewer; `M05` (covered text) and `A03`, `A05` are enabled.

### US-015-4: Run graph (`FEATURE_RUN_GRAPH`)

- **AC-015-4** A document or month page has "How this was processed": the run graph of
  [`docs/17`](../../17-observability.md) §5 from `runs.stages`, live while running, with duration,
  model, tokens and a one-line summary per node, and a "View trace" link for the team.

### US-015-5: Month sign-off (`FEATURE_SIGN_OFF`)

- **AC-015-5** A reviewer (or the owner) signs off a `RECONCILED` month; changes to it then return
  `409 MONTH_LOCKED`; reopening needs a reason; both are audited.

### US-015-6: Exports and long PDFs

- **AC-015-6** `GET /api/exports/reconciliation.csv?month=` returns matches, unmatched lines and the
  review log, with CSV-injection escaping.
- **AC-015-7** A PDF over the page limit offers "Split and upload": parts of ≤ 20 pages become
  documents; structure checks run once on the untouched original.

## Out of scope

Anything that changes P0 behaviour when its flag is off.
