# Tasks 006 — Duplicates and Document Forensics

## Phase 1 — Duplicates

- [ ] **T006-01** **TDD** `duplicates.py`: `D02` overlap vs adjacent periods and identical vs different rows; `D03` vs `D04`; `D05` total tolerance and pHash 8 vs 9; `D06` within and across files. (AC-006-1…4)
- [ ] **T006-02** **TDD** holding: held records excluded from a figures function and from matching inputs; `DuplicateService` decisions flip and mark months dirty. (AC-006-5, AC-006-6)
- [ ] **T006-03** `detect_content_duplicates` node and `POSSIBLE_DUPLICATE` items. (AC-006-5)

## Phase 2 — Integrity

- [ ] **T006-04** **TDD** `A01`/`A02` incl. property test and the witness-only rule. (AC-006-7)
- [ ] **T006-05** [P] **TDD** `A04` for invoices and receipts. (AC-006-7)
- [ ] **T006-06** **TDD** `M01`–`M04`, `M06` on fixture PDFs. (AC-006-8)
- [ ] **T006-07** `E0x`, `X05`, `X06`; verdict; finding upsert rules. (AC-006-9…11)
- [ ] **T006-08** `inspect_file` and `check_document` nodes.

## Phase 3 — Scenarios

- [ ] **T006-09** Scenario tests S1, S2, S3. (AC-006-12, AC-006-13)

## Phase 4 — Close

- [ ] **T006-10** Update `docs/20-implementation-status.md`.
