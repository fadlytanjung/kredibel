# ADR-015 — Scope: a finance workspace that checks your books, not loan review

**Status:** Accepted · **Date:** 2026-10-10 · **Supersedes:** the loan-review scope of
[`01`](../01-brainstorm-and-decision.md) §5, ADR-007 (case decision state machine) and the scoring
and memo parts of ADR-005

## Context

The first design (idea C1) made Kredibel a credit analyst's tool: a lender opened a **case** for a
loan applicant, the applicant's documents were analysed, and the case ended with a scorecard, a
credit memo and an approve or decline decision. On review the team found it harder to explain than
the problem it already knows: small businesses and their accountants upload invoices and ledger
entries every day, upload the bank statement at month end, and then spend days matching, chasing
duplicates and wondering whether a document can be trusted. Our previous platform did the reading;
what it lacked was **trust**: proof for every number, duplicate and tamper detection, and an honest
review path for the 15–20% that AI cannot match on its own.

## Decision

1. **Kredibel is a finance workspace for one business or person** (individual or company). The
   workspace *is* the entity whose books are checked. There are no applicants, cases, loan requests,
   scorecards, credit memos or approve/decline decisions.
2. **Documents in any order.** Bank statements, sales and purchase invoices, receipts and
   general-ledger exports (CSV or Excel) go into one library. Each is read and checked when it
   arrives. Every calendar **month** is reconciled automatically and **incrementally**: a statement
   uploaded before its invoices, or after, ends in the same result.
3. **Checks before trust:** duplicate detection (same file, same statement period, same invoice,
   same receipt, same ledger entry), document integrity forensics (the existing two-readings rule,
   P6), and anomaly checks across documents (invoices never paid, payments to a changed supplier
   account, ledger and bank disagreeing).
4. **Fraud risk is a deterministic level with reasons** per document and per month (policy file
   `contracts/policy/risk.v1.yaml`); Gemini writes the explanation and the recommended next steps,
   grounded on the findings (P2, P3).
5. **Humans fix exceptions in a review queue.** Target: 80–85% of bank lines matched automatically
   on the synthetic scenarios; the rest become review items (match by hand, correct a value,
   confirm a duplicate, ignore). Every fix is audited and triggers a re-reconciliation of its month.
6. **Dashboard first:** a home dashboard (money in and out, money-flow Sankey, month status, risk,
   review count) separate from the tables (Documents, Reconciliation, Review, Risk).
7. **Access control:** the hackathon build has one owner per workspace. Roles for an accounting team
   (accountant uploads, reviewer resolves, viewer reads) are P1.
8. **Loans later:** a "Loan readiness report" built on the same verified data is shown as *coming
   soon*; nothing of it is built.

## Consequences

- Removed: applicant onboarding, cases and loan requests, `scorecard.v1.yaml`, the credit memo and
  grounding guard for memos, the decision panel and its state machine.
- Kept and re-aimed: adaptive reading (ADR-010), forensics and the two-readings rule (P6),
  categorization (now for the money-flow view), reconciliation (now the core), workspaces and plans
  (ADR-011), profile suggestions and counterparties (ADR-012, now for the workspace's own entity),
  versioned data (ADR-013).
- New: duplicate detection, ledger import, receipts, incremental month reconciliation, the review
  queue, the fraud risk level, the dashboard, the Finance Assistant (ADR-014).
- The grounding idea survives where it matters: risk explanations and assistant answers may only cite
  numbers that exist as facts.

## Alternatives considered

| Option | Why not |
|---|---|
| Keep loan review | Harder to explain; depends on a lender persona the team cannot test with; less reuse of our platform |
| Both products now | Too broad for 7 days; the loan report is shown as coming soon instead |
| A case or batch per upload | Forces users to think about containers; months are what accountants close |
