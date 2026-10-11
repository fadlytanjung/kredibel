# Tasks 003 — Document Intake

## Phase 1 — Domain

- [x] **T003-01** **TDD** `file_types.py` with fixtures (real PDF, ZIP renamed to `.pdf`, PNG, JPEG, XLSX, CSV with BOM, empty file). (AC-003-2)
- [x] **T003-02** **TDD** `page_triage.py`: usable, `(cid:…)` unusable, image-only, blank page. (AC-003-4)

## Phase 2 — API

- [x] **T003-03** **TDD** `DocumentService.upload`: limits and their error codes; page reservation; counters in the same transaction. (AC-003-3, AC-003-4)
- [x] **T003-04** **TDD** exact duplicates: same hash → `DUPLICATE` record, nothing stored, nothing enqueued, usage unchanged; concurrent uploads → one original. (AC-003-5)
- [x] **T003-05** Storage, rendering, task enqueue; `DOCUMENT_UPLOADED` event. (AC-003-4)
- [x] **T003-06** List, get, file, pages routes; **TDD** foreign IDs → 404. (AC-003-7, AC-003-11)
- [x] **T003-07** **TDD** delete cascade and months marked dirty; original-of-duplicate rule. (AC-003-10)

## Phase 3 — UI

- [ ] **T003-08** `UploadSheet` with camera input and duplicate notice; stories for each file state. (AC-003-1, AC-003-6)
- [ ] **T003-09** `DocumentsPage` with filters, badges and live status; visual tests at 390/834/1440. (AC-003-7, AC-003-8)
- [ ] **T003-10** `DocumentPage` (pages, read values, findings, matches, events). (AC-003-9)

## Phase 4 — Close

- [ ] **T003-11** Update `docs/20-implementation-status.md`.
