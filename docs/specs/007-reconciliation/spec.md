# Spec 007 — Categorization and Month Reconciliation

| | |
|---|---|
| **Status** | In progress |
| **Priority** | P0 · P1 (`R03`, `B03`, `X07`) |
| **Owner role** | B: Risk engine (+ A for the categorizer) |
| **Depends on** | 004, 005, 006 |
| **Requirements** | FR-024, FR-030, FR-031, FR-032, FR-035, FR-036, FR-037, FR-038, FR-040, NFR-05, NFR-09, P0-08, P0-09 |
| **Design** | [`docs/08`](../../08-risk-engine.md) §2.6–§2.7, §4.1, §5, §6; `contracts/policy/reconciliation.v1.yaml`, `categorization-rules.v1.yaml` |

## Summary

Bank lines are categorized (rules first, Gemini for the rest). Each month is then **reconciled from
all its data**: bank lines are matched to invoices, receipts and ledger cash entries; documents are
matched to ledger entries; only unique, high-scoring candidates are confirmed automatically, and every
match records why. Month figures and cross-document checks follow. Same data in any order, same
result.

Bank statements anchor **bank cash movement**, independently of document support. An invoice
without a statement waits; a statement row without an invoice is **Bank recorded · No supporting
document**. A person may approve a document or confirm payment without bank evidence as separate
audited actions. Neither creates bank cash. See [ADR-025](../../adr/ADR-025-bank-evidence-and-document-support.md).
This extends P0 with manual attestations and clarifies the existing bank-first design.

## User stories

### US-007-1: Every bank line has a category

- **AC-007-1** Precedence of [`docs/08`](../../08-risk-engine.md) §4.1: user correction, a match,
  internal transfer, keyword rules, then `txn_categorizer` in batches of 100; confidence < 0.5 →
  `UNKNOWN`; each line records `categorizedBy` and its cash-flow class and risk tags.
- **AC-007-2** `PATCH /api/bank-lines/{txId}` sets a category (`categorizedBy: USER`), which no re-run
  overwrites, and marks the month dirty.

### US-007-2: Months reconcile themselves

- **AC-007-3** `reconcile_month(month, data, decisions)` is pure; it reads the month's data and the
  neighbouring months (± 1) and the user's decisions (manual matches, rejected proposals, corrected
  values, duplicate decisions, ignored items); held records are excluded.
- **AC-007-4** Supported matches ([`docs/08`](../../08-risk-engine.md) §6.2): bank credit ↔ sales
  invoice(s) (exact, net of withholding, split into 2–3 credits, several invoices in one credit); bank
  debit ↔ purchase invoice(s) or a card/transfer receipt; bank line ↔ ledger cash entry; invoice or
  receipt ↔ ledger entry.
- **AC-007-5** Scoring and assignment as [`docs/08`](../../08-risk-engine.md) §6.3; `AUTO` only when
  the best score ≥ 0.85, the runner-up is < best − 0.10 and no value used is `CONFLICT`; otherwise
  `PROPOSED` (≥ 0.60) or none. Every match stores reason codes and a plain-language reason.
- **AC-007-6** Payment states on documents (`PAID`, `PARTIAL`, `UNPAID`, `NOT_DUE`,
  `WAITING_FOR_STATEMENT`) and match states on lines and entries are written from the result.
- **AC-007-7** **Order independence:** a property test over random permutations of a month's inputs
  gives identical matches, figures and items; S5 equals S1 by deterministic IDs.
- **AC-007-8** On S1: ≥ 85% of bank lines matched automatically, **0** automatic matches that
  `truth.json` does not list, and the ambiguous February pair is `PROPOSED`, never `AUTO`.

### US-007-3: Month figures and checks

- **AC-007-9** Figures of [`docs/08`](../../08-risk-engine.md) §5 are written as facts with IDs
  (`fact:2026-03:money_in`) and inputs.
- **AC-007-10** Month checks run with evidence: `X01`, `X02`, `X08`, `X09`, `R01`, `R02`, `B01`,
  `B04`, `C02`, `D07` ([`docs/08`](../../08-risk-engine.md) §2.2, §2.6, §2.7).
- **AC-007-11** S4: `X08` (HIGH) names both supplier accounts (masked) and the payment; two `R02`
  findings for the Bluewater Trading Co. invoices. The `double-payment` fixture raises `D07`.

### US-007-4: See a month

- **AC-007-12** `/months` lists months (state, statement per account, auto-match rate, open items,
  risk); `/months/:month` shows the figures, the bank lines with their match state and reason, the
  documents waiting or unpaid, the ledger difference, and the findings; on phones the lines become
  cards and the reasons expand on tap.
- **AC-007-13** From a bank line I can open its match (both sides with reasons) and **unmatch**
  (`DELETE /api/matches/{id}`) or **match manually** (`POST /api/matches`) with a picker of candidates
  that shows amounts and the remaining difference; the month re-reconciles.

### US-007-5: Understand what the evidence proves

- **AC-007-14** Given an eligible statement row without supporting documents, when the month is
  computed, then it contributes once to bank cash and reads **Bank recorded · No supporting
  document**. Missing support alone is informational; integrity, coverage and ledger issues are
  separate. Statement presence alone never produces `RECONCILED`.
- **AC-007-15** Given an invoice/receipt whose payment window is not covered by statements, when
  it is read, then it waits without an unpaid accusation. When covering statements arrive, matching
  reruns automatically, including cross-month payments and gaps in account/date coverage.
- **AC-007-16** Given a document without a bank match, when a person approves the document or
  confirms payment, then these are distinct audited decisions. Approval never implies payment;
  payment confirmation records amount, currency, date, method and reason, shows **No bank evidence**,
  preserves partial payment and never changes bank totals. Later evidence preserves the history
  without double counting. This action is available even without an open review item.
- **AC-007-17** Given candidate matches, when scoring, then currency and direction must agree,
  each date is within the policy window, and tolerance is currency-specific. Amount, party,
  reference and date contributions are inspectable. Amount alone cannot auto-confirm; tax-like
  shortfalls require review unless an explicit adjustment is confirmed. Cash/unknown-method receipts
  do not automatically match bank debits. The fixed workspace currency selects the tolerance.
- **AC-007-18** Given a grouped payment, when displayed, then each invoice/allocation, the bank
  total, remaining difference and reasons are visible. One-to-many and many-to-one compete against
  single matches before any assignment. No record is silently consumed twice within a match kind.
  Extraction, integrity, bank evidence, support and manual approval are separate labels in the mock
  and future page, at mobile, tablet and desktop widths.
- **AC-007-19** Given a workspace fixed to MYR and a document printed in IDR, when read, then ask
  for agreement before using its amounts as MYR **without conversion**. Until accepted it is
  excluded from totals/matching. Acceptance preserves numeric values and printed currency, records
  an audited override and uses MYR tolerances. No exchange rates or FX totals. A document that
  prints no currency is read as MYR without asking, and says "No currency printed: read as MYR".

## Delivery boundaries

The statement/invoice/receipt path can be delivered before ledger import and the review queue.
Its month state comes from computed allocations, statement coverage and blocking findings, never
statement presence alone. `COLLECTING` means coverage is missing; `NEEDS_REVIEW` means a proposal or
blocking finding remains. `RECONCILED` describes the eligible inputs checked in that run, not a risk
assessment, ledger reconciliation or sign-off. Unimplemented stages explicitly report that they
were skipped.

The category correction endpoint previously bundled into T007-02 moves to T007-09 with the books
API. Completing this spec still requires ledger pairs, cross-month upload-order verification and
the full S1/S4/S5 scenario gates. The five-document replay in T007-08a proves the document-first
path and fixed-currency decisions; it does not satisfy those broader gates or complete specs
005/006. Manual match controls and the reconciliation UI remain T007-09/T007-10.

## Out of scope

Risk levels and explanations (008), the review queue (009), the money flow (010), sign-off (015).
