# ADR-022 — Real documents in production; synthetic data for tests

**Status:** Accepted · **Date:** 2026-10-12 · **Amends:** constitution P8 ("Synthetic data only"),
[ADR-009](ADR-009-regions-and-data-residency.md) (residency premise)

## Context

Kredibel was specified as a prototype that only ever sees generated documents. The product is meant
to run on real businesses' statements, invoices, receipts and ledgers: real layouts (a bilingual
Malaysian RHB statement already exposed four verifier rules the synthetic books never did, spike S1),
real currencies and real personal data. A demo on generated data alone does not show that.

## Decision

- **Production runs on real customer documents.** `DATA_CLASS=real` on every deployed service and in
  local development against the cloud project. The owner's own statements and invoices are the first
  real documents, for the end-to-end test and the demo.
- **Tests, evals, fixtures and CI stay synthetic** ([`18`](../18-synthetic-data.md)); real documents
  are never committed and never used as ground truth without the owner's consent.
- **Real-data controls are always on**, not a later hardening step:
  - no content capture: traces and agent events carry IDs, models, tokens and timings, never prompts,
    page text or outputs (`AI_CONTENT_CAPTURE` is refused unless `DATA_CLASS=synthetic`);
  - logs never contain document text, names or account numbers ([`17`](../17-observability.md) §3);
  - account numbers stored masked, matched by keyed hash; tax IDs masked
    ([`14`](../14-security-and-compliance.md) §6);
  - deleting a document removes its records and files, object versions included on request;
  - learning from a workspace's corrections stays inside it unless the owner consents.
- **Residency is a launch condition, not a footnote.** Today Gemini runs on `global` and Document AI
  in `us`, so page content leaves the region during reading. Before onboarding customers whose rules
  require in-region processing (Indonesia's PDP Law, Malaysia's PDPA), the production path of ADR-009
  is applied: in-region endpoints where the models and processors exist, VPC Service Controls around
  the data services, and a compliance review.
- **The UI says what is true:** the brand panel promises that Kredibel only reads documents, never
  moves money and never changes the accounting system; it no longer says "synthetic data only".

## Consequences

- Every new feature is built and reviewed for real data from the start (masking, logging, deletion).
- Real layouts become a source of reading rules; each one found is recorded in docs/07 and, where
  possible, reproduced in a synthetic fixture so tests keep covering it.
- Cost and latency are measured on real documents as well as on the synthetic books.
