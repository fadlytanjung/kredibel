# Spec 010 — Trust Extensions (P1)

| | |
|---|---|
| **Status** | Ready (start only after the P0 cut line passes) |
| **Priority** | P1, in this order: ① Model Armor ② revision diff ③ run timeline ④ visual forensics ⑤ remaining checks + S4/S5 |
| **Owner role** | A: Agents (① ④) · B: Risk engine (② ⑤) · C: Frontend (③ and UI parts) |
| **Depends on** | 006, 008, 009 |
| **Requirements** | FR-050, FR-051, FR-052, FR-055, P1-01, P1-02, P1-03, P1-05, P1-06 |

## Summary

The features that make Kredibel's trust story memorable: documents screened before any model reads
them, the original value recovered from an edited PDF, a visual second opinion that cannot convict on
its own, and a visible agent trace.

## ① Model Armor screening (FR-050)

- **AC-010-1** With `FEATURE_MODEL_ARMOR=true`, `screen_document` sends each original file to Model
  Armor (`kredibel-docs` template) before any model call; the result is stored in `documents.screening`.
- **AC-010-2** On a prompt-injection match: `S01_EMBEDDED_INSTRUCTIONS` (CRITICAL, `detectedBy:
  MODEL_ARMOR`), `quarantined: true`, document status passes through `QUARANTINED`, verdict at best
  `SUSPICIOUS`, hard stop `EMBEDDED_INSTRUCTIONS`.
- **AC-010-3** The Gemini gateway refuses any call that includes content from a quarantined document
  (raises, logged); a quarantined document is read by the witness only (text layer or OCR, `WITNESS_ONLY`)
  and classified with text heuristics only (or `OTHER`). Test asserts **zero** gateway calls with quarantined content on S6.
- **AC-010-4** Model Armor errors do not fail the document: `screening.verdict = ERROR`, a LOW finding,
  processing continues (fail-open is visible, not silent).
- **AC-010-5** S6 with the flag on → `REFER` with `EMBEDDED_INSTRUCTIONS`; with the flag off →
  same recommendation as S1, and the memo contains no claim taken from the hidden text.

## ② Revision recovery (FR-052)

- **AC-010-6** For PDFs with > 1 revision, the earliest revision's text is extracted and diffed with the
  final text by position; changed numeric strings are stored as `revisionDiff[] {page, bbox, before,
  after}`.
- **AC-010-7** A numeric change raises `M03` to `CRITICAL` with facts `before`/`after`; on S2 the
  evidence viewer shows `1,250,000.00 → 7,250,000.00` on the edited row.

## ③ Run timeline (FR-055)

- **AC-010-8** Activity tab shows the latest run's stages with duration bars, model, tokens and outcome;
  per-document sub-rows; totals (time, tokens, pages read and cached, OCR pages, estimated USD).

## ④ Visual forensics (FR-051)

- **AC-010-9** With `FEATURE_VISUAL_FORENSICS=true`, `check_visual` sends each statement page image
  (150 dpi) plus the regions of key values to Gemini (`examine_page` prompt) and receives regions with
  `box_2d` and a kind/description/confidence; boxes are converted to normalized bboxes.
- **AC-010-10** `V01` is `MEDIUM`; it becomes `HIGH` only when corroborated by A01, M04 or M05 on the
  same row or an overlapping box (IoU ≥ 0.3), recording `corroboratedBy`. It never produces `TAMPERED`
  alone.
- **AC-010-11** Visual findings on S1 are reported in evals (E-VIS), not asserted in tests.

## ⑤ Remaining checks and scenarios

- **AC-010-12** Implement and enable A03, A05, M05, X02, X03, X04, R03, C03, C04, B02, B03, B05, B06, E04
  per [`docs/08`](../../08-risk-engine.md) §2, each with unit tests.
- **AC-010-13** S4 → `DECLINE` (`DSCR_BELOW_ONE`) with B01, B02, C01, C02; S5 → `REFER`
  (`SUSPICIOUS_DOCUMENT`) with X01 and M01 on May.

## Out of scope

Clarification interrupts via `RequestInput` unless spike S3 passed (then: own-account confirmation per
[`docs/06`](../../06-agent-design.md) §8, as an extra story).
