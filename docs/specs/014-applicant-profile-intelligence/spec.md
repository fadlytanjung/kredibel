# Spec 014 — Applicant Profile Intelligence

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 (counterparty directory, header-based suggestions, `X06`, Applicant tab) · P1 (related parties, key clients/suppliers, `X07`, `B07`, pre-fill on upload, applicant list page) |
| **Owner role** | B: Risk engine (domain) + C: Frontend (Applicant tab) + A: Agents (counterparty names in the categorizer) |
| **Depends on** | 003 (applicants), 005 (verified headers), 007 (categories, reconciliation) |
| **Requirements** | FR-075 – FR-081, P0-20, P0-21, P1-13 – P1-15 |
| **Design** | [ADR-012](../../adr/ADR-012-applicant-profile-with-ai-suggestions.md), [`docs/08`](../../08-risk-engine.md) §2.5, §4.3, §4.4, [`docs/09`](../../09-data-model.md) §3.13–§3.17, [`docs/11`](../../11-frontend.md) §6.5a |

## Summary

Analysts onboard applicants with as little or as much as they have (spec 003). After an analysis
run, Kredibel compares the documents with the profile and **suggests** what is missing or different:
bank accounts from statement headers, tax ID and address from invoices, spelling aliases, and (P1)
related parties and key clients/suppliers. It also builds a **counterparty directory** (clients,
suppliers, lenders, own accounts, related parties, other payees) from the transactions, invoices and
reconciliation. Every suggestion carries evidence and waits for an analyst's **Accept** or
**Reject**. The profile then feeds the holder, account, tax-ID and related-party checks.

## User stories

### US-014-1: Counterparty directory

- **AC-014-1** After a run, `cases/{id}/counterparties/*` exist for that run with roles assigned in
  code per [`docs/08`](../../08-risk-engine.md) §4.3. On S1 seed-1 the six customers are `CLIENT`, the
  three suppliers `SUPPLIER`, `ANDI PRATAMA` is `RELATED_PARTY` (declared beneficial owner), and the
  unnamed buckets "Loan installments" and "VAT payments" are `LENDER` and `GOVERNMENT`, matching
  `truth.json`.
- **AC-014-2** The categorizer returns a cleaned counterparty name and kind for rows the rules could
  not parse; spellings with `token_set_ratio ≥ 90` merge into one counterparty with `aliases`.
- **AC-014-3** `GET /api/cases/{id}/counterparties?role=` returns the current run's list, largest flow
  first, with a summary (`clients`, `suppliers`, `topClientShare`). Facts `fact:client_count` and
  `fact:top_client_share` are published for the memo.
- **AC-014-4** Each transaction gets `counterpartyId`; the Cash flow tab filters by counterparty.

### US-014-2: Profile suggestions

- **AC-014-5** `build_applicant_profile` creates suggestions per [`docs/08`](../../08-risk-engine.md)
  §4.4 with evidence. On S1 seed-1, for an applicant with no tax ID and no address: one `TAX_ID`
  (`HIGH`, evidence on ≥ 2 invoices) and one `ADDRESS` (`MEDIUM`); a declared operating account that
  matches the statements produces no `BANK_ACCOUNT` suggestion.
- **AC-014-6** For an applicant with no declared accounts, each distinct statement account yields one
  `BANK_ACCOUNT` suggestion (`HIGH` when the header values are `AGREED`) with the statement's page-1
  box as evidence.
- **AC-014-7** Suggestion IDs are deterministic: a re-run creates no duplicates, never reopens an
  `ACCEPTED` or `REJECTED` suggestion, and never re-suggests a rejected value.
- **AC-014-8** A suggestion that contradicts a single-valued field (tax ID, legal name) is stored as
  `CONFLICT` with `conflictWith`.
- **AC-014-9** Accepting writes into the profile: `BANK_ACCOUNT` → `bankAccounts` (`source: DETECTED`,
  hash in `orgPrivate`); `TAX_ID` → `company.taxId`; `ADDRESS` → `address`; `LEGAL_NAME` → `aliases`;
  (P1) `RELATED_PARTY` → `relatedParties` with the roles given in the decision; (P1) `KEY_CLIENT`/
  `KEY_SUPPLIER` → `keyCounterparties`. Each decision writes `SUGGESTION_ACCEPTED` or
  `SUGGESTION_REJECTED` to the applicant's events and updates `pendingSuggestions`.
- **AC-014-10** Deciding a suggestion that is not `PENDING`/`CONFLICT` → `409 SUGGESTION_ALREADY_DECIDED`.
  Accepting a `RELATED_PARTY` suggestion without roles → `422 VALIDATION_ERROR`.

### US-014-3: Checks that use the profile

- **AC-014-11** `X05` compares the statement holder with the applicant's legal or full name, trading
  name, accepted aliases and declared account holders. S1's holder matches; a T6 fixture statement held
  by "Sunrise Trading Partners" raises `X05` (HIGH).
- **AC-014-12** `X06_UNDECLARED_ACCOUNT` (LOW) is raised for a statement account that matches none of
  the declared accounts, only when at least one account is declared; S1 with its operating account
  declared raises none; the fixture with an extra undeclared account raises one, plus a
  `BANK_ACCOUNT` suggestion.
- **AC-014-13** (P1) `X07_TAX_ID_MISMATCH` (HIGH) when a sales invoice's issuer tax ID differs from the
  profile's, with both values as facts and the invoice box as evidence.
- **AC-014-14** (P1) Credits from a declared or accepted related party are categorized `OWNER_CAPITAL`
  (not `SALES_RECEIPT`) and leave operating inflow; `B07_RELATED_PARTY_FLOWS` (MEDIUM) above the
  thresholds in `forensics.v1.yaml`; scenario S7 matches its truth.

### US-014-4: Applicant tab

- **AC-014-15** The case's **Applicant** tab shows the profile, the suggestions (pending first, with
  confidence, basis and an evidence chip that opens the page with the box highlighted) and the
  counterparties by role. Accept and Reject update the profile and the tab badge without a reload.
- **AC-014-16** The memo's "business" section states applicant type, legal form, years operating and
  the top client's share of inflows, with citations to `fact:top_client_share` and
  `fact:client_count`.

### US-014-5: Pre-fill on upload (P1)

- **AC-014-17** With `PREFILL_ON_UPLOAD=on`, uploading a statement or invoice enqueues a light task that
  reads page 1 with the same cache key the run will use (so the run does not pay again) and creates
  header-based suggestions (`BANK_ACCOUNT`, `TAX_ID`, `ADDRESS`) before any analysis. It counts
  against the plan's pages like a run.

### US-014-6: Applicant list (P1)

- **AC-014-18** `/applicants` lists applicants with type, cases and pending suggestions; name prefix
  search; the detail page lists the applicant's cases.

## Out of scope

Registry lookups (company registry, tax office), identity-document verification, sanctions and PEP
screening, automatic profile writes, sharing applicants across workspaces.

## Edge cases

- The profile changes after a run: past findings stay as they were; the next run uses the new
  profile.
- A counterparty that also matches the applicant's own names is `OWN_ACCOUNT`, never `CLIENT`.
- Individual applicants pay many people for personal reasons: a `PERSON` counterparty is suggested as
  a related party only above the monthly-pattern thresholds of [`docs/08`](../../08-risk-engine.md)
  §4.4, always as `LOW`.
- Two applicants declaring the same account number are allowed; the second gets an `INFO` note in the
  API response (`sharedWithApplicantId`), not a finding.
