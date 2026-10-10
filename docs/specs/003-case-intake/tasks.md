# Tasks 003 — Case Intake

## Phase 1 — Domain & ports

- [ ] **T003-01** **TDD** `Money` value object: parse/format decimal strings, minor units round-trip, rejects floats. 
- [ ] **T003-02** Case and document models + enums; `CaseCreate` validation mirrors `contracts/openapi.yaml`. (AC-003-2)
- [ ] **T003-21** **TDD** applicant models and validation (type blocks, ownership ≤ 100%, ID last 4); `accounts.py` mask, ID, hash. (AC-003-17, AC-003-18, AC-003-19)
- [ ] **T003-22** **TDD** `page_triage.py`: usable, unusable (`cid` glyphs), none, blank. (AC-003-22)
- [ ] **T003-03** Ports `CaseRepository`, `BlobStore`, `PageRenderer`; in-memory fakes in `tests/fakes/`.

## Phase 2 — Services (TDD)

- [ ] **T003-23** **TDD** `ApplicantService` create/get/list/update, bank accounts (hash in `orgPrivate`, duplicate → 409) and related parties; events. (AC-003-17 – AC-003-20)
- [ ] **T003-04** **TDD** `CaseService.create/list/get/update` with existing or inline applicant, snapshot refresh, entitlement check, `CASE_NOT_EDITABLE` and events. (AC-003-1, AC-003-3, AC-003-6, AC-003-23)
- [ ] **T003-05** **TDD** type sniffing by magic bytes; size/page/count limits; encrypted detection. (AC-003-8, AC-003-9)
- [ ] **T003-06** **TDD** duplicate detection by sha256 → `DUPLICATE_DOCUMENT` with `existingDocId`. (AC-003-10)
- [ ] **T003-07** **TDD** upload stores original + pages + thumbs at the right paths, triages each page into `pages[]`; plan limits; event; count increment. (AC-003-9, AC-003-11, AC-003-13, AC-003-22)
- [ ] **T003-08** **TDD** remove in `DRAFT` deletes prefix + doc + event + count; outside → 409. (AC-003-12, AC-003-16)

## Phase 3 — Adapters & API

- [ ] **T003-09** `adapters/firestore_repo.py` (cases, documents, events) with transactions; integration test against the emulator if available, else contract test with fakes.
- [ ] **T003-10** [P] `adapters/gcs_store.py`, `adapters/page_renderer.py`.
- [ ] **T003-11** Routers `api/applicants.py`, `api/cases.py`, `api/documents.py` (incl. `/file` and `/pages/{n}` streaming with workspace check). (AC-003-15)
- [ ] **T003-12** **TDD** integration: every route with a foreign `caseId` → 404. (AC-003-5)

## Phase 4 — Frontend

- [ ] **T003-13** `npm run gen:api`; entity hooks for cases/documents.
- [ ] **T003-14** Case list page with filters and empty state. (AC-003-4)
- [ ] **T003-15** New case wizard: applicant step (picker + Individual | Company form with optional bank accounts and people), loan request step, documents step. (AC-003-1, AC-003-2, AC-003-21)
- [ ] **T003-16** Workspace shell (header, tabs, default-tab rule from docs/11 §4).
- [ ] **T003-17** Documents tab: dropzone with plan limits shown, parallel uploads (3), per-file progress and errors; list with thumbnails and Digital/Scanned badge; remove. (AC-003-7, AC-003-9, AC-003-14, AC-003-16)
- [ ] **T003-18** Component tests (MSW) for upload error states.

## Phase 5 — Verify

- [ ] **T003-24** (P1) `split=auto`: original kept once, parts created and linked; "Split and upload" in the `TOO_MANY_PAGES` error. (AC-003-24)
- [ ] **T003-19** Manual: onboard Sunrise Coffee Roasters as a company with one bank account and one beneficial owner; upload S1 seed-1 files on the deployed env; thumbnails and Digital badges appear; duplicate rejected.
- [ ] **T003-20** Update `docs/20-implementation-status.md`.
