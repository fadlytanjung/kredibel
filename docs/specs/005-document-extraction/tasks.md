# Tasks 005 — Document Extraction

## Phase 0 — Spike

- [ ] **T005-01** Spike S1 (see plan): Gemini page-image accuracy at `high` vs `ultra_high`, tokens per page, verifier agreement on digital and scanned S1, Enterprise OCR processor created; numbers recorded in docs/02 §6 and docs/21 §3.2; raw outputs saved as recordings.

## Phase 1 — Pure domain (TDD)

- [ ] **T005-02** **TDD** `normalize.py` amounts (all formats in AC-005-10, negative, CR/DB, empty, garbage → None + note).
- [ ] **T005-03** **TDD** `normalize.py` dates (numeric and English month names) and year inference across Dec/Jan.
- [ ] **T005-04** **TDD** counterparty extraction from common prefixes.
- [ ] **T005-05** **TDD** `verify.py` row anchoring and band/column matching: identical values; wrong column; value outside any band; multi-line description. (AC-005-11)
- [ ] **T005-06** **TDD** `verify.py` coverage check: AI drops a row → one witness-only row; AI invents a row → `SINGLE_SOURCE`; white-out + overlay fixture → `CONFLICT`. (AC-005-12, AC-005-13)
- [ ] **T005-07** **TDD** header search, agreement formula, value choice, `Provenance`. (AC-005-11, AC-005-15)
- [ ] **T005-08** **TDD** `bbox.py` union boxes and OCR polygon conversion (fixture from the generator). (AC-005-16)
- [ ] **T005-09** Extraction findings builders `E01`, `E02`, `E03`, `E05`.

## Phase 2 — Adapters

- [ ] **T005-10** `pdf_inspector` (metadata, revisions, fonts, words per page). (AC-005-1, AC-005-8)
- [ ] **T005-11** `docai_ocr` adapter + mapper to words with boxes; raw save. (AC-005-8)
- [ ] **T005-12** **TDD** per-page extraction cache (hit skips the paid call; `ocr_only` and `off` modes; usage counts hits). (AC-005-19)
- [ ] **T005-13** `gemini_gateway` (schema, retries, schema retry, media resolution, labels, usage). (AC-005-5, AC-005-6)
- [ ] **T005-14** Prompts `classify_document.md`, `read_statement_page.md`, `read_invoice_page.md`; `prompt_registry`.
- [ ] **T005-15** Recording tool + `RecordedGemini`/`RecordedOcr` fakes; record S1–S3 seed-1 and the scanned S1 variant.

## Phase 3 — Nodes

- [ ] **T005-16** `inspect_pdf` node. (AC-005-1)
- [ ] **T005-17** `classify_document` node incl. sales/purchase rule and low-confidence handling. (AC-005-2, AC-005-3, AC-005-4)
- [ ] **T005-18** `read_page` node: page 1 first, then bounded parallel pages with header context; blank pages skipped; quarantine respected; page status updates. (AC-005-5, AC-005-6, AC-005-7)
- [ ] **T005-19** `witness_pages` node: text layer or OCR per page; fallbacks. (AC-005-8, AC-005-9)
- [ ] **T005-20** `verify_pages` node: normalize, verify, provenance, persist (chunked upserts, deterministic IDs, masked account, `matchedAccountId`), usage. (AC-005-14, AC-005-17, AC-005-20)

## Phase 4 — Verify

- [ ] **T005-21** Scenario test (recordings): S1 rows == truth 100%, agreement ≥ 0.95, box coverage ≥ 98% (scanned ≥ 90%); S2 edited credit `AGREED`. (AC-005-16, AC-005-18)
- [ ] **T005-22** Run S1 on the deployed env with real services; compare to the recording run and to the cost estimate. (AC-005-20)
- [ ] **T005-23** Update `docs/20-implementation-status.md`; record deviations in docs/07.

## Phase 5 — P1

- [ ] **T005-24** `docai_parser` adapter (Form Parser table mapper, Invoice Parser mapper) + `consensus.py` three-source alignment (**TDD**). (AC-005-21)
- [ ] **T005-25** `escalate_pages` node with the per-case budget; `EXTRACTION_MODE=thorough`. (AC-005-21, AC-005-22)
