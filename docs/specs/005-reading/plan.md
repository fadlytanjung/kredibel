# Plan 005 — Reading

## Backend

| File | Content |
|---|---|
| `agents/prompts/classify_document.md`, `read_statement_page.md`, `read_invoice_page.md`, `read_receipt.md`, `map_ledger_columns.md` | prompts with front matter ([`docs/06`](../../06-agent-design.md) §6) |
| `agents/llm/schemas.py` | `DocClassification`, `StatementPage`, `InvoicePage`, `ReceiptPage`, `LedgerMapping` |
| `adapters/gemini_gateway.py` | multimodal structured calls, retries, labels, cache, usage accounting |
| `adapters/docai_ocr.py` | Enterprise OCR in ≤ 15-page batches → words with normalized boxes |
| `adapters/pdf_inspector.py` | text-layer words with fonts (pdfplumber) |
| `domain/normalize.py` | amounts, dates, directions, descriptions, counterparty names, payment methods |
| `domain/verify.py` | statements, invoices, receipts ([`docs/07`](../../07-document-intelligence.md) §6) |
| `domain/ledger_parse.py` | table → entries with a mapping; layout signature; shape masking for the mapper |
| `adapters/spreadsheet_reader.py` | CSV sniffing, openpyxl read-only |
| `agents/nodes/doc_nodes.py` | `classify_document`, `read_page`, `witness_pages`, `verify_pages`, `propose_ledger_mapping`, `parse_ledger`, `escalate_pages` (P1) |
| `backend/tests/scenarios/recordings/` | recorded Gemini and OCR outputs per page ([`docs/15`](../../15-testing-and-evaluation.md) §6) |

## Spikes

- **S1** media resolution `high` vs `ultra_high` on 20 statement pages (agreement and cost).
- **S3** OCR on the scanned S1 variant and on receipt photos (box quality, latency).

## Constitution check

P2 ✔ (models read; code verifies and computes) · P3 ✔ (provenance on every value) · P4 ✔ (untrusted
framing; mapper sees shapes only) · P6 ✔ (status per value) · P7 ✔

## Risks

- Receipts photographed at an angle may have low agreement: the receipt total alone matters for
  matching; a `SINGLE_SOURCE` total becomes a review item instead of blocking.
