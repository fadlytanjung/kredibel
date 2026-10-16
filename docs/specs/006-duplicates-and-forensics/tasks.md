# Tasks 006 — Duplicates and Document Forensics

## Phase 1 — Duplicates

- [x] **T006-01** **TDD** `duplicates.py`: `D02` overlap vs adjacent periods and identical vs different rows; `D03` vs `D04`; `D05` total tolerance and pHash 8 vs 9; `D06` within and across files (same date, amount, account and reference; the later entry is the copy). (AC-006-1…4)
- [x] **T006-01a** **TDD** D05 image fallback respects contradictory receipt readings; unrelated
  S1 till rolls remain eligible, while missing-field duplicate photos still hold. (AC-006-3)
- [x] **T006-02** **TDD** holding: held records excluded from a figures function and from matching inputs; `DuplicateService` decisions flip and mark months dirty. (AC-006-5, AC-006-6) Held documents, records and ledger rows stay out of the month's figures and matching inputs (`month_data`, `profit_loss`); the decisions live in `ReviewService` (`CONFIRM_DUPLICATE` / `NOT_DUPLICATE`, months marked dirty), proven through the API by the S3 gate: figures equal S1's while copies are held, releasing a copy adds its values back (15 Oct 2026).
- [x] **T006-03** `detect_content_duplicates` node and `POSSIBLE_DUPLICATE` items. (AC-006-5) `D02`–`D05` in the duplicate node; `D06` in `parse_ledger` (the file's rows that repeat an earlier entry are held with a `D06` finding, a decision on a re-read is kept); the review items of spec 009 cover both, one item per copied journal entry, decided through `CONFIRM_DUPLICATE` / `NOT_DUPLICATE` on the entries. Built 15 Oct 2026.

## Phase 2 — Integrity

- [x] **T006-04** **TDD** `A01`/`A02` incl. property test and the witness-only rule. (AC-006-7)
- [x] **T006-05** [P] **TDD** `A04` for invoices and receipts. (AC-006-7)
- [x] **T006-06** **TDD** `M01`–`M04`, `M06` on fixture PDFs. (AC-006-8)
- [x] **T006-07** `E0x`, `X05`, `X06`; verdict; finding upsert rules. (AC-006-9…11) `E03` as a finding is written by `classify_document` with the `CONFIRM_TYPE` item (15 Oct 2026).
- [x] **T006-08** `inspect_file` and `check_document` nodes.

## Phase 3 — Scenarios

- [x] **T006-09** Scenario tests S1, S2, S3. (AC-006-12, AC-006-13) `test_scenario_forensics.py`: every S1 statement `CLEAN`, S2's March `TAMPERED` with `A01` at the edited row, `A02`, `M01`–`M03` (`M04` on the workflow path), S3's `D02`/`D03`/`D05` held and `D01` refused at upload; S3's figures equal S1's through the API (009). `D06` stays open with the ledger copy.

## Phase 4 — Close

- [x] **T006-11** **TDD** `D03` on a copy whose pay-to account differs from the original's is `HIGH`,
  names both masked accounts and says so in its title: a payment diversion signal that `X08` cannot
  see while the copy is held. Decided 13 Oct 2026 after the synthetic run (S1 then S4), where the
  diverted Roastline invoice was held as a plain `MEDIUM` copy. (AC-006-5)
- [x] **T006-10** Update `docs/20-implementation-status.md`. (kept current with every change; the duplicate and integrity rows record what is built and the deviations)
- [x] **T006-12** **TDD** A running-balance break right after a statement row that could not be kept
  (`ROW_DROPPED_ABOVE`) is `E01`, not a CRITICAL `A01`: the gap is our reading, not the page (16 Oct
  2026, a real scanned statement; docs/08 §2.3).
