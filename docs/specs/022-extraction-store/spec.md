# Spec 022 — Extraction store and knowledge base

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 (phase A, B), P1 (phase C) |
| **Owner role** | A: Document intelligence, B: Backend, C: Frontend |
| **Depends on** | 005 (reading, layout chunks, ADR-023), 016 (page extraction file), 011 (retrieval) |
| **Requirements** | FR-005, FR-011, FR-016, NFR-6 (privacy), NFR-9 (cost) |
| **Design** | [`docs/07`](../../07-document-intelligence.md) §5.3, §8; [`docs/09`](../../09-data-model.md) §3.17, §3.21; mocks `labels.html`, `label.html`, `document.html` |

## Summary

Every page Kredibel reads is cut into **layout chunks** (ADR-023): the text layer of a PDF today, and
the words Document AI OCR finds on a scan or a photo once the witness is built. The reader cites
chunks for every value, and code checks each value against the chunk it cites. Today those chunks
live only in a per-file cache in Cloud Storage, the page's Markdown file is written only for
documents read since 16 Oct 2026, scans and photos have no chunks at all (one reading, `E01`), and the
assistant has no store to search. So the Labels page shows "no extraction" for older documents, and
the "read twice" promise is one reading for every photo.

This spec makes the extraction a **first-class store**: every chunk of every read page is a record in
the workspace with its metadata (document, page, order, kind, box, source, the values and records it
backs), from which the page Markdown and the whole document's Markdown are rebuilt deterministically
("merged back"); scans and photos get their second reading from **Document AI OCR**; and the chunks
get embeddings so the assistant can search the books with citations.

## Current state (16 Oct 2026)

| Piece | State |
|---|---|
| Layout chunks per page (text layer) | Built (ADR-023); stored only as `cache/extraction/{fileSha}/p{n}/chunks-v1.json` in Cloud Storage |
| Chunk cited by each read value | Built; the citation lives in the raw reader output, not on a record |
| OCR witness for scans and photos | Not built (`DOCAI_OCR_PROCESSOR_ID` unread; T005-05 spike S3 open); photos are single-source (`E01`) |
| Page extraction Markdown | Built 16 Oct 2026 (T016-04) for pages read from then on; older documents have none |
| Whole-document Markdown | Not built |
| Retrieval chunks with embeddings (`retrievalChunks`) | Not built (T011-02) |
| Embeddings | Built only for decided labels (`embedding_v1`, T016-08) |

## User stories

### US-022-1: Every read page has its extraction, for every document (person checking a label)

- **AC-022-1** After a page is read, each of its layout chunks is stored as a record
  `orgs/{orgId}/chunks/{chunkId}` with: `docId`, `docType`, `pageNo`, `ordinal` (reading order),
  `kind` (`HEADING`, `PARAGRAPH`, `TABLE_ROW`, `KEY_VALUE`, `FOOTER`, `OTHER`), `text` (account and ID
  numbers masked), `box` (normalised to the page), `source` (`TEXT_LAYER`, `OCR`), the `months` of
  the document, and its **links**: the fields read from it and the bank lines, invoices, receipts or
  ledger entries those values became. IDs are deterministic (`chk_` + document, page, ordinal), so a
  re-read replaces, never duplicates.
- **AC-022-2** The page's Markdown (docs/07 §8) and the **whole document's Markdown** (pages in order,
  one heading per page) are rebuilt from the stored chunks and records alone, byte for byte the same
  for the same data; `GET /api/documents/{docId}/extraction.md` serves the document,
  `GET /api/documents/{docId}/pages/{n}/extraction.md` the page, and `GET
  /api/documents/{docId}/chunks?page=` the chunks with their metadata. A page whose file is missing is
  built on its first request.
- **AC-022-3** Documents read before this spec get their chunks and Markdown without a model call:
  from the cached chunks, else from the stored PDF's text layer; an owner can rebuild every document
  (`POST /api/extractions/rebuild`), and `make extractions-rebuild` does it for a workspace. A
  document whose pages have no text and no OCR yet is listed as needing a re-read.

### US-022-2: Photos and scans are read twice too (any person uploading a receipt photo)

- **AC-022-4** A page without a usable text layer (a scan, a photo) is read by **Document AI OCR**
  (`DOCAI_OCR_PROCESSOR_ID`, location `DOCAI_LOCATION`); its words and boxes become layout chunks with
  `source: OCR`, the reader cites them, and code checks every value against them as for a text layer,
  so a photo's values can be `AGREED` and the `E01` single-source finding no longer applies to it.
  OCR output is cached by page image like the reader's (docs/07 §8), and counts against the plan's
  pages once.
- **AC-022-5** Re-reading a document (`POST /api/documents/{docId}/reread`, owner) runs its workflow
  again with the OCR witness; people's decisions and labels stay (spec 016).

### US-022-3: The assistant searches the books with citations (P1)

- **AC-022-6** Each chunk gets an embedding of its masked text (`embedding_v1`, `MODEL_EMBEDDING`, 768
  dimensions; best effort, a failure leaves the chunk without one and is retried by the rebuild); a
  vector index on `chunks` serves `find_nearest` within the workspace only.
- **AC-022-7** The assistant's `search_documents` tool (spec 011) returns the nearest chunks with
  document, page and chunk IDs, and every sentence that uses one cites it; nothing from another
  workspace is ever returned (tested).

## Out of scope

- Training on chunks (spec 016's dataset export needs consent).
- Form parsing with Document AI's form processor (the OCR witness only).

## Edge cases

- An exact copy is never read: it has no chunks of its own and links to the original's.
- A quarantined document never reaches a model: no OCR, no embedding.
- Deleting a document deletes its chunks and Markdown files (docs/09 §8).
- A chunk's text is capped at 2,000 characters; a longer block is split in reading order.
- Ledger exports: 50-row blocks are chunks with `kind: TABLE_ROW` blocks and `source: LEDGER`.
