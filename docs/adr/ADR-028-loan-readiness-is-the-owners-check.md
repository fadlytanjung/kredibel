# ADR-028 — Loan readiness is the owner's check, not a credit decision

**Status:** Accepted · **Date:** 23 Nov 2026 · **Scope:** spec 025

## Context

ADR-015 made Kredibel a finance workspace for a business's own books and removed the lender's side
(applicants, cases, a scorecard, a credit memo). It kept a "Loan readiness report" as coming soon:
the same verified data, shown to a lender. Small businesses in the region are asked for months of
bank statements, sales and payables when they apply for credit, and the person who checks them does
it by hand. Kredibel already holds those books checked.

## Options

1. **A credit score.** A number a lender could act on. Rejected: it is the lender's decision, needs
   data we do not have (credit bureau, collateral), and would bring back what ADR-015 removed.
2. **A model-written summary for lenders.** Rejected for now: a model would phrase figures it did not
   compute, and the grounding guard would be the only safeguard on a document meant for a third
   party.
3. **The owner's readiness check, computed by code** (chosen). A level that says whether the books
   are ready to show (Ready, Almost ready, Not ready yet), the checks behind it with their evidence
   and next steps, and the figures a lender reads first; printed or saved as a PDF by the owner.

## Decision

Option 3. The thresholds are policy (`contracts/policy/readiness.v1.yaml`); the level never uses
words of lending ("approved", "creditworthy", "score"). The only model-written words are each
month's risk explanation, which the month run already verified (spec 008); an unverified one is
left out. The report is read-only and computed on request; nothing new is stored. The page states
that it is not a credit decision.

## Consequences

- Plan and usage and the pricing page stop listing the report as coming soon (FR-005); FR-077 is new.
- A lender's own access (a shared link, a lender account) is out of scope; the owner hands over a PDF.
- Revisit when lenders ask for a machine-readable export, or when a person's sign-off of a month
  (spec 015, T015-03) exists: a signed-off month is a stronger fact for the report than a reconciled one.
