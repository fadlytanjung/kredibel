# Spec 007 — Cash Flow & Reconciliation

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 |
| **Owner role** | B: Risk engine (+ A for the categorizer prompt) |
| **Depends on** | 005, 006 |
| **Requirements** | FR-027, FR-028, FR-029, P0-08, P0-09, P0-10 |
| **Design** | [`docs/08`](../../08-risk-engine.md) §2.6, §4–§6; `contracts/policy/categorization-rules.v1.yaml` |

## Summary

Categorize every transaction into IAS 7 classes, compute monthly and aggregate cash-flow metrics as
citable facts, match sales invoices to bank credits, and raise the P0 case-level findings (R01, R02,
C01, C02, B01, B04).

## User stories

### US-007-1: Categorize

- **AC-007-1** Precedence is analyst override → internal-transfer rule (applicant names, aliases and
  declared accounts) → related-party rule (P1, spec 014) → keyword rules (YAML order) → model;
  `categorizedBy` and confidence are stored.
- **AC-007-2** On S1, payroll, utilities, tax, bank fees, rent and loan repayments are categorized by
  rules; customer receipts end up `SALES_RECEIPT`; transfers to the owner `OWNER_DRAWING`.
- **AC-007-3** The model categorizes remaining transactions in batches of ≤ 100 with `MODEL_LITE`;
  confidence < 0.5 → `UNKNOWN`; categorization accuracy on S1–S3 ≥ 0.85 macro-F1 (eval, not gate).
  The same call returns a cleaned counterparty name and kind for rows whose name the rules could not
  parse (used by spec 014).
- **AC-007-4** Re-running does not overwrite `ANALYST` categories.

### US-007-2: Metrics

- **AC-007-5** `analysis/{runId}.monthly` has one entry per covered month with the fields of
  [`docs/08`](../../08-risk-engine.md) §5.1; ADB uses carried-forward end-of-day balances.
- **AC-007-6** Aggregates and facts (§5.2) are published with `fact:` IDs, decimal-string values, units
  and inputs; values on S1 match `truth.json` expected metrics to the unit.
- **AC-007-7** The proposed installment uses the annuity formula with the policy rate unless the case
  has an installment override.

### US-007-3: Reconcile

- **AC-007-8** Each sales invoice gets `match.status` and `method` per the algorithm of §6; on S1 all
  due invoices are `MATCHED` (one `NET_OF_TAX`, one `SPLIT`) and one is `NOT_DUE`.
- **AC-007-9** On S3, the 5 fake invoices are `UNMATCHED`; `revenue_verification_ratio < 0.5`;
  `R01` (HIGH) lists each unmatched invoice as evidence; `R02` (HIGH) is raised.
- **AC-007-10** Matched transactions record `matchedInvoiceIds`; assignment is deterministic.

### US-007-4: Behaviour & cash-flow findings

- **AC-007-11** `C01` when DSCR proxy < 1.25 (MEDIUM) / < 1.0 (HIGH); `C02` when negative days ≥ 3;
  `B01` for any `GAMBLING` transaction; `B04` for returned items, each with evidence (transactions or
  facts).
- **AC-007-12** S1 raises none of these.

### US-007-5: Read the results

- **AC-007-13** `GET /api/cases/{id}/transactions` supports filters (doc, month, category, risk tag,
  text) with cursor pagination; `GET /api/cases/{id}/invoices` returns invoices with match details;
  `GET /api/cases/{id}/analysis` returns monthly flows, facts and reconciliation (scorecard follows in
  008).

## Out of scope

P1 checks (C03, C04, B02, B03, B05, B06, R03), purchase-invoice matching, analyst re-categorization UI.
