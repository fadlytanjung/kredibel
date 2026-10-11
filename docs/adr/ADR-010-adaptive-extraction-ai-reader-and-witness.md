# ADR-010 — Adaptive extraction: one AI reader and a deterministic witness per page

**Status:** Accepted · **Date:** 2026-10-10 · **Supersedes in part:** [ADR-004](ADR-004-dual-extraction-consensus.md)
(the "two readers" principle stays; the choice of readers changes)

## Context

ADR-004 reads every statement and invoice twice, with a Document AI parser and Gemini. The cost
model in [`21`](../21-cost-analysis.md) §3 shows where the money goes for scenario S1's statements and invoices (58 pages):

- the Invoice Parser (USD 0.10 per 10 pages, so USD 0.10 per one-page invoice) dominates the cost;
- Form Parser (USD 30 per 1,000 pages) costs about 5× more per page than Gemini Flash reading the
  same page;
- specialized parsers depend on layout, and every business deals with different banks, suppliers and
  receipt formats.

What we must keep is constitution **P6**: no fraud verdict from a single reading. What we don't need
is a second *paid AI* on every page. Most statements and invoices are born-digital PDFs whose
**text layer** already contains every printed value with exact coordinates, for free.

## Decision

1. **Split every document into pages at upload.** Each page is rendered (150 dpi PNG), hashed, and
   tested for a usable text layer. Limits: ≤ 20 pages and ≤ 20 MB per file (plan-dependent, see
   ADR-011). Pages are the unit of extraction, caching, parallelism and cost accounting.
2. **One AI reading per page:** Gemini (`MODEL_FAST`) reads the **page image only** and returns every
   value as printed, with the row structure. It never sees the text layer, so it stays independent of
   the witness.
3. **One deterministic witness per page:**
   - a page with a usable text layer → the **PDF text layer** (pdfplumber words with boxes), free;
   - a scanned page, an image upload, or a broken text layer → **Document AI Enterprise Document OCR**
     (words with boxes, USD 1.50 per 1,000 pages).
4. **A verifier in domain code** checks every AI value against the witness by position (same row band,
   same column), produces `AGREED` / `CONFLICT` / `SINGLE_SOURCE` per value, takes the bounding box
   from the witness, and runs a **coverage check**: printed amounts the AI did not account for become
   witness-only rows, never silently dropped.
5. **Escalation (P1):** a page whose agreement stays below `extraction.escalateBelow` (0.90) is read once
   more by a specialized Document AI processor (Form Parser for statement tables, Invoice Parser for
   invoices), within a monthly page budget. With three sources, two that agree decide.
6. **Modes:** `EXTRACTION_MODE = adaptive` (default) or `thorough` (the specialized Document AI
   processor also reads every page, as in ADR-004). `thorough` is reserved for evals and a future paid
   tier (shown as "coming soon").

## Why the witness counts as an independent reader

The AI reads **pixels**; the witness reads the **content stream** (or, for scans, Google's OCR engine).
They fail in different ways. A tampered PDF whose visible value differs from its text layer (white-out
plus overlay) makes them **disagree**, which is itself a signal (`M05`, P1). The corroboration rule is
unchanged: arithmetic is `CRITICAL` only when every value in the equation is `AGREED`, and no unread
witness row sits between the rows involved.

## Alternatives considered

| Option | Cost, S1 statements and invoices (58 pages) | Why not |
|---|---|---|
| ADR-004 with Bank Statement Parser | ≈ USD 8.9 | Most expensive; layout fit unproven |
| ADR-004 with Form Parser + Invoice Parser | ≈ USD 4.9 | Two paid readers everywhere; Invoice Parser dominates cost |
| Document AI only (Form + Invoice Parser) | ≈ USD 4.6 | One reading behind an accusation; brittle on new layouts |
| Gemini only | ≈ USD 0.35 | Same cost as adaptive on digital pages (the witness is free), but no independent check (violates P6) |
| Gemini twice (two prompts or two models) | ≈ USD 0.61 | Correlated errors; not independent |
| **Adaptive: Gemini + witness (chosen)** | **≈ USD 0.35** all digital, **≈ 0.44** all scanned | — |

## Consequences

- Reading cost falls more than 10× (≈ USD 0.35 vs 4.9 for S1's statements and invoices). Document AI is still used, but where
  it is cheapest and strongest: OCR for scans, and specialized parsers only on demand.
- Gemini reads one page per call; page 1 runs first and passes its header (account, period, column
  order) as context to the other pages, which run in parallel.
- The verifier and the coverage check are pure functions with their own unit tests; they replace the
  two-list row alignment of ADR-004 for the default path. Three-source alignment (escalation,
  `thorough`) reuses the ADR-004 alignment code.
- Gemini reading images instead of the PDF costs slightly more input tokens per page (1,120 at high
  media resolution vs 560 for native PDF input). Independence is worth the ≈ USD 0.0004 per page.
- Spike S1 measures field accuracy of Gemini on page images (high vs ultra-high media resolution) and
  the verifier's agreement on S1–S3 plus a scanned variant.
- Constitution P6 is reworded to "two independent readings" (version 1.1).
