# Spec 003 — Document Intake

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 |
| **Owner role** | C: Frontend (library, upload) + D: Platform (API, storage) |
| **Depends on** | 001, 013 (phases 1–3: workspace and entitlements) |
| **Requirements** | FR-002, FR-010, FR-011, FR-013, NFR-06, NFR-12, P0-02, P0-03 (exact copies) |
| **Design** | [`docs/07`](../../07-document-intelligence.md) §1, §3.1; [`docs/09`](../../09-data-model.md) §3.5; [`docs/10`](../../10-api-contract.md) §2.2; [`docs/11`](../../11-frontend.md) §6 |

## Summary

Users upload statements, invoices, receipts and ledger exports **in any order, at any time**. The
server checks type and plan limits, records an **exact copy** as a duplicate without reading it,
stores the original, splits PDFs and images into triaged pages, and hands the document to the
document workflow (spec 004). The **Documents** library lists everything with live status.

## User stories

### US-003-1: Upload anything, anytime

- **AC-003-1** From the global **Upload** action (top bar; floating button on phones), I can drop or
  pick several files (max 3 uploading in parallel, each with a progress bar); on a phone I can also
  take a photo of a receipt. A `docTypeHint` can be chosen but is optional.
- **AC-003-2** `POST /api/documents` accepts PDF, PNG, JPEG, CSV and XLSX detected by content; anything
  else → `415 UNSUPPORTED_MEDIA_TYPE`; a `.pdf` that is really a ZIP → `415`.
- **AC-003-3** Limits from the plan: larger than `fileSizeMb` → `413 DOCUMENT_TOO_LARGE`; more pages
  than `pagesPerDocument` → `422 TOO_MANY_PAGES` with `maxPages`; a ledger file with more rows than
  `ledgerRowsPerFile` → `422 TOO_MANY_ROWS`; encrypted PDF → `422 ENCRYPTED_DOCUMENT`; over
  `documentsPerMonth` or the page budget → `403 PLAN_LIMIT_REACHED`; after the trial →
  `403 TRIAL_EXPIRED`. Errors are shown per file with what to do.
- **AC-003-4** A new file gets `status: UPLOADED`, `docType: UNKNOWN` (or the hint), page count, size
  and SHA-256; the original is stored at the GCS path of [`docs/09`](../../09-data-model.md) §7; pages
  are rendered (150 dpi + thumbnail) and triaged (text layer usable, unusable or none; blank); a
  `doc-{docId}-1` task is enqueued; `DOCUMENT_UPLOADED` is recorded; usage counters change in the
  same transaction.

### US-003-2: The same file twice is never read twice

- **AC-003-5** Uploading a file whose SHA-256 equals a non-duplicate document of the workspace returns
  `201` with `status: DUPLICATE`, `duplicate {kind: EXACT, code: D01_EXACT_FILE_DUPLICATE, ofDocId,
  decision: CONFIRMED}` and `countsAgainstLimits: false`; no file is stored, no task is enqueued and no
  usage counter changes; `DUPLICATE_RECORDED` is logged as an event.
- **AC-003-6** The upload sheet shows it at once: "Already uploaded on 3 Feb as *BCA Feb.pdf* — not
  read again", with a link to the original.

### US-003-3: The Documents library

- **AC-003-7** `/documents` lists documents newest first with thumbnail, name, type, period or date,
  a **Digital / Scanned / Spreadsheet** badge, live status ("Reading page 3 of 18"), integrity
  verdict, risk level and duplicate state; filters by type, month, status, risk and "duplicates only";
  on phones it becomes a list of cards (responsive table, [`docs/11`](../../11-frontend.md) §5a).
- **AC-003-8** Status and page progress update live through the Firestore listener on the document,
  without polling (NFR-02).
- **AC-003-9** `/documents/:docId` shows the pages (thumbnail strip + page viewer), what was read
  (statement period and balances, invoice or receipt fields, ledger rows imported), findings and
  matches for that document, and its events.

### US-003-4: Remove a document

- **AC-003-10** `DELETE /api/documents/{docId}` removes the document, its GCS prefix and everything
  read from it (bank lines, invoices, receipts, ledger entries, findings scoped to it, retrieval
  chunks), records `DOCUMENT_REMOVED` and marks its months dirty; exact copies of the file go with it,
  while documents held as content duplicates of it are read again, which releases them; the UI asks for confirmation and
  names what will change ("March will be reconciled again").

### US-003-5: Only my workspace

- **AC-003-11** Documents of another workspace never appear; `GET /api/documents/{foreignId}`,
  `…/file` and `…/pages/{n}` return `404`.

## Out of scope

Reading and checks (005, 006), content duplicates (006), signed-URL uploads, "split and upload" for
long PDFs (P1, spec 015), email-in or bank feeds.

## Edge cases

- Two uploads of the same new file at the same moment: the second waits on the SHA-256 lookup inside
  the transaction and becomes the exact duplicate.
- A 0-byte or truncated file → `422 VALIDATION_ERROR` with "The file is empty or damaged".
- A CSV with a byte-order mark or Windows line endings is accepted.
- Deleting the original of an exact duplicate promotes the duplicate record to a normal upload that
  must be uploaded again (the UI says so); the duplicate record itself is removed.
