# ADR-027 — Subledger detail and company profit and loss

- Status: Accepted for implementation, 14 October 2026
- Scope: Spec 018, product-owner request to extend dashboard and assistant

## Research

A subledger holds detailed activity (customers, suppliers, assets, inventory, payroll). Its control
accounts reconcile to the general ledger. P&L totals come from income and expense GL postings,
with the subledger retaining supporting detail. Invoice payment does not by itself recognize income
or expense. [Oracle, Account Reconciliation and Subledgers](https://docs.oracle.com/en/cloud/saas/financials/26d/faugl/account-reconciliation-and-subledgers.html)
describes posted GL balances and reconciliation to source activity. [ACCA, Sales and purchases in a
computerised accounting system](https://www.accaglobal.com/gb/en/student/exam-support-resources/foundation-level-study-resources/fa1/technical-articles/sales-comp-acc-system.html)
illustrates a credit sale posting receivables and revenue separately.

Cash flow and profit are distinct. [IAS 7](https://www.ifrs.org/issued-standards/list-of-standards/ias-7-statement-of-cash-flows.html/)
describes adjustments for non-cash items and accruals. [IFRS 18](https://www.ifrs.org/issued-standards/list-of-standards/ifrs-18-presentation-and-disclosure-in-financial-statements/)
is effective for annual periods beginning on or after 1 January 2027 (early application permitted),
and changes P&L presentation. A generic IFRS/US GAAP switch is therefore insufficient to establish
statutory compliance. Sources consulted 14 October 2026; this is a management-report design decision.

## Decision

Keep cash-flow framework selection. Add independent company account mappings with two dimensions:

| Dimension | Purpose | Examples |
|---|---|---|
| Subledger family | Source/detail grouping | Receivables, payables, inventory, fixed assets, payroll, cash, general |
| P&L line | Recognition in management report | Revenue, cost of sales, operating expenses, other income, finance costs, income tax, balance sheet |

Compute accrual management P&L from posted GL entries once; never add subledger invoices or bank
payments on top of their GL postings. Revenue/other income = credits minus debits. Expense lines =
debits minus credits. Gross profit = revenue − cost of sales; operating profit = gross profit −
operating expenses; net profit = operating profit + other income − finance costs − income tax.
Balance-sheet mappings contribute no P&L. Company/account mapping is explicit and confirmed by a
person; codes are never inferred from numeric ranges. Tax, owner drawings, capex and loan principal
must not be inferred to be ordinary expenses from their cash direction.

Every report carries coverage, exclusions, source rows and fact IDs. Missing data is unavailable;
incomplete classifications or ledger gaps make it partial. It is never certified as a complete
company income statement solely because imported debits and credits balance.

## Consequences

Ledger population remains the responsibility of spec 005. This feature can report existing posted
entries and shows an honest empty state until they exist. Full subledger/control-account
reconciliation, document-derived accrual suggestions and statutory presentation profiles are future
work. No changes to a person's general ledger or journal posting are made by Kredibel.
