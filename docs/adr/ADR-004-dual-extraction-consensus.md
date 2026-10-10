# ADR-004 — Two independent readers and a consensus

**Status:** Superseded in part by [ADR-010](ADR-010-adaptive-extraction-ai-reader-and-witness.md) · **Date:** 2026-10-10

> **What still holds:** two independent readings before an accusation, per-value status, and the
> corroboration rule. **What changed:** by default the second reading is a deterministic witness
> (PDF text layer, or Document AI OCR for scans), not a second paid parser. The design below is now
> the `thorough` extraction mode and the three-source alignment used by escalation.

## Context

Forensic arithmetic checks are only as good as extraction. A single OCR/LLM mistake on one amount
makes a genuine statement look tampered, which means a false fraud accusation. Document AI's
specialized parsers give structured fields with bounding boxes and confidence but may not cover
Indonesian layouts fully; Gemini reads layouts flexibly but gives no native bounding boxes for PDF
text.

## Decision

Read every bank statement and invoice **twice, independently**, with Document AI and Gemini, in
parallel. Normalize both in code, align rows, compare fields, and store a status per value (`AGREED`,
`CONFLICT`, `SINGLE_SOURCE`, `MISSING`). Arithmetic findings are **CRITICAL only when every involved
value is AGREED**; otherwise they are reported as extraction uncertainty (`E01`), and the document can
at most be `UNVERIFIABLE`.

## Alternatives considered

| Option | Why not |
|---|---|
| Document AI only | Weaker on unfamiliar layouts; one source of truth for an accusation |
| Gemini only | No independent check; no native bboxes; probabilistic reading behind a fraud verdict |
| Gemini twice (two prompts) | Correlated errors; not independent |
| Custom Extractor (generative) as second reader | Good production path for residency (ADR-009), but it is Gemini-based too, so less independent than a specialized parser |

## Consequences

- Roughly double extraction cost per document. Mitigated by Form Parser as the default statement
  reader (≈ USD 0.03/page vs USD 0.75/document for the Bank Statement Parser) and a content-addressed
  extraction cache ([`21`](../21-cost-analysis.md) §3.3, §5).
- Agreement becomes a product feature ("both readers agree on these values") and an eval metric.
- If S1 shows Document AI cannot produce rows, the second reader for rows becomes the PDF text layer
  (pdfplumber table extraction) for text PDFs; record as an amendment here.
