# Plan 022 — Extraction store and knowledge base

## Phase A: the store and the Markdown (no model calls)

- `domain/extraction_store.py` (pure): `chunk_records(doc, page_no, layout_chunks, records)` →
  `StoredChunk`s with deterministic IDs, masked text, box, kind, source and links (a value's chunk is
  the one whose words cover it, from the verifier's anchors); `document_markdown(pages)` merges page
  Markdown in order.
- `ports/chunk_repository.py` + Firestore adapter + fake: replace a document's chunks, list by
  document and page, delete with the document.
- `services/extraction_service.py`: `build(org_id, doc)` gathers the stored records, reading details,
  page types (PAGE_TYPE labels) and layout chunks (the cache, else the stored PDF's text layer via
  `PageText`), writes the chunks and the page and document Markdown; `page_markdown` and
  `document_markdown` read or build on demand; `rebuild_all(principal)`.
- `verify_pages` calls the service instead of writing files itself.
- Routes: `GET .../extraction.md` (document), `GET .../chunks`, `POST /api/extractions/rebuild`;
  `make extractions-rebuild EMAIL=…`.

## Phase B: the OCR witness

- `adapters/docai_page_text.py`: Document AI OCR (the `documentai` client, `DOCAI_OCR_PROCESSOR_ID`,
  `DOCAI_LOCATION`), page words with boxes for image pages; cached by page image.
- `witness_pages` uses it for pages without a text layer; `chunk_page` on its words.
- Infra: create the OCR processor (docs/16 §4 step), grant the worker `roles/documentai.apiUser`.
- `POST /api/documents/{docId}/reread`.

## Phase C: embeddings and retrieval

- Embed masked chunk text in batches with the existing `Embedder`; vector index in
  `contracts/firestore.indexes.json`; `ports/chunk_search.py` with a workspace filter;
  `search_documents` tool (spec 011 T011-02, T011-03).

## Dependencies

`google-cloud-documentai` (phase B), added to `backend/pyproject.toml` and this plan.
