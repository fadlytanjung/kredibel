# Plan 005 — Document Extraction

## Spike first (S1, ≤ 1.5 h)

On S1 seed-1 and a scanned variant (rasterized pages, no text layer):

1. Run `read_statement_page` on page images at media resolution `high` and `ultra_high`; record field
   accuracy vs truth and tokens per page.
2. Run the verifier against the pdfplumber witness (digital) and Enterprise OCR (scanned); record
   agreement and box coverage.
3. Create the Enterprise OCR processor (`scripts/create_processors.py --ocr`); optionally Form Parser
   and Invoice Parser for the P1 escalation comparison.
4. Commit raw outputs as the first recordings; write the numbers into [`docs/02`](../../02-research.md)
   §6 and [`docs/21`](../../21-cost-analysis.md) §3.2.

## Modules

| File | Responsibility |
|---|---|
| `ports/pdf_inspector.py`, `adapters/pdf_inspector.py` | pikepdf info/XMP, revision count from raw bytes, fonts (pdfplumber chars), **words with boxes per page** (the text-layer witness) |
| `ports/ocr_witness.py`, `adapters/docai_ocr.py` | Document AI Enterprise OCR (`us-documentai.googleapis.com`), ≤ 15 pages per request, tokens → normalized words with boxes, retries |
| `ports/docai_parser.py`, `adapters/docai_parser.py` | P1: Form Parser table mapper (header → canonical columns) and Invoice Parser entity mapper (anti-corruption layer) |
| `ports/extraction_cache.py`, `adapters/gcs_extraction_cache.py` | per-page content-addressed cache; modes `on`, `ocr_only`, `off` (`EXTRACTION_CACHE`) |
| `ports/gemini.py`, `adapters/gemini_gateway.py` | `generate_structured(model, prompt_id, parts, schema, temperature, media_resolution)`; labels, retries, one schema retry, usage accounting, quarantine check (hook for 010) |
| `agents/prompts/classify_document.md`, `read_statement_page.md`, `read_invoice_page.md` | prompts with front matter; untrusted-content framing; "values exactly as printed" |
| `agents/llm/schemas.py` | `DocClassification`, `StatementPage`, `StatementHeader`, `StatementTotals`, `InvoicePage` (docs/07 §4, §5.2) |
| `agents/prompt_registry.py` | load prompts at startup; expose `id@version` |
| `domain/normalize.py` | amounts, dates, direction, descriptions, counterparty extraction |
| `domain/verify.py` | row anchoring, band and column matching, description check, coverage check (witness-only rows), header search, agreement, value choice, `Provenance` |
| `domain/consensus.py` | P1: three-source alignment (LCS on key tuples, two-of-three) for escalation and thorough mode |
| `domain/bbox.py` | union boxes from witness words; OCR polygon → BBox; coordinate normalization |
| `domain/forensics/extraction_checks.py` | `E01`, `E02`, `E03`, `E05` builders |
| `agents/nodes/doc_nodes.py` | real `inspect_pdf`, `classify_document`, `read_page`, `witness_pages`, `verify_pages`; `escalate_pages` (no-op until P1) |
| `adapters/firestore_repo.py` | `upsert_transactions` (chunked), `upsert_invoice`, `update_document_fields`, `update_page_status` |
| `tests/fakes/recorded.py` | `RecordedGemini`, `RecordedOcr`, `RecordedParser` replaying `tests/scenarios/recordings/` |
| `backend/scripts/record.py` | `make record SCENARIO=… SEED=…` (per page) |

## Key decisions

- **One page per Gemini call, image only.** Independence from the witness is the point (ADR-010).
- **The witness never interprets.** It provides words and boxes; the verifier decides.
- **All arithmetic and parsing in `domain/`** (P2). The model returns strings as printed.
- **Recordings** make 006–008 and 014 scenario tests offline and deterministic.

## Constitution check

P2 ✔ · P3 ✔ (provenance, boxes from the witness) · P4 ✔ (image only; untrusted framing; quarantine
hook) · P6 ✔ (two independent readings per value) · P7 ✔ (Gemini, Document AI) · P10 ✔ (verifier and
normalization unit tests; reading quality measured in evals)
