# Spec 005 — Reading: classification, adaptive reading, ledger import

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 · P1 (escalation to Document AI parsers, thorough mode) |
| **Owner role** | A: Agents + B: Risk engine (verifier, normalizers, ledger parser) |
| **Depends on** | 002, 003, 004 |
| **Requirements** | FR-020, FR-021, FR-022, NFR-01, NFR-07, P0-04, P0-05, P0-06, P1-08 |
| **Design** | [`docs/07`](../../07-document-intelligence.md) §4–§9; [`docs/06`](../../06-agent-design.md) §5; [ADR-010](../../adr/ADR-010-adaptive-extraction-ai-reader-and-witness.md) |

## Summary

Turn each document into canonical, verified records with provenance: classify it; for statements,
invoices and receipts, let Gemini read each page image and check every value against a witness (the
PDF text layer, or Document AI OCR for scans and photos); for ledger exports, let Gemini propose the
column mapping once per layout, let the user confirm it, and parse every row in code.

## User stories

### US-005-1: Know what each document is

- **AC-005-1** `classify_document` returns one of `BANK_STATEMENT`, `SALES_INVOICE`,
  `PURCHASE_INVOICE`, `RECEIPT`, `LEDGER_EXPORT`, `OTHER`; sales vs purchase is decided in code from
  the workspace's names and aliases ([`docs/07`](../../07-document-intelligence.md) §4).
- **AC-005-2** Confidence < 0.6 → document `NEEDS_INPUT`, finding `E03_UNCERTAIN_TYPE`, and a
  `CONFIRM_TYPE` review item; choosing a type continues the workflow.
- **AC-005-3** Classification results are cached by SHA-256 + model + prompt version.

### US-005-2: Read statements, invoices and receipts twice

- **AC-005-4** Each non-blank page is read once by `MODEL_FAST` from the page image plus its numbered
  layout chunks ([ADR-023](../../adr/ADR-023-parse-extract-ground.md); page 1 first, the rest in
  parallel with page 1's header as context), returning values **as printed** in the schemas of
  [`docs/07`](../../07-document-intelligence.md) §5.2 (`StatementPage`, `InvoicePage`,
  `ReceiptPage`). A PDF with several invoices or receipts gives one record per printed number.
- **AC-005-5** The witness is the text layer when usable, else Enterprise OCR (≤ 15 pages per request).
- **AC-005-6** The verifier gives every value a status (`AGREED`, `CONFLICT`, `SINGLE_SOURCE`,
  `MISSING`) and a box from witness tokens; witness-only rows are inserted in printed order; a value
  in the wrong column is a `CONFLICT` ([`docs/07`](../../07-document-intelligence.md) §6).
- **AC-005-7** Records are written with deterministic IDs: `bankLines` (statements, with signed
  amounts and printed balances), `invoices`, `receipts`; `statementMeta`, `reading` (method,
  agreement, model, prompt version) on the document; account numbers masked, hashes in `orgPrivate`.
- **AC-005-8** Agreement < 0.90 for a document → `E01_LOW_EXTRACTION_AGREEMENT`; a page both readers
  fail → page `FAILED`; a statement with a failed page → document `FAILED` with `E02`.
- **AC-005-9** Raw outputs are cached per page; a cache hit is not billed and not counted against
  `extractedPagesPerMonth`; reserved pages are released after reading.

### US-005-3: Import a ledger export

- **AC-005-10** CSV (delimiter and encoding sniffed) and XLSX (first sheet, header row detected) are
  read into a table; the layout signature is the SHA-1 of the normalized header.
- **AC-005-11** With a confirmed mapping for the signature, the file is parsed at once. Otherwise
  `ledger_mapper` (`MODEL_LITE`) proposes a mapping from the header and value **shapes** only; the
  document goes to `NEEDS_INPUT` with a `CONFIRM_LEDGER_MAPPING` item showing 5 rows parsed by the
  proposal and the bank-account-to-ledger-code mapping, pre-filled.
- **AC-005-12** After confirmation, every row becomes a `ledgerEntries` record (deterministic ID,
  minor units, month, `isBankCash` for mapped bank codes); bad rows are listed with row numbers; more
  than 2% bad rows reopens the mapping item.

### US-005-4: Escalation (P1)

- **AC-005-13** With `EXTRACTION_ESCALATION=on`, a page with agreement < 0.90 is read by Form Parser
  (statements) or Invoice Parser (invoices, receipts) within `escalationPagesPerMonth`; a value agreed
  by any two of three sources is `AGREED`.
- **AC-005-14** `EXTRACTION_MODE=thorough` reads every page with the parser too (evals only).

## Out of scope

Duplicate and integrity checks (006), categorization (007), retrieval chunks (011), handwriting,
multi-currency.

## Edge cases

- Dot-grouped amounts (`1.250.000,00`) detected per document; `CR`/`DR` suffixes; parentheses.
- Dates without a year are inferred from the statement period; out-of-period dates get a parse note.
- A receipt photo upside down: the reader is told the page may be rotated; the OCR witness reports
  orientation; boxes are mapped back to the image as shown.
- A ledger file in which every amount is in one column with a separate `D`/`C` column: the mapper can
  propose `signConvention` from that column.
