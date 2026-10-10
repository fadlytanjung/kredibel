# ADR-012 — Applicant profile, filled by the analyst and suggested by the AI

**Status:** Accepted · **Date:** 2026-10-10

## Context

A case used to carry a small `borrower` map (name, legal form, industry). Lenders onboard applicants
differently depending on who they are: an **individual** (including sole traders) or a **company**
(with registration and tax IDs, bank accounts and the people who own or control it). Much of this
information is already printed in the documents the applicant hands over: statement headers show
account holders and numbers, invoices show tax IDs, addresses and payment accounts, and the
transactions show who the clients and partners are.

## Decision

- **Applicant is a first-class entity** (`orgs/{orgId}/applicants/{applicantId}`), type `INDIVIDUAL`
  or `COMPANY`, reused across cases. A case references one applicant and keeps a small snapshot.
- **Onboarding asks for little and allows more:** required fields are minimal (name, type, industry,
  years operating, legal form for companies). Bank accounts and related parties (beneficial owners,
  directors, shareholders, guarantors) are optional at creation.
- **The AI suggests; the analyst accepts.** After a run, `build_applicant_profile` creates
  **suggestions** (bank account, tax ID, address, related party, key client, key supplier), each with
  evidence (document, page, box or transactions) and a confidence from the corroboration status.
  Nothing is written to the profile until an analyst accepts it. Rejected values are not suggested
  again.
- **Counterparties are derived per run** (`cases/{caseId}/counterparties`): clients, suppliers,
  lenders, own accounts, related parties and other payees, with totals and evidence. Roles are
  decided in code from categories, invoices and reconciliation; the model only normalizes messy
  names inside the existing categorization call.
- **The profile feeds checks:** holder match (`X05`), undeclared accounts (`X06`), invoice tax-ID
  mismatch (`X07`, P1), related-party flows (`B07`, P1), customer concentration (`B06`, P1).

## Alternatives considered

| Option | Why not |
|---|---|
| Keep the borrower map inside the case | No reuse; no place for accounts and people; no profile to compare against |
| Let the model write the profile directly | Breaks P4/P5: a document could plant data the analyst never saw |
| Full KYC/KYB (registries, ID verification) | Needs external registries and real identity data; out of scope (P7, P8) |

## Consequences

- New collections: `applicants`, `applicants/{id}/suggestions`, `applicants/{id}/events`,
  `cases/{id}/counterparties`. The case API takes `applicantId` (or an inline applicant) instead of
  `borrower`.
- Personal data grows: national ID numbers are never stored in full (last 4 digits only); account
  numbers are stored masked plus a hash for matching ([`14`](../14-security-and-compliance.md) §6).
- The demo gains a moment: "Kredibel found the applicant's tax ID, a second bank account and their six
  biggest clients, each with the page it came from. Accept?"
