# Spec 005 — Document Extraction (classify, adaptive reading, verification)

| | |
|---|---|
| **Status** | Ready (after spike S1) |
| **Priority** | P0 (escalation and thorough mode: P1) |
| **Owner role** | A: Agents (classifier, page reader, OCR adapter) + B: Risk engine (normalization, verifier) |
| **Depends on** | 002, 003 (page split and triage at upload), 004 |
| **Requirements** | FR-022, FR-023, FR-024, NFR-07, P0-05, P0-06, constitution P2/P3/P6 |
| **Design** | [`docs/07`](../../07-document-intelligence.md), [ADR-010](../../adr/ADR-010-adaptive-extraction-ai-reader-and-witness.md), [`docs/06`](../../06-agent-design.md) §3–§5, [`docs/21`](../../21-cost-analysis.md) §3 |

## Summary

Replace the stub nodes `inspect_pdf`, `classify_document`, `read_page`, `witness_pages` and
`verify_pages` with real implementations. Every page of a bank statement or invoice gets **one AI
reading** (Gemini on the page image) and **one deterministic witness** (the PDF text layer, or
Document AI Enterprise OCR for scanned pages). A pure verifier turns them into canonical transactions
and invoices with a per-value status, bounding boxes and an agreement score. Escalation to a
Document AI parser and `thorough` mode are P1.

## User stories

### US-005-1: Inspect

- **AC-005-1** For each PDF, `documents.pdf` records producer, creator, creation/mod dates, revision
  count and fonts; inspection runs on the original upload.

### US-005-2: Classify

- **AC-005-2** S1–S3 statements are classified `BANK_STATEMENT` and invoices `SALES_INVOICE` with
  confidence ≥ 0.6 by `MODEL_LITE` from page 1; the result, model and run ID are stored.
- **AC-005-3** Sales vs purchase is decided in code from the applicant-name match (names, trading
  name, aliases); an unclear party raises `E05_PARTY_UNCLEAR` (LOW).
- **AC-005-4** Confidence < 0.6 → `docType OTHER` and `E03_UNCERTAIN_TYPE`; `OTHER` documents are
  `SKIPPED` and none of their pages is read.

### US-005-3: Read each page with the AI

- **AC-005-5** Each non-blank page of a statement or invoice is read by `MODEL_FAST` from its **page
  PNG only** (the text layer is never sent), with media resolution `high` (or the value chosen in spike
  S1), `temperature=0`, and the `read_statement_page` / `read_invoice_page` prompt. Page 1 runs first;
  pages 2..n run in parallel (`PAGE_CONCURRENCY`, default 6) with the page-1 header as context.
- **AC-005-6** Output is validated against `StatementPage`/`InvoicePage`; one retry with the
  validation error; then the page continues `WITNESS_ONLY` with an `E01` finding.
- **AC-005-7** Quarantined documents (P1, spec 010) are never sent to Gemini; their pages are
  `WITNESS_ONLY`.

### US-005-4: Witness each page

- **AC-005-8** Pages with `textLayer = USABLE` get words with boxes from pdfplumber at no cost;
  pages with `NONE` or `UNUSABLE` get words from Document AI Enterprise OCR (`DOCAI_OCR_PROCESSOR_ID`,
  ≤ 15 pages per request). Boxes are normalized 0..1, top-left origin.
- **AC-005-9** An OCR failure after retries leaves the page `AI_ONLY` (values `SINGLE_SOURCE`, no
  boxes) with an `E01` finding; both failing → page `FAILED`; a statement with a failed page is
  `FAILED` with `E02_EXTRACTION_FAILED`.

### US-005-5: Normalize and verify

- **AC-005-10** Amounts in `1,250,000.00`, `(1,250,000.00)`, `1,250,000.00 CR`, `IDR 1,250,000` and the
  dot-grouped `1.250.000,00`, and dates `05/03`, `05/03/2026`, `05 MAR`, `5-Mar-26` normalize
  correctly; unparsable values become `None` with a parse note, never a guess.
- **AC-005-11** The verifier anchors rows on their date, matches values in the row band and column,
  and gives each value `AGREED`, `CONFLICT` or `SINGLE_SOURCE` with `Provenance` (sources, raw strings,
  box) per [`docs/07`](../../07-document-intelligence.md) §6–§7.
- **AC-005-12** The coverage check turns printed amounts the AI did not account for into witness-only
  rows (`SINGLE_SOURCE`, `witnessOnly: true`) in printed order; a fixture where the AI output drops one
  row produces exactly one witness-only row and lowers agreement.
- **AC-005-13** A fixture where the text layer and the visible value differ in one cell (white-out +
  overlay) produces `CONFLICT` for that value and never `AGREED`.
- **AC-005-14** `documents.extraction` stores method, agreement, compared/agreed counts, AI rows,
  witness-only rows, pages by witness, model and prompt version; `documents.pages[]` stores per-page
  witness, agreement and status.
- **AC-005-15** Agreement < `policy.extraction.minAgreement` → `E01_LOW_EXTRACTION_AGREEMENT` (MEDIUM).

### US-005-6: Locate evidence

- **AC-005-16** On S1, ≥ 98% of transaction amounts get a box from the witness; on the scanned S1
  variant, ≥ 90%.

### US-005-7: Persist and cache

- **AC-005-17** Transactions are written with deterministic IDs (`tx_…`) in batches ≤ 400; invoices as
  `inv_…`; `statementMeta` with the masked account number and `matchedAccountId` when it matches a
  declared account; re-running the node overwrites, never duplicates.
- **AC-005-18** On S1 seed-1 (recordings), verified rows equal the generator's truth rows (date, amount,
  direction) for 100% of rows, and agreement ≥ 0.95; on S2 the edited March credit is `AGREED` (both
  readings see 7,250,000.00).
- **AC-005-19** Raw outputs are cached per page (`cache/extraction/{sha256}/p{n}/…`); re-processing a
  file with the same SHA-256 in any case of the workspace makes no Gemini or OCR call unless
  `EXTRACTION_CACHE` says otherwise; `runs.usage.pagesCached` counts the hits and they do not count
  against the plan.
- **AC-005-20** `runs.usage` records `pagesRead`, `ocrPages`, tokens and `estimatedUsd`; on S1 the
  estimate is ≤ USD 0.20 for reading (NFR-07 budget for the whole case: ≤ USD 0.50).

### US-005-8: Escalate and thorough mode (P1)

- **AC-005-21** With `EXTRACTION_ESCALATION=on`, a page whose agreement stays < `extraction.escalateBelow`
  is read by Form Parser (statements) or Invoice Parser (invoices), within
  `escalationPagesPerCase`; values are re-decided two-of-three; `pages[].escalated = true`.
- **AC-005-22** With `EXTRACTION_MODE=thorough`, every page is also read by the parser; `method =
  THOROUGH`; evals compare agreement and cost against `adaptive` (spec 012).

## Out of scope

Forensic checks on the extracted data (006). Categorization (007). Model Armor screening (010).
Splitting over-long uploads into parts (003, P1).
