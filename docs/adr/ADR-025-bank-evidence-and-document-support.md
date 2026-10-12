# ADR-025 — Bank evidence and document support are separate

**Status:** Accepted · **Date:** 12 Oct 2026 · **Scope:** spec 007, P0 clarification and extension

## Context

The product owner clarified that a bank statement anchors cash movement, but a bank row need not
have one invoice: it may cover several invoices, a bank charge, payroll, or an unsupported payment.
Invoices and receipts may arrive before the statement. A person may verify a document or confirm
payment without bank evidence. Extraction completion does not implement this reconciliation flow.

## Decision

Keep four independent dimensions: processing, document integrity, payment evidence and supporting
documents. Never use an unqualified **Verified** badge for all four.

| Situation | User-facing label | Effect on bank cash totals |
|---|---|---|
| Eligible statement transaction, no support attached | Bank recorded · No supporting document | Include once |
| Confirmed one-to-one, grouped or split match | Bank recorded · Matched to documents | Still include once |
| Invoice/receipt, payment window not covered by statements | Waiting for statement | None |
| Person approves the document | Document approved | None; makes no payment claim |
| Person confirms payment without a bank match | Payment confirmed by you · No bank evidence | None; keep separately from bank-confirmed payments |
| Possible match or inconsistent evidence | Choose a match / Check evidence | Never invent or alter a bank amount |

An uploaded statement is still untrusted input and retains its integrity findings. **Bank recorded**
means the transaction was read from the statement, not that the bank authenticated the file or that
the expense is valid. Failed, quarantined and held copies cannot contribute to trusted totals.
Conflicting values and integrity findings remain visible and block an unqualified month completion.

Manual document approval and payment confirmation are distinct audited decisions. Payment
confirmation requires a reason, payment date, amount, currency and method; partial payments remain
partial. It never fabricates a bank line, bank match or cash flow. A later statement may provide bank
evidence, preserving the decision history and avoiding double counting. Document approval alone never
marks an invoice paid. Neither decision overwrites a confirmed/corrected classification (spec 016).

Missing support is informational by default, not an accusation or automatically a blocking review
item. Ambiguous matches, contradictory values, missing required statement coverage and ledger
differences remain actionable. A person can mark support as not required with a reason. A month is
reconciled only after actual computation, statement coverage checks and resolution of blockers;
the presence of one statement is insufficient.

Each workspace has one fixed currency chosen at onboarding; there is no FX feature. Preserve the
printed currency. If it differs (or is unknown), ask the user to accept the numeric amounts as the
workspace currency **without conversion**, or replace the document. For example: “This document
says IDR. Use its amounts as MYR without conversion?” Until explicitly accepted, exclude it from
totals and matching. Store the original currency and the audited decision separately; never silently
relabel source evidence. T007-06a owns the decision contract and UI, including statement documents.

Matching considers accepted workspace currency, direction and payment date eligibility first, then amount, party and
reference evidence. One bank row can settle up to the policy's maximum number of invoices; several
bank rows can settle one invoice. Both conserve the original bank amounts. Ambiguity is checked
across every competing allocation. Amount equality alone is never enough for an automatic match.
An approximate shortfall is a possible withholding adjustment, not proof of tax.

## Consequences and rollout

The bank evidence labels and manual decisions extend P0 in spec 007. This is not the P1 learning or
label-management feature. Implement pure scoring first, then assignment and state derivation, then
versioned persistence/API decisions, workflow integration, and the screens. No schema changes are
made by this ADR; T007-06a owns the OpenAPI contract, versions, upcasters and migration before writes.
Current extraction models and API payment enums must not be overloaded to store these new meanings.

Product precedents (not universal accounting thresholds): [Xero grouped reconciliation](https://central.xero.com/0/article/View-bank-reconciliation-details)
and [Oracle tolerance rules](https://docs.oracle.com/en/cloud/saas/financials/26b/faipp/overview-of-tolerance-rules.html).

## Audit of the current implementation and mocks

- Reading, classification, grounding and most document forensics exist. `reconcile`, `check_month`
  and review synchronization are still stubs; a successful run is not evidence of matching.
- The old finalizer incorrectly inferred `RECONCILED` from statement presence. Until real results
  exist, keep the month collecting and explicitly note that reconciliation is not available yet.
- `month.html` focuses on the edited March statement. Keep that evidence example; add
  `reconciliation.html` with the ordinary upload-first, statement-only and grouped-payment paths.
- The current library's processing badge must not become a payment badge. The future month page
  shows bank evidence and support separately; dashboards link to those states without counting
  unsupported bank rows as inherently fraudulent.
- The fixed IDR tolerance is unsafe for MYR workspaces. Keep the existing IDR baseline and select
  the absolute floor by the fixed workspace currency, including after an explicit document override.
