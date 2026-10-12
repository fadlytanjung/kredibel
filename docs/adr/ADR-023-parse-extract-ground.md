# ADR-023 — Parse, extract, ground: layout chunks as the reader's context

**Status:** Accepted · **Date:** 2026-10-12 · **Amends:** [ADR-010](ADR-010-adaptive-extraction-ai-reader-and-witness.md)
(the reader no longer reads the image alone; the witness becomes the grounding source)

## Context

ADR-010 kept the AI reader blind to the page text so that "two independent readings agree" would
prove a value. On a real statement (spike S1) that blindness costs more than it gives: the reader
must re-type every digit from pixels, while the PDF already holds the exact strings; scans and photos
need OCR anyway. Document pipelines such as LlamaParse and LandingAI's agentic extraction show the
stronger pattern: parse the document into layout-aware chunks first, give them to the model with the
image, and make every extracted value cite the chunk it came from. We build that pattern on Google
products only, and for real data ([ADR-022](ADR-022-real-documents-in-production.md)).

## Decision

1. **Parse** every page into layout chunks: text lines and blocks, table rows with their cells, header
   and totals lines. Each chunk has an ID (`p{page}-c{n}`), a kind, its text and a box; each word keeps
   its own box.
   - Digital PDFs: from the PDF text layer (`pdfplumber` words), chunked by `domain/layout.py`: free,
     exact, and inside our container, so in-region.
   - Scans, photos and unusable text layers: from **Document AI Enterprise OCR** words with boxes
     (USD 1.50 per 1,000 pages), chunked by the same code.
   - Not now: Document AI's Gemini-powered Layout Parser. Its Gemini versions are previews that route
     through the global endpoint (not data-residency compliant) and only v1.0 returns boxes; we revisit
     it for complex invoices and charts when it is GA with boxes.
2. **Extract** with Gemini (`MODEL_FAST`, `thinking_level=low`, `response_schema`): the input is the
   page image **and** the page's chunks as numbered context. Every value is returned as printed, with
   the `chunk_ids` it was read from; when the image shows something different from the chunk text (a
   value covered and redrawn, a text layer that disagrees with what is visible), the reader reports the
   visible value and sets `differs_from_text`. Prompts frame both image and chunks as untrusted data.
3. **Ground** in code (`domain/verify.py`, pure): a value is `AGREED` (grounded) when it is found in the
   words of a chunk it cites, else `CONFLICT`; a value with no citation is `SINGLE_SOURCE`; a chunk with
   amounts that no row cites becomes a witness-only row. Every grounded value gets the box of the exact
   words, so every number on screen points at its place on the page (P3). `differs_from_text` is always
   a `CONFLICT` with a note for `M05`.
4. **Forensics keep their own evidence.** Fonts, revisions, producer and the running-balance arithmetic
   read the file and the grounded values, not the reader's opinion (docs/08 §2.3–§2.4); a CRITICAL
   arithmetic finding still needs every involved value grounded (P6).

## Alternatives considered

| Option | Why not |
|---|---|
| Keep the blind reader (ADR-010) | Independence guards against hallucination, which grounding also does, at the price of re-typing every digit from pixels |
| Text only (no image) | Loses columns, stamps, handwriting cues and the visible-vs-text check that catches covered values |
| Gemini on the whole PDF in one call | No per-value boxes, no per-page cache, slower on 13+ pages; kept for classification only |
| Document AI Layout Parser (Gemini versions) as the parser | Preview, global routing, no boxes; v1.0 boxes without the table quality; revisit later |
| A third-party parser (LlamaParse, LandingAI) | The product must stay on Google services |

## Consequences

- Reading cost per digital page rises slightly (≈ 1–2K more input tokens of chunk text); scans cost the
  same (OCR was already the witness). Latency stays ≈ 8 s per page with pages in parallel.
- The verifier rules found in spike S1 (whitespace-free matching, serial-number columns, continuation
  rows, totals lines) move into the chunker and the grounding check.
- Agreement now means "grounded": the share of values found in the chunk they cite. The 0.90 threshold
  and `E01` keep their meaning.
