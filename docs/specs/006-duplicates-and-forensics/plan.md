# Plan 006 — Duplicates and Document Forensics

## Backend

| File | Content |
|---|---|
| `domain/duplicates.py` | content keys per type; overlap and fuzzy issuer rules; newer-is-held rule; pure. Receipt pHash fallback is blocked by contradictory available merchant, date or total readings, so similar till-roll layouts do not become duplicates |
| `domain/checks/base.py`, `registry.py` | `Check` protocol and registration ([`docs/08`](../../08-risk-engine.md) §1) |
| `domain/checks/arithmetic.py`, `structure.py`, `extraction.py`, `holder.py` | `A0x`, `M0x`, `E0x`, `X05`, `X06` |
| `domain/verdict.py` | integrity verdict |
| `adapters/pdf_inspector.py` | metadata, revisions, fonts per character, rectangles; perceptual hash via `imagehash` |
| `agents/nodes/doc_nodes.py` | `inspect_file`, `check_document`, `detect_content_duplicates` |
| `services/duplicate_service.py` | apply a decision: flip `heldAsDuplicate` on the document and its records, mark months dirty |
| repository | lookups by content key: statements by `accountId` and period, invoices by issuer + number, receipts by merchant + date + total, ledger entries by key |

Content keys are stored on the records (`dupKey`) so lookups are single-field queries.

## Constitution check

P2 ✔ (all deterministic) · P3 ✔ (evidence on every finding) · P6 ✔ (CRITICAL only on agreed values;
duplicates held, not deleted)
