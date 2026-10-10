# Tasks 014 — Applicant Profile Intelligence

## Phase 1 — Domain (TDD)

- [ ] **T014-01** **TDD** `counterparties.py`: normalization, merge of spellings, role rules for every role in docs/08 §4.3, shares, facts. (AC-014-1, AC-014-3)
- [ ] **T014-02** **TDD** `profile_suggestions.py`: `BANK_ACCOUNT`, `TAX_ID`, `ADDRESS`, `LEGAL_NAME` rules and confidences; deterministic IDs; rejected values skipped; `CONFLICT`. (AC-014-5 – AC-014-8)
- [ ] **T014-03** **TDD** `profile_checks.py`: `X05` with aliases and declared holders, `X06`. (AC-014-11, AC-014-12)

## Phase 2 — Nodes and LLM

- [ ] **T014-04** Categorizer schema + prompt: counterparty name and kind; recorded outputs refreshed. (AC-014-2)
- [ ] **T014-05** `build_counterparties` node; `transactions.counterpartyId`; facts published. (AC-014-1, AC-014-3, AC-014-4)
- [ ] **T014-06** `build_applicant_profile` node; suggestions upserted create-if-absent; `pendingSuggestions` counter. (AC-014-5 – AC-014-7)
- [ ] **T014-07** Scenario tests (recordings): S1 counterparties and suggestions equal `truth.json`; undeclared-account fixture. (AC-014-1, AC-014-5, AC-014-12)

## Phase 3 — Service and API

- [ ] **T014-08** **TDD** `ApplicantService.decide_suggestion`: accept per field writes the profile (+ hash) in one transaction; reject; events; `409`/`422` cases. (AC-014-9, AC-014-10)
- [ ] **T014-09** Endpoints: suggestions list/decide, applicant events, counterparties. (AC-014-3, AC-014-9)

## Phase 4 — Frontend

- [ ] **T014-10** Applicant tab: profile block (edit reuses the 003 form), suggestions panel with evidence chips, counterparties panel. (AC-014-15)
- [ ] **T014-11** Cash flow filter by counterparty. (AC-014-4)
- [ ] **T014-12** Memo "business" section cites the counterparty facts (with spec 008 prompt). (AC-014-16)

## Phase 5 — P1

- [ ] **T014-13** **TDD** `RELATED_PARTY` and `KEY_CLIENT`/`KEY_SUPPLIER` suggestions; accept with roles. (AC-014-9, AC-014-10)
- [ ] **T014-14** **TDD** related-party categorization step + `B07`; `X07`; S7 scenario test. (AC-014-13, AC-014-14)
- [ ] **T014-15** Pre-fill on upload (`PREFILL_ON_UPLOAD`), sharing the page-1 cache key with the run. (AC-014-17)
- [ ] **T014-16** Applicant list and detail pages. (AC-014-18)

## Phase 6 — Verify

- [ ] **T014-17** On the deployed env: S1 run → Applicant tab shows the tax ID and address suggestions with evidence; accept them; re-run shows no duplicates.
- [ ] **T014-18** Update `docs/20-implementation-status.md`.
