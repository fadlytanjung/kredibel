# Tasks 005 — Reading

## Phase 1 — Pure parts

- [x] **T005-01** **TDD** `normalize.py` (amount formats, dates, direction, counterparty extraction, payment methods). (AC-005-7, edge cases)
- [x] **T005-02** **TDD** `verify.py` for statements: anchoring, columns, coverage, witness-only rows, conflicts, boxes. (AC-005-6)
- [x] **T005-03** [P] **TDD** `verify.py` for invoices and receipts. (AC-005-6)
- [x] **T005-04** **TDD** `ledger_parse.py`: both layouts, bad rows, 2% rule, layout signature, shape masking. (AC-005-10, AC-005-12)

## Phase 2 — Model calls

- [ ] **T005-05** Spike S1 and S3; record results in `docs/02`. (S1 done 12 Oct 2026, incl. ADR-023 grounding; S3 OCR open)
- [x] **T005-06** Prompts and schemas; `GeminiGateway` with cache and usage accounting. (AC-005-3, AC-005-9)
- [x] **T005-07** `classify_document` node incl. `NEEDS_INPUT` + `CONFIRM_TYPE`. (AC-005-1, AC-005-2) The `E03` finding, the item and `SET_TYPE` (the choice is kept on the document as `typeSetBy`, the workflow continues) built 15 Oct 2026.
- [x] **T005-08** `read_page` and `witness_pages` (text layer and OCR); `verify_pages` writing records. (AC-005-4…8)
  The OCR witness is not built yet: no adapter reads `DOCAI_OCR_PROCESSOR_ID`, so scans and photos
  have no witness (every value single-source, `E01`). Built 16 Oct 2026 with spec 022 phase B
  (T022-05): Document AI OCR reads every page without a usable text layer.
- [x] **T005-09** `propose_ledger_mapping` and `parse_ledger` incl. `CONFIRM_LEDGER_MAPPING`. (AC-005-11, AC-005-12)

## Phase 3 — Scenarios

- [ ] **T005-10** `make record` for S1 seed 1 (digital, scanned) and the receipt photos; scenario test: S1 reads every value of `truth.json` with agreement ≥ 0.95. (AC-005-4…8)
- [x] **T005-11** UI: the document page shows read values with their status and boxes; the mapping confirmation screen (shared with spec 009). (AC-005-11) (the `CONFIRM_LEDGER_MAPPING` item from the document workflow, `GET …/ledger-mapping`, `CONFIRM_MAPPING`, the review drawer `MappingEditor`, the waiting document's banner; proposal by code, the model mapper as a later fallback, docs/20 deviations)

## Phase 4 — P1

- [ ] **T005-12** Escalation and thorough mode. (AC-005-13, AC-005-14)

## Phase 5 — Close

- [x] **T005-13** Update `docs/20-implementation-status.md`. (Ledger import Built with its deviation, 15 Oct 2026; the reader rows stay as recorded)
- [x] **T005-14** **TDD** Statements that print the date once per day: a row with its own amount and
  a blank date cell is a transaction of the day above, in the layout, the grounding, the bank lines
  and `read_statement_page` v3 (docs/07 §6 rule 9; `test_statement_undated_rows.py`). Found 16 Oct
  2026 in a tester's real scanned statement: the same-day rows were dropped, so balances, totals and
  findings were wrong. (AC-005-4, AC-005-7)
