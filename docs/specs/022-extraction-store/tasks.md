# Tasks 022 — Extraction store and knowledge base

## Phase A — the store and the Markdown

- [x] **T022-01** **TDD** `domain/extraction_store.py`: chunk records with deterministic IDs, masked text, links; document Markdown from pages. (AC-022-1, AC-022-2) Built 16 Oct 2026 (`test_extraction_store.py`).
- [x] **T022-02** `ChunkRepository` (Firestore, fake), `ExtractionService.build`; `verify_pages` writes through it; delete with the document. (AC-022-1, AC-022-2) Built 16 Oct 2026 (`chunks` in Firestore, `verify_pages` through `build_extraction`, deleted with the document).
- [x] **T022-03** Routes: page Markdown built on first request, document Markdown, chunks. (AC-022-2) Built 16 Oct 2026 (`test_extraction_store_api.py`).
- [x] **T022-04** Rebuild for documents read before this spec: from the cache, else the PDF text layer; `POST /api/extractions/rebuild`, `make extractions-rebuild`. (AC-022-3) Built 16 Oct 2026; the demo template rebuilt: 78 documents, 87 pages, 20 photos and scans waiting for the OCR witness.

## Phase B — the OCR witness

- [ ] **T022-05** Spike S3 (T005-05) and `DocAiPageText`; the processor in the project; scans and photos read twice. (AC-022-4)
- [ ] **T022-06** `POST /api/documents/{docId}/reread`; re-read the demo template's photos. (AC-022-5)

## Phase C — embeddings and retrieval (P1)

- [ ] **T022-07** Chunk embeddings, vector index, workspace-scoped search. (AC-022-6)
- [ ] **T022-08** The assistant's `search_documents` with citations (with spec 011 T011-02, T011-03). (AC-022-7)

- [ ] **T022-09** Update `docs/20-implementation-status.md`, docs/07 §8, docs/09.
