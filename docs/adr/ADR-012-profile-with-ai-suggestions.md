# ADR-012 — Workspace profile, filled by the user and suggested by the AI

**Status:** Accepted · **Date:** 2026-10-10 · **Revised by:** [ADR-015](ADR-015-scope-finance-workspace-not-loan-review.md)
(the profile belongs to the workspace itself, not to a loan applicant)

## Context

A workspace is one business or person. Signing up should ask for little: individual or company, a
name, an industry, maybe the main bank account. Much more is printed in the documents they upload:
statement headers show account holders and numbers, sales invoices show the business's tax ID and
address, and the books show who the clients and suppliers are, and **which bank accounts suppliers
were paid to**.

## Decision

- **The profile lives on the workspace** (`orgs/{orgId}.entityType`, `profile`, `bankAccounts`).
  Onboarding asks only for type, name, industry and time zone; the first bank account is optional.
- **The AI suggests; the user accepts.** The month workflow creates **suggestions** (bank account, tax
  ID, address; P1: alias, related party), each with evidence and a confidence from the reading
  status. Nothing is written to the profile until the user accepts. Rejected values are not suggested
  again.
- **Counterparties are derived from the books** (`orgs/{orgId}/counterparties`): clients, suppliers,
  lenders, the owner, government, with totals per month and the **bank accounts seen** for each
  (masked; hashes server-only). Roles are decided in code from categories, documents and matches; the
  model only normalizes messy names inside the categorization call.
- **The profile feeds checks:** holder match (`X05`), undeclared accounts (`X06`), changed supplier
  account (`X08`), invoice tax-ID mismatch (`X07`, P1).

## Alternatives considered

| Option | Why not |
|---|---|
| A long onboarding form | People abandon it; the documents already contain the data |
| Let the model write the profile directly | Breaks P4/P5: a document could plant data the user never saw |
| Company registry and identity checks | Needs external registries and real identity data; out of scope (P7, P8) |

## Consequences

- Personal data stays small: account numbers masked plus a hash for matching; tax IDs masked
  ([`14`](../14-security-and-compliance.md) §6).
- The demo gains a moment: "Kredibel found your tax ID and a second bank account, each with the page
  it came from. Accept?", and the supplier whose account changed in May.
