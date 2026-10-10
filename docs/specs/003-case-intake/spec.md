# Spec 003 — Case Intake (applicant onboarding, cases, uploads)

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 |
| **Owner role** | C: Frontend (UI) + B or D (API) |
| **Depends on** | 001, 013 (phases 1–3: workspace and entitlements) |
| **Requirements** | FR-003, FR-004, FR-005, FR-010, FR-011, FR-012, FR-013, FR-014, FR-046 (events), FR-070 – FR-074, P0-02, P0-03 |

## Summary

Analysts onboard an **applicant** (individual or company, [ADR-012](../../adr/ADR-012-applicant-profile-with-ai-suggestions.md)),
create a case for that applicant in a three-step wizard, and upload the applicant's documents. Files
are validated against the workspace's plan, stored in Cloud Storage, **split into pages** (rendered and
triaged: usable text layer or not, blank or not), and registered in Firestore. The case workspace
shell (header + tabs) is introduced with the Documents tab working. AI suggestions for the profile
come later (spec 014).

## User stories

### US-003-1: Create a case

- **AC-003-1** Given the wizard's applicant step (an existing applicant, or a new one per US-003-6) and
  a valid loan request (amount, tenor, purpose), when I submit, then `POST /api/cases` (with
  `applicantId` or an inline `applicant`) returns `201` with `status: DRAFT`, a `reference` like
  `KRD-XXXXXX`, the `applicant` snapshot, and the wizard moves to the documents step.
- **AC-003-2** Invalid input (e.g. amount ≤ 0, tenor 0, empty name, `type: COMPANY` without a
  `company` block, both `applicantId` and `applicant`) → `422 VALIDATION_ERROR` with field errors shown
  next to the fields.
- **AC-003-3** A `CASE_CREATED` event is recorded with the actor.

### US-003-2: See my cases

- **AC-003-4** `/cases` lists my workspace's cases newest first with reference, applicant (with an
  individual/company icon), amount, status, grade (when available) and critical/high counts; filter by
  status; `?applicantId=` lists one applicant's cases.
- **AC-003-5** Cases of another org never appear, and `GET /api/cases/{foreignId}` returns `404`.

### US-003-3: Edit a draft

- **AC-003-6** In `DRAFT` or `INFO_REQUESTED`, `PATCH /api/cases/{id}` updates the loan request and
  records `CASE_UPDATED`, and the applicant snapshot refreshes from the applicant; in other statuses →
  `409 CASE_NOT_EDITABLE` (and the snapshot stays frozen).

### US-003-4: Upload documents

- **AC-003-7** Dropping PDF/PNG/JPEG files uploads each with a progress bar (max 3 in parallel); each
  becomes a document with `status: UPLOADED`, `docType: UNKNOWN`, page count, size and SHA-256.
- **AC-003-8** The type is decided by magic bytes: a `.pdf` file that is really a ZIP → `415
  UNSUPPORTED_MEDIA_TYPE`.
- **AC-003-9** Limits come from the plan (free trial: 20 MB, 20 pages, 20 documents): larger file →
  `413 DOCUMENT_TOO_LARGE`; more pages → `422 TOO_MANY_PAGES` with `maxPages`; one document too many →
  `409 TOO_MANY_DOCUMENTS`; encrypted PDF → `422 ENCRYPTED_DOCUMENT`; after the trial →
  `403 TRIAL_EXPIRED`; errors are shown per file.
- **AC-003-10** Uploading the same file twice → `409 DUPLICATE_DOCUMENT` with `existingDocId`.
- **AC-003-11** The original is stored at the GCS path of [`docs/09`](../../09-data-model.md) §7;
  the file is split into pages: full pages (150 dpi) and thumbnails are rendered and each page is
  triaged at upload (US-003-7).
- **AC-003-12** Upload outside `DRAFT`/`INFO_REQUESTED` → `409 CASE_NOT_EDITABLE`.
- **AC-003-13** `DOCUMENT_UPLOADED` event recorded; `case.counts.documents` incremented atomically.

### US-003-5: View and remove documents

- **AC-003-14** The Documents tab lists documents with thumbnail, name, pages, size, type badge, a
  **Digital / Scanned** badge and status.
- **AC-003-15** `GET …/file` streams the original; `GET …/pages/{n}?variant=thumb|full` returns the PNG;
  both only for my org.
- **AC-003-16** In `DRAFT`, removing a document deletes its GCS prefix and Firestore doc, records
  `DOCUMENT_REMOVED`, and decrements the count.

### US-003-6: Onboard an applicant

- **AC-003-17** `POST /api/applicants` creates an `INDIVIDUAL` (required: full name, industry) or a
  `COMPANY` (required: legal name, legal form, industry, years operating) with optional address,
  contact, bank accounts and related parties; `APPLICANT_CREATED` is recorded; `displayName` is the
  legal or full name.
- **AC-003-18** A bank account's full number is accepted on input, stored only as `accountMasked`
  (last 4) in the applicant and as a hash in `orgPrivate/{orgId}/accountHashes`, never returned and
  never logged; `accountId` is deterministic, so adding the same account twice → `409`.
- **AC-003-19** Related parties take a name, kind and ≥ 1 role (beneficial owner, director,
  shareholder, guarantor, authorized signatory) and an optional ownership %; the ownership of all
  parties may not exceed 100% (`422`). Only the last 4 digits of any ID number are accepted.
- **AC-003-20** `PATCH /api/applicants/{id}` edits profile fields (type cannot change); bank accounts
  and related parties are added/removed through their own endpoints; each change records an applicant
  event.
- **AC-003-21** The wizard's applicant step offers a picker (`GET /api/applicants?q=` name prefix) and
  the Individual | Company form; optional sections (address, bank accounts, people) can be skipped
  with the hint that Kredibel will suggest them from the documents.

### US-003-7: Split and triage pages

- **AC-003-22** Every uploaded page gets `{pageNo, width, height, imagePath, thumbPath, sha256,
  textLayer, blank}` per [`docs/07`](../../07-document-intelligence.md) §3.1: S1 pages are `USABLE`,
  the scanned S1 variant's pages are `NONE`, a fixture with `(cid:…)` glyphs is `UNUSABLE`, and a white
  page is `blank`.
- **AC-003-23** Creating a case checks the plan's `casesPerMonth` and the trial (spec 013):
  `403 PLAN_LIMIT_REACHED` / `403 TRIAL_EXPIRED`.
- **AC-003-24** (P1) `POST …/documents?split=auto` with a PDF longer than `pagesPerDocument` stores the
  untouched original once (`uploads/{uploadId}`), creates parts of ≤ 20 pages named
  `file (part n of m).pdf` sharing `sourceUploadId`, and returns all parts; the UI offers this from the
  `TOO_MANY_PAGES` error ("Split and upload").

## Out of scope

Classification and reading (005), starting analysis (004), AI profile suggestions (014), the
applicant list page (014, P1).

## Edge cases

- Zero-byte file → 415. PNG with 1 page counts as 1 page; a JPEG photo of a page is triaged `NONE`
  (OCR witness). Concurrent uploads update counts correctly
  (transaction). Very long file names are truncated to 200 chars for display.
