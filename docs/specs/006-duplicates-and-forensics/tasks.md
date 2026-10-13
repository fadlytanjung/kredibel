# Tasks 006 — Duplicates and Document Forensics

## Phase 1 — Duplicates

- [x] **T006-01** **TDD** `duplicates.py`: `D02` overlap vs adjacent periods and identical vs different rows; `D03` vs `D04`; `D05` total tolerance and pHash 8 vs 9; `D06` within and across files. (AC-006-1…4)
- [x] **T006-01a** **TDD** D05 image fallback respects contradictory receipt readings; unrelated
  S1 till rolls remain eligible, while missing-field duplicate photos still hold. (AC-006-3)
- [ ] **T006-02** **TDD** holding: held records excluded from a figures function and from matching inputs; `DuplicateService` decisions flip and mark months dirty. (AC-006-5, AC-006-6) (holding done: document and records flagged, released when the earlier copy goes; exclusion from figures and matching comes with spec 007, decisions with spec 009)
- [ ] **T006-03** `detect_content_duplicates` node and `POSSIBLE_DUPLICATE` items. (AC-006-5) (node done for `D02`, `D03`, `D04`, `D05` incl. the page-1 image hash; the review item comes with spec 009; `D06` with ledger import)

## Phase 2 — Integrity

- [x] **T006-04** **TDD** `A01`/`A02` incl. property test and the witness-only rule. (AC-006-7)
- [x] **T006-05** [P] **TDD** `A04` for invoices and receipts. (AC-006-7)
- [x] **T006-06** **TDD** `M01`–`M04`, `M06` on fixture PDFs. (AC-006-8)
- [ ] **T006-07** `E0x`, `X05`, `X06`; verdict; finding upsert rules. (AC-006-9…11) (done except `E03` as a finding, which comes with the `CONFIRM_TYPE` item of spec 009)
- [x] **T006-08** `inspect_file` and `check_document` nodes.

## Phase 3 — Scenarios

- [ ] **T006-09** Scenario tests S1, S2, S3. (AC-006-12, AC-006-13)

## Phase 4 — Close

- [x] **T006-11** **TDD** `D03` on a copy whose pay-to account differs from the original's is `HIGH`,
  names both masked accounts and says so in its title: a payment diversion signal that `X08` cannot
  see while the copy is held. Decided 13 Oct 2026 after the synthetic run (S1 then S4), where the
  diverted Roastline invoice was held as a plain `MEDIUM` copy. (AC-006-5)
- [ ] **T006-10** Update `docs/20-implementation-status.md`.
