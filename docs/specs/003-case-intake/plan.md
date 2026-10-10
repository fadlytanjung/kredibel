# Plan 003 — Case Intake

## Backend

| File | Content |
|---|---|
| `domain/models/applicant.py` | `Applicant`, `IndividualProfile`, `CompanyProfile`, `BankAccount`, `RelatedParty`, `ApplicantSummary`; validation (type block, ownership ≤ 100%, ID last 4 only) |
| `domain/models/case.py` | `LoanRequest`, `Case` (with applicant snapshot), `CaseStatus`, `Money` value object |
| `domain/accounts.py` | account-number normalization, mask, deterministic `accountId`, hash `sha256(orgId:digits)` |
| `domain/page_triage.py` | text-layer usability test and blank-page test (thresholds from `forensics.v1.yaml` `verification`) |
| `domain/models/document.py` | `Document`, `DocStatus`, `DocType` |
| `domain/case_state.py` | transition table (only `DRAFT`/`INFO_REQUESTED` editability used here; full table in 009) |
| `ports/repository.py` | `CaseRepository` Protocol: `create_case`, `get_case`, `list_cases`, `update_case`, `add_document`, `get_document`, `list_documents`, `remove_document`, `append_event` (all org-scoped) |
| `ports/blob_store.py` | `BlobStore`: `put`, `get_stream`, `delete_prefix`, `exists` |
| `ports/page_renderer.py` | `PageRenderer`: `count_pages`, `render(page, dpi)`, `is_encrypted` |
| `adapters/firestore_repo.py` | implementation; minor-unit money mapping; atomic count updates in transactions; events in the same transaction |
| `adapters/gcs_store.py` | implementation (sync client in thread) |
| `adapters/page_renderer.py` | pypdfium2 + pikepdf (`is_encrypted`), PIL for PNG/JPEG |
| `services/applicant_service.py` | create/get/list/update applicants; add/remove bank accounts (hash in `orgPrivate`) and related parties; applicant events |
| `services/case_service.py` | create (existing or inline applicant, entitlement check), list/get/update with validation, snapshot refresh, events |
| `services/document_service.py` | sniff type (magic bytes), plan limits (size/pages/count), sha256 dedupe, store original, **split**: render pages + thumbs, triage each page, register; P1 `split=auto` |
| `api/applicants.py`, `api/cases.py`, `api/documents.py` | thin routers per `contracts/openapi.yaml` |
| `tests/fakes/` | `InMemoryRepository`, `InMemoryBlobStore`, `FakePageRenderer` |

## Frontend

| File | Content |
|---|---|
| `entities/case/api.ts`, `entities/document/api.ts` | query/mutation hooks |
| `entities/case/ui/StatusBadge.tsx`, `entities/document/ui/DocTypeBadge.tsx` | atoms |
| `shared/ui/DataTable.tsx`, `Dropzone.tsx`, `MoneyText.tsx`, `Tabs.tsx` | design system additions |
| `pages/CaseListPage.tsx` | table + filters |
| `pages/CaseNewPage.tsx` + `features/create-case/` | three-step wizard (applicant → loan request → documents) |
| `features/onboard-applicant/` | Individual \| Company segmented form; optional bank accounts and people; applicant picker |
| `entities/applicant/` | hooks, mappers, `ApplicantTypeIcon` |
| `pages/CaseWorkspacePage.tsx` | header + tabs shell (tabs other than Documents show "Available after analysis") |
| `widgets/DocumentsPanel/` + `features/upload-documents/` | dropzone, parallel uploads, per-file errors, list |

## Constitution check

P1 ✔ · P3 ✔ (sha256, page renders for later evidence) · P4 ✔ (magic bytes, limits, org scoping) ·
P7 ✔ (Firestore, GCS) · P8 ✔ · P10 ✔ (validators unit-tested)

## Risks

- Rendering 20 pages synchronously could approach the 60 s web timeout on cold start → render at 150 dpi
  with a cap of 4,000 px; measure; fall back to rendering thumbnails only at upload and full pages in
  the worker if needed.
- Account numbers are personal data even when synthetic → never logged; masked in responses; hash in
  `orgPrivate` (docs/14 §6).
