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

- [x] **T003-08** `UploadSheet` with camera input and duplicate notice; stories for each file state. (AC-003-1, AC-003-6) The tray's list (16 Oct 2026, `features/upload/trayRows.ts`): files sending from this tab, then the workspace's uploads of the last day and any upload still waiting for a person (a held copy with **Decide**, a ledger with **Check columns**, a file that needs input or failed), newest first, at most six, each with its live state ("Reading page 2 of 3" with its bar) and the original linked; the mock `documents.html` draws it from `contracts/design/fixtures/documents.json`, `documents.spec.ts`.
- [x] **T003-09** `DocumentsPage` with filters, badges and live status; visual tests at 390/834/1440. (AC-003-7, AC-003-8)
- [x] **T003-09a** The library is one `DataTable` of the workspace's documents: chips by type with counts,
  search by name, type, status or month, 10 a page, sortable columns, rows opening the document. (AC-003-7)
- [x] **T003-10** `DocumentPage` (pages, read values, findings, matches, events). (AC-003-9)

## Phase 4 — Close

- [x] **T003-11** Update `docs/20-implementation-status.md`.
