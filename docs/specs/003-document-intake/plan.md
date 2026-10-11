# Plan 003 — Document Intake

## Backend

| File | Content |
|---|---|
| `domain/file_types.py` | content sniffing: PDF, PNG, JPEG, XLSX (zip with `xl/workbook.xml`), CSV (text sniff) |
| `domain/page_triage.py` | text-layer usability and blank-page tests ([`docs/07`](../../07-document-intelligence.md) §3.1) |
| `services/document_service.py` | `upload(principal, file, hint)`: validate → hash → exact-duplicate lookup → entitlement check and page reservation → store → render and triage → create document → enqueue; `delete(principal, doc_id)` |
| `adapters/page_renderer.py` | pypdfium2 render at 150 dpi, long edge ≤ 4,000 px, thumbnail 300 px |
| `adapters/spreadsheet_reader.py` | row count for limits (full parsing is spec 005) |
| `api/documents.py` | routes of [`docs/10`](../../10-api-contract.md) §2.2 |
| repository | `documents` with a single-field index on `sha256`; deletion cascade by `docId` in chunks of 400 |

The exact-duplicate lookup and the document creation run in one Firestore transaction keyed on the
SHA-256, so two simultaneous uploads cannot both become originals.

## Frontend

| File | Content |
|---|---|
| `features/upload/UploadSheet.tsx` | drop zone, file picker, camera input (`accept="image/*" capture`), per-file progress and errors, duplicate notice |
| `pages/DocumentsPage.tsx` | library with filters and responsive table |
| `pages/DocumentPage.tsx` | page viewer, read values, findings, matches, events |
| `entities/document/` | API hooks, Firestore listener hook `useDocumentLive(docId)` |

## Constitution check

P4 ✔ (type by content, limits server-side) · P7 ✔ (GCS, Firestore, Cloud Tasks) · P8 ✔ · P9 ✔

## Risks

- Rendering 20 pages near the request timeout on a cold start: render thumbnails first and let the
  worker render full pages if the budget is exceeded (flag `RENDER_IN_WORKER`).
