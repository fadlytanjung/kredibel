# ADR-009 — Regions and the data-residency path

**Status:** Accepted for the prototype · **Date:** 2026-10-10

## Context

Businesses and accounting firms in Indonesia and the region expect financial data to stay in-region. In the
prototype, all Document AI processors sit in `us` (the optional Bank Statement Parser is only offered
in `us`/`eu`), and the newest Gemini models are
broadly available on the `global` endpoint. The prototype processes **synthetic data only**.

## Decision

- **Prototype:** state (Firestore, GCS, Cloud Tasks, Cloud Run) in `asia-southeast1`; Document AI in
  `us`; Gemini on `global`; Model Armor regional. Acceptable because no real data exists (P8).
- **Production path (documented, not built):**
  1. Run the witness (Enterprise OCR) and any escalation parser in-region where offered (Custom
     Extractor is offered in `asia-southeast1`); the text-layer witness already runs inside our
     container, so digital PDFs need no extra service; keep the reader/witness independence of ADR-010.
  2. Pin Gemini calls to an in-region endpoint where the chosen models are available, or to a
     jurisdictional endpoint that satisfies the customer's policy.
  3. Consider `asia-southeast2` (Jakarta) for state if a customer requires in-country storage.
  4. Wrap Document AI, Agent Platform, Storage and Firestore in a VPC Service Controls perimeter.

## Consequences

- The architecture keeps location as configuration (`DOCAI_LOCATION`, `GOOGLE_CLOUD_LOCATION`,
  `REGION`), so the move is configuration plus a processor swap.
- The pitch states the residency path explicitly; judges from BFSI will ask.
