# Spec 014 — Profile Suggestions and Counterparties

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 (counterparties, accounts seen, `BANK_ACCOUNT`/`TAX_ID`/`ADDRESS` suggestions) · P1 (aliases, related parties) |
| **Owner role** | B: Risk engine + C: Frontend |
| **Depends on** | 005, 007, 013 |
| **Requirements** | FR-060, FR-061, FR-062, P0-14 |
| **Design** | [`docs/08`](../../08-risk-engine.md) §4.2–§4.3; [ADR-012](../../adr/ADR-012-profile-with-ai-suggestions.md) |

## Summary

Kredibel learns from the documents without changing anything on its own. It derives the business's
**clients and suppliers** from the books (with totals per month and **the bank accounts each supplier
was paid to**, which powers the payment-diversion check `X08`), and it **suggests** profile facts it
found (a bank account not declared yet, the tax ID printed on sales invoices, the address) with
evidence; the user accepts or rejects each one.

## User stories

### US-014-1: Clients and suppliers

- **AC-014-1** `build_counterparties` (month workflow) groups bank lines, invoices and receipts by
  normalized name (`token_set_ratio ≥ 90` merges spellings), assigns roles in code
  ([`docs/08`](../../08-risk-engine.md) §4.2), keeps totals per month, first and last dates, sample
  evidence and **accounts seen** (masked; hashes in `orgPrivate`), and puts unnamed lines into named
  buckets ("VAT payments", "Bank fees").
- **AC-014-2** `/counterparties` lists clients and suppliers with money in and out for the period,
  open invoices, and a marker when a supplier was paid to more than one account; a counterparty page
  shows its months, its documents, its bank lines and its accounts with first and last use.
- **AC-014-3** On S1 the counterparties equal `truth.json.expectedCounterparties` (names, roles, one
  account each); on S4 Roastline Equipment Service shows two accounts.

### US-014-2: Suggestions, never silent changes

- **AC-014-4** `build_profile_suggestions` creates `BANK_ACCOUNT` (statement account not among the
  workspace's), `TAX_ID` (issuer tax ID on the workspace's sales invoices, when the profile has none)
  and `ADDRESS` (statement holder or invoice issuer address, when the profile has none) with
  confidence, basis and evidence; IDs are deterministic.
- **AC-014-5** `PATCH /api/suggestions/{id}` with `ACCEPT` writes the value into the profile (bank
  accounts get mask + hash) and records `SUGGESTION_ACCEPTED`; `REJECT` records
  `SUGGESTION_REJECTED`, and the same value is never suggested again; a decided suggestion →
  `409 SUGGESTION_ALREADY_DECIDED`.
- **AC-014-6** A suggestion that contradicts a single-valued field is `CONFLICT` and shows both values.
- **AC-014-7** Suggestions appear as a small card on the dashboard ("Kredibel found 2 details for
  your profile") and in Settings → Profile; on S1 they equal `truth.json.expectedSuggestions`.

### US-014-3: P1

- **AC-014-8** `ALIAS` suggestions (spellings of the workspace's name) and `RELATED_PARTY` suggestions
  (a person receiving owner drawings in ≥ 3 months).

## Out of scope

Editing counterparties by hand (merge or split, later), external company registries.
