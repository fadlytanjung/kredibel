# ADR-022 — The owner's own documents for end-to-end testing and the demo

**Status:** Accepted · **Date:** 2026-10-12 · **Amends:** constitution P8 ("Synthetic data only")

## Context

The synthetic books ([`18`](../18-synthetic-data.md)) prove the pipeline against known truth, but a
reviewer asks what happens with a real bank's statement: its layout, its wording, its currency. The
project owner wants to run their own Malaysian bank statements (RHB, MYR) and invoices through the
deployed app and show that in the demo video.

## Decision

- **Allowed:** the project owner's own documents, uploaded by the owner into their own workspace, for
  end-to-end testing and the demo. Nobody else's documents, and no customer data.
- **Never in the repository:** real files stay on the owner's machine and in the workspace's bucket.
  Tests, evals, fixtures and the generator's demo set stay synthetic; real documents are not truth.
- **Treated as real data:** `DATA_CLASS=real` on every service and in local development, so
  `AI_CONTENT_CAPTURE` cannot be turned on (start-up refuses): traces and agent events carry IDs,
  models, tokens and timings, never prompts, page text or outputs. Logs never contain document text,
  names or account numbers ([`14`](../14-security-and-compliance.md) §6, [`17`](../17-observability.md) §3).
- **Data leaves the region for reading:** Gemini runs on the `global` endpoint and Document AI in `us`
  ([ADR-009](ADR-009-regions-and-data-residency.md)); the owner accepts this for their own documents.
- **Deletion:** deleting a document removes its records and files; the bucket's object versions are
  removed with it when the owner asks (`gcloud storage rm --all-versions`), otherwise after 7 days.
- **Learning stays off:** no labels or examples from these documents leave the workspace
  (`learning.shareVerifiedLabels` stays false).

## Consequences

- Reading must cope with real layouts and a non-IDR currency: the workspace currency is MYR
  ([ADR-020](ADR-020-workspace-currency-chosen-at-onboarding.md)); a statement in another currency than
  the workspace's becomes a review item, never a silent conversion.
- The demo video may show the owner's own figures; account numbers are masked in the UI (`••••1234`).
