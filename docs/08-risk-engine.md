# 08 — Risk Engine

> Everything deterministic that turns extracted data into duplicates, findings, matches, month
> figures, money flows, review items and a fraud risk level. All of it lives in `backend/app/domain/`
> as pure, unit-tested functions. Thresholds come from versioned YAML in `contracts/policy/`
> (`forensics.v1.yaml`, `reconciliation.v1.yaml`, `risk.v1.yaml`), never from code constants.

---

## 1. Findings: the common shape

```python
class EvidenceRef(BaseModel):
    doc_id: str | None = None
    page: int | None = None
    bbox: BBox | None = None          # normalized 0..1, top-left origin
    tx_id: str | None = None          # bank line
    invoice_id: str | None = None
    receipt_id: str | None = None
    ledger_entry_id: str | None = None
    match_id: str | None = None
    fact_id: str | None = None        # e.g. "fact:2026-03:money_in"
    label: str | None = None          # short caption shown in the viewer

class Finding(BaseModel):
    finding_id: str                   # fnd_{sha1(code|anchor)[:16]}; stable across re-runs
    code: str                         # e.g. "A01_RUNNING_BALANCE_BREAK"
    category: Literal["SCREENING", "EXTRACTION", "DUPLICATE", "ARITHMETIC", "STRUCTURE", "VISUAL",
                      "CROSS_DOCUMENT", "RECONCILIATION", "BEHAVIOURAL"]
    scope: Literal["DOCUMENT", "MONTH"]
    doc_id: str | None
    month: str | None                 # "2026-03"
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
    title: str                        # templated, short
    facts: dict[str, str]             # e.g. {"expected": "48500000.00", "printed": "42500000.00"}
    explanation: str | None           # plain language, from the explainer or the template
    next_steps: list[str]             # from risk.v1.yaml actions, phrased by the explainer
    evidence: list[EvidenceRef]
    detected_by: Literal["RULE", "MODEL", "MODEL_ARMOR"]
    corroborated_by: list[str] = []
    status: Literal["OPEN", "ACKNOWLEDGED", "DISMISSED", "RESOLVED"] = "OPEN"
```

Every check implements one interface (`domain/checks/base.py`) and is registered in
`domain/checks/registry.py`; a check runs only when its code is enabled in `forensics.v1.yaml`.

```python
class Check(Protocol):
    code: str
    scope: Literal["DOCUMENT", "MONTH"]
    def applies_to(self, ctx: CheckContext) -> bool: ...
    def run(self, ctx: CheckContext) -> list[Finding]: ...
```

A re-run recomputes a document's or a month's findings and **upserts** them by ID: a finding that no
longer applies becomes `RESOLVED`; `ACKNOWLEDGED` and `DISMISSED` keep their status and history.

---

## 2. Check catalog

"Agreed" means every value used was `AGREED` by the AI reader and the witness
([`07`](07-document-intelligence.md) §6).

### 2.1 Screening and extraction (per document)

| Code | Detects | Severity | P |
|---|---|---|---|
| `S01_EMBEDDED_INSTRUCTIONS` | Model Armor prompt-injection match in the file | CRITICAL | P1 |
| `E01_LOW_EXTRACTION_AGREEMENT` | Agreement < `minAgreement`, or a failing equation with non-agreed values | MEDIUM | P0 |
| `E02_EXTRACTION_FAILED` | Neither reading produced usable output | HIGH | P0 |
| `E03_UNCERTAIN_TYPE` | Classification confidence < 0.6 (the user is asked to confirm the type) | LOW | P0 |
| `E04_MULTIPLE_ACCOUNTS` | More than one account number in one statement | MEDIUM | P1 |
| `E05_PARTY_UNCLEAR` | Neither the issuer nor the buyer of an invoice is the workspace (names, aliases) | LOW | P0 |

### 2.2 Duplicates

| Code | Rule | Severity | Effect | P |
|---|---|---|---|---|
| `D01_EXACT_FILE_DUPLICATE` | SHA-256 of the uploaded bytes equals an existing document's | INFO | Not read, not counted; library shows "Copy of …" | P0 |
| `D02_STATEMENT_PERIOD_DUPLICATE` | Same account (bank + last 4 digits) and statement periods overlapping by ≥ 1 day | HIGH if the overlapping rows differ, MEDIUM if they are identical | Newer document held as possible duplicate | P0 |
| `D03_INVOICE_DUPLICATE` | Same issuer (`token_set_ratio ≥ 90`) and invoice number, or same issuer, issue date and total | MEDIUM | Newer document held | P0 |
| `D04_INVOICE_NUMBER_REUSED` | Same issuer and invoice number with a **different** total or date | HIGH | Both kept; flagged on the later document with the earlier one as evidence | P0 |
| `D05_RECEIPT_DUPLICATE` | Same merchant, date and total (± 1 unit), or page perceptual hash distance ≤ `pHashMaxDistance` (8) without contradictory available merchant/date/total readings; layout similarity alone cannot override different receipt values | MEDIUM | Newer document held | P0 |
| `D06_LEDGER_ENTRY_DUPLICATE` | Two ledger entries with the same date, amount, account and reference (from one or several imports) | MEDIUM | Later entry held | P0 |
| `D07_DOUBLE_PAYMENT` | Two bank debits matched (or matchable) to the same purchase invoice or receipt | HIGH | Second payment goes to review | P0 |

"Held" means the document (or entry) is a **possible duplicate**: its values are excluded from month
figures and matching until the user confirms ("it is a duplicate", values stay excluded) or rejects
("it is a different document", values count). Confirmation is a review item (§7).

### 2.3 Arithmetic (per document)

| Code | Rule | Severity | P |
|---|---|---|---|
| `A01_RUNNING_BALANCE_BREAK` | For consecutive rows: `abs(balance[i-1] + credit[i] − debit[i] − balance[i]) > tol` (tol = 1 unit); the first row uses the opening balance; witness-only rows are included | CRITICAL if agreed and no witness-only row sits between, else `E01` | P0 |
| `A02_OPENING_CLOSING_MISMATCH` | `opening + Σcredits − Σdebits ≠ closing` | CRITICAL if agreed, else `E01` | P0 |
| `A03_PRINTED_TOTALS_MISMATCH` | Printed total credits/debits ≠ sum of rows | HIGH | P1 |
| `A04_INVOICE_TOTAL_MISMATCH` | `Σ lines ≠ subtotal`, `subtotal + tax ≠ total`, or `qty × unit price ≠ line` (tol = 1 unit per line); receipts: neither `Σ items + tax` nor `Σ items` equals the total (prices in our markets often include SST or PPN); checked only when every line or item has an amount | HIGH | P0 |
| `A05_TAX_RATE_INCONSISTENT` | `tax / subtotal` not within ±0.5 pp of any rate in `policy.vatRates` | MEDIUM | P1 |

`A01` reports one finding per broken row and states whether the following rows continue from the
printed (wrong) balance, which shows where the edit was made.

### 2.4 Structure (per document, PDF only)

| Code | Rule | Severity | P |
|---|---|---|---|
| `M01_EDITING_SOFTWARE_PRODUCER` | `Producer`/`Creator` matches `policy.editorProducerPatterns` | MEDIUM | P0 |
| `M02_MODIFIED_AFTER_CREATION` | `ModDate − CreationDate > policy.modifiedAfterCreationMinutes` (10) | MEDIUM | P0 |
| `M03_MULTIPLE_REVISIONS` | > 1 revision: MEDIUM if later revisions only add signatures or annotations; HIGH if they replace page content; CRITICAL (P1) if the revision diff changes numbers | MEDIUM / HIGH / CRITICAL | P0 (detect) / P1 (diff) |
| `M04_FONT_ANOMALY_IN_VALUES` | Among the read transaction values of a page (amounts and balances of its rows; printed totals excluded), one value's font or size is used by < 10% of them. Measured per page, not per column: a short column of 7 credits would hide a single edited value at 14% | HIGH | P0 |
| `M05_COVERED_TEXT` | A filled rectangle overlaps existing characters and new characters are drawn on top | HIGH | P1 |
| `M06_IMAGE_ONLY` | No text layer on a page | INFO | P0 |

### 2.5 Visual (per page, P1)

| Code | Rule | Severity |
|---|---|---|
| `V01_VISUAL_EDIT_SUSPECTED` | Gemini reports a region with signs of editing | MEDIUM; HIGH if corroborated by `A01`, `M04` or `M05` on the same row or an overlapping box (IoU ≥ 0.3). Never CRITICAL. |

### 2.6 Cross-document (per month)

| Code | Rule | Severity | P |
|---|---|---|---|
| `X01_STATEMENT_DISCONTINUITY` | For the same account, `closing(month N) ≠ opening(month N+1)` | HIGH (anchored to the later statement) | P0 |
| `X02_STATEMENT_MISSING` | A month between the first and last statement of an account has no statement | MEDIUM | P0 |
| `X05_ACCOUNT_HOLDER_MISMATCH` | Statement holder matches none of the workspace's names, aliases or declared account holders (`token_set_ratio < 80`) | HIGH | P0 |
| `X06_UNDECLARED_ACCOUNT` | A statement's account is not among the workspace's bank accounts (also creates a `BANK_ACCOUNT` suggestion) | LOW | P0 |
| `X07_TAX_ID_MISMATCH` | A sales invoice's issuer tax ID differs from the workspace's tax ID | HIGH | P1 |
| `X08_SUPPLIER_ACCOUNT_CHANGED` | A purchase invoice's pay-to account, or a bank debit to a known supplier, uses an account not seen before for that supplier while an earlier account exists | HIGH | P0 |
| `X09_LEDGER_BANK_MISMATCH` | For a mapped bank account, ledger cash movement for the month differs from the statement's net movement by > tol; or a ledger cash entry has no bank line within the window | MEDIUM (per entry) / HIGH (month difference > 5%) | P0 |

### 2.7 Reconciliation and behaviour (per month)

| Code | Rule | Severity | P |
|---|---|---|---|
| `R01_SALES_INVOICE_OVERDUE` | A sales invoice unpaid more than `graceDays` after its due date, statements covering that period present (every day from issue to due + grace; otherwise it is waiting for a statement, not overdue); reported in the month it becomes overdue | LOW (MEDIUM if > 10% of the invoiced sales of its issue month) | P0 |
| `R02_SUPPLIER_INVOICE_UNKNOWN_PARTY` | A purchase invoice from a supplier with no bank history and no ledger entry, never paid | MEDIUM | P0 |
| `R03_PAID_BEFORE_ISSUE` | A matched payment dated more than 3 days before the invoice issue date | MEDIUM | P1 |
| `B01_GAMBLING_INDICATORS` | ≥ 1 bank line tagged `GAMBLING` | MEDIUM | P0 |
| `B03_ROUND_TRIPPING` | Same counterparty in and out within 2 days at ±2%, ≥ 2 times | HIGH | P1 |
| `B04_RETURNED_ITEMS` | ≥ 1 bank line tagged `RETURNED_ITEM` (≥ 3 → HIGH) | MEDIUM / HIGH | P0 |
| `C02_NEGATIVE_BALANCE_DAYS` | Days with end-of-day balance < 0 ≥ `negativeDaysThreshold` (3) | MEDIUM | P0 |

---

## 3. Document integrity verdict

Per document, from its own findings (screening, extraction, arithmetic, structure, visual, plus `X01`
anchored to it), top-down:

| Verdict | Rule |
|---|---|
| `TAMPERED` | ≥ 1 CRITICAL finding from `A01`, `A02` or `M03`-with-diff (deterministic, agreed) |
| `SUSPICIOUS` | `S01`, or ≥ 1 HIGH integrity finding, or ≥ 2 MEDIUM integrity findings. Extraction findings (`E0x`) do not count here: they say how well the page was read, not that it was changed, and lead to `UNVERIFIABLE` |
| `UNVERIFIABLE` | `E01` or `E02` present |
| `CLEAN` | none of the above |

Ledger exports have no integrity verdict (no page to tamper with); their checks are `D06` and `X09`.

---

## 4. Categorization, counterparties and profile suggestions

### 4.1 Taxonomy and the accounting framework

The category vocabulary and each category's cash-flow class live in
[`contracts/policy/categories.v1.yaml`](../contracts/policy/categories.v1.yaml). The class depends on
the workspace's **accounting framework** (`profile.accountingFramework`, [ADR-016](adr/ADR-016-human-verified-labels-and-learning-loop.md));
code derives it, a model never sets it.

Each category has a **statement line** (for the dashboard's money flow and cash-flow statement, §5.1
and §5.2) and, per framework, a **cash-flow class** (`OPERATING`, `INVESTING`, `FINANCING`, `NON_CASH`
or `UNCLASSIFIED`). Line names follow each framework's usual wording:

| `category` | Direction | Statement line: IFRS wording / US GAAP wording | Class under IFRS (IAS 7 as amended by IFRS 18) | Class under US GAAP (ASC 230) |
|---|---|---|---|---|
| `SALES_RECEIPT` | in | `REVENUE`: Revenue / Net sales | `OPERATING` | `OPERATING` |
| `OTHER_OPERATING_INCOME` | in | `OTHER_INCOME`: Other income | `OPERATING` | `OPERATING` |
| `INTEREST_RECEIVED` | in | `OTHER_INCOME`: Other income | `INVESTING` | `OPERATING` |
| `INVENTORY_PURCHASE` (goods and materials for sale) | out | `COST_OF_SALES`: Cost of sales / Cost of goods sold | `OPERATING` | `OPERATING` |
| `SUPPLIER_PAYMENT` (services), `PAYROLL`, `RENT`, `UTILITIES`, `BANK_FEES`, `OTHER_OPERATING_EXPENSE` | out | `OPERATING_EXPENSES`: Operating expenses / Selling, general and administrative | `OPERATING` | `OPERATING` |
| `TAX_PAYMENT` | out | `INCOME_TAX`: Taxes paid | `OPERATING` | `OPERATING` |
| `INTEREST_PAID` | out | `FINANCE_COSTS`: Finance costs / Interest expense | `FINANCING` | `OPERATING` |
| `ASSET_SALE` / `ASSET_PURCHASE` | in / out | `INVESTING`: Equipment and investments / Capital expenditures | `INVESTING` | `INVESTING` |
| `LOAN_DISBURSEMENT`, `OWNER_CAPITAL` | in | `FINANCING`: Loans and owner | `FINANCING` | `FINANCING` |
| `LOAN_REPAYMENT` (principal), `OWNER_DRAWING` | out | `FINANCING`: Loans and owner | `FINANCING` | `FINANCING` |
| `INTERNAL_TRANSFER`, `REVERSAL` | either | `NONE`: not a cash flow | `NON_CASH` | `NON_CASH` |
| `UNKNOWN` | either | `NONE` until categorized | `UNCLASSIFIED` | `UNCLASSIFIED` |

The dashboard splits `OPERATING_EXPENSES` further by category (payroll, rent and utilities, repairs and
services, other), so the money flow shows the same rows a person expects in a statement. Statement
lines are cash-basis groupings of bank lines, not an accrual income statement; the UI says so.

Goods or services: a debit matched to a purchase invoice is `INVENTORY_PURCHASE` when the invoice
reader marks it `supplyKind = GOODS` (beans, packaging, stock) and `SUPPLIER_PAYMENT` when
`SERVICES` (maintenance, delivery, consulting); `MIXED` follows the larger share. Either way it is a
`CATEGORY` label a person can correct, and that correction is the kind of example the categorizer
learns from first.

IFRS 18's classification applies to periods from 1 Jan 2027; for earlier periods IAS 7 allows a policy
choice, and Kredibel applies the IFRS 18 one for comparability and says so under the cash-flow table.
⚠️ An accountant confirms these mappings before any real-data pilot.

**Risk tags:** `GAMBLING`, `CRYPTO`, `P2P_LENDING`, `CASH_DEPOSIT`, `CASH_WITHDRAWAL`, `RETURNED_ITEM`,
`ROUND_TRIP`.

**Order of precedence:** (1) a person's decision on the line's `CATEGORY` label (`categorizedBy =
USER`, never overwritten); (2) a match decides it (a credit matched to a sales invoice is
`SALES_RECEIPT`, a debit matched to a purchase invoice is `INVENTORY_PURCHASE` or `SUPPLIER_PAYMENT`
by its `supplyKind`, a debit matched to a
ledger entry takes that entry's account mapping); (3) internal transfer between the workspace's own
accounts; (4) a **workspace rule** a person created with "Apply to similar lines" (P1,
[`09`](09-data-model.md) §3.20); (5) related party (P1); (6) keyword rules in
`contracts/policy/categorization-rules.v1.yaml`, first match wins; (7) Gemini (`txn_categorizer`,
batches of 100, with up to 5 verified examples from the same workspace in the prompt, P1) for the rest;
confidence < 0.5 → `UNKNOWN`. Every outcome is written as a `CATEGORY` label with its source and
confidence, so a person can check it on the Labels page. The same call returns a cleaned
counterparty name and kind for rows the rules cannot parse.

### 4.2 Counterparties

`build_counterparties` (pure) groups bank lines, invoices and receipts by normalized party name
(`token_set_ratio ≥ 90` merges spellings) and assigns roles in code:

| Role | Rule |
|---|---|
| `CLIENT` | Buyer on ≥ 1 sales invoice, or counterparty of a `SALES_RECEIPT` |
| `SUPPLIER` | Issuer of ≥ 1 purchase invoice or receipt, or counterparty of a `SUPPLIER_PAYMENT` |
| `LENDER` | Counterparty of `LOAN_REPAYMENT` or `LOAN_DISBURSEMENT` |
| `OWNER` | Counterparty of `OWNER_DRAWING` or `OWNER_CAPITAL` (feeds the "Owner" nodes of the money flow) |
| `OWN_ACCOUNT` | One of the workspace's names or accounts (`INTERNAL_TRANSFER`) |
| `RELATED_PARTY` | A declared or accepted related person (P1) |
| `GOVERNMENT` | Counterparty of `TAX_PAYMENT` |
| `OTHER` | Anyone else |

Unnamed rows (e.g. `VAT PAYMENT MAR`) go to named buckets ("VAT payments", "Bank fees") so totals stay
complete. Each counterparty keeps totals per month, first and last date, **the bank accounts seen for
it** (masked, with a hash in `orgPrivate`; this feeds `X08`) and sample evidence.

### 4.3 Profile suggestions

`build_profile_suggestions` (pure) proposes profile changes; nothing changes until the user accepts.

| Suggestion | Source | Confidence | P |
|---|---|---|---|
| `BANK_ACCOUNT` | Statement header (bank, holder, account) not among the workspace's accounts | `HIGH` if agreed, else `MEDIUM` | P0 |
| `TAX_ID` | Issuer tax ID on the workspace's sales invoices (most frequent), when the profile has none | `HIGH` if agreed on ≥ 2 invoices | P0 |
| `ADDRESS` | Statement holder address or invoice issuer address, when the profile has none | `MEDIUM` | P0 |
| `ALIAS` | A holder or issuer spelling of the workspace's name (`token_set_ratio ≥ 90`) | `MEDIUM` | P1 |
| `RELATED_PARTY` | A person receiving `OWNER_DRAWING` debits in ≥ 3 months | `LOW` | P1 |

A suggestion that contradicts a single-valued field is stored as `CONFLICT` with the current value.
A rejected value is never suggested again (deterministic suggestion ID).

---

## 5. Month figures and money flows

All `Decimal`. A month's figures use bank lines of the workspace's accounts dated in that month,
excluding `NON_CASH` and lines of held (possible duplicate), failed or quarantined statements and of
documents whose printed currency was not accepted (ADR-025). Each eligible line counts once in bank
cash whether or not a document supports it; a person's payment confirmation never adds bank cash.

| Fact (`fact:<yyyy-mm>:<name>`) | Formula |
|---|---|
| `money_in`, `money_out` | Σ credits, Σ debits |
| `net` | `money_in − money_out` |
| `operating_in`, `operating_out` | by class `OPERATING` |
| `opening`, `closing` | per account from statements; Σ over accounts |
| `negative_days` | days with end-of-day balance < 0 |
| `bank_lines`, `auto_matched`, `manually_matched`, `proposed`, `unmatched`, `excluded` | counts of bank lines by match state; `unmatched` lines are **Bank recorded · No supporting document**, still in cash; `excluded` are `NON_CASH` |
| `auto_match_rate` | `auto_matched / (bank_lines − excluded)`, four decimals |
| `uncategorized` | lines still `UNKNOWN` |
| `category:<id>`, `line:<statement line>` | signed totals per category and per statement line (feeds §5.1) |
| `invoiced_sales`, `invoiced_purchases`, `receipts_total` | Σ document totals dated in the month |
| `ledger_cash_movement` | Σ ledger entries on mapped bank accounts |
| `open_review_items` | count |

Aggregates for a period (quarter, year, all) sum or recompute from months. Every figure is a **fact**
with an ID, a decimal-string value and its inputs; explanations and the assistant cite facts.

### 5.1 Money flow

`build_money_flow(period, view, framework)` (pure) returns `{nodes, links}`. Two views; the dashboard
opens on `STATEMENT`, and the framework defaults to the workspace's `profile.accountingFramework`:

**`STATEMENT` (default):** four columns, so the flow reads like a cash-flow statement.

| Column | Nodes | Rule |
|---|---|---|
| Revenue and other money in | Top 5 clients by inflow, "Other clients", "Cash sales deposited", then one node per other inflow line (other income, loans and owner, equipment sold), and "Taken from balance" when the period's net is negative | Credits by counterparty (for `REVENUE`) or by statement line |
| Accounts | One node per bank account (masked label) | Credits into, debits out of each account |
| Activity | Operating, Investing, Financing (classes under the chosen framework), and "Kept" when net is positive | Debits grouped by class |
| Statement line | Cost of sales, Payroll, Rent and utilities, Repairs and services, Other operating expenses, Taxes paid, Finance costs, Equipment and investments, Loan principal repaid, Owner drawings (framework wording) | Debits grouped by statement line, operating expenses split by category |

**`COUNTERPARTIES`:** three columns, clients and other sources → accounts → "Suppliers", "Payroll",
"Rent and utilities", "Tax", "Loan payments", "Owner drawings", "Other spending" and "Kept in the
account". Same totals, grouped by who was paid instead of by statement line.

Links carry `amountMinor` and the query that lists their bank lines. Σ in = Σ out + kept for each
account, in both views. Internal transfers between own accounts are drawn as account-to-account links
only when the user chooses "show transfers" (off by default). Switching the framework moves interest
(and dividends, when present) between activities; nothing else changes, and the totals never do.

The same data gives the dashboard's **Bars** (statement lines grouped by activity) and **Table** views,
so a person who cannot read a Sankey sees the same numbers.

### 5.2 Cash-flow series and statement

`build_cash_flow(period, framework)` (pure) returns what the dashboard's two other charts need:

| Part | Content |
|---|---|
| `months[]` | Per month: `in`, `out`, `net`, closing balance (Σ over accounts) |
| `byActivity` | Opening balance, net operating, net investing, net financing, closing balance (a waterfall) |
| `byLine[]` | Per statement line: class under the framework, amount |
| `framework`, `note` | The framework used and the sentence shown under the chart (for example, where interest paid went) |

`opening + Σ byActivity = closing` is checked in code; a gap means a statement is missing or a month
is incomplete, and the chart says so instead of drawing a balance that does not exist.

---

## 6. Reconciliation

Policy: `contracts/policy/reconciliation.v1.yaml` (tolerances, windows, weights, thresholds).

Bank statements anchor bank cash; document support is a separate dimension (ADR-025). An eligible
bank row without support is **Bank recorded · No supporting document**, included once in cash
totals. This is neither an authenticity guarantee nor an unsupported-expense accusation. Preserve
integrity warnings. Documents without account/date coverage for their payment window wait for the
statement, even if some other statement exists in that calendar month.

Document approval and payment confirmation without bank evidence are separate audited inputs.
Neither creates a bank row. Payment confirmation records amount, currency, date, method and reason;
partial confirmation stays partial. Later bank evidence links the same payment without counting it
twice. T007-06a owns the versioned contract before these decisions can be persisted.

**Payment evidence** of an invoice or receipt is derived each run (`domain/evidence.py`), first
match wins: `CURRENCY_TO_CONFIRM` (printed currency differs or is unknown and no agreement yet),
`PAID_BANK` (confirmed matches cover the total within tolerance; a grouped payment pays each invoice
its own total; a confirmed net-of-tax adjustment counts as full), `PARTIAL_BANK`, `PROPOSED`,
`CONFIRMED_BY_YOU` (a person's confirmation, shown apart, never bank cash), `PAID_CASH` (cash
receipts), `WAITING_FOR_STATEMENT`, `NO_BANK_MATCH` (receipts), `NOT_DUE`, `UNPAID`. **Coverage**:
every account that has statements covers every day from the issue date to the earlier of the
payment window's end (`due + graceDays`, or `+ receiptDays`) and the evaluation date; payments before
the issue date are not required to be covered. **Bank support** of a line: `EXCLUDED` (non-cash),
`MATCHED`, `PROPOSED`, `NOT_REQUIRED` (a person said so, with a reason) or `NO_SUPPORT`
(informational: "Bank recorded · No supporting document").

### 6.1 Order independence

`reconcile_month(month, data)` is a pure function of **all** current data for the month and its
neighbours (a ±1 month window for cross-month payments), not of the order it arrived in. The month
workflow re-runs it whenever the month is marked dirty (a document read, a value corrected, a
duplicate decided, a manual match made). User decisions (manual matches, rejections, duplicate
decisions, ignored items) are **inputs** and are never undone by a re-run. Same inputs, same
output: uploading S1 in reverse order (scenario S5) ends in the same matches.

### 6.2 What is matched

| Pair | Left | Right | Notes |
|---|---|---|---|
| Sales | Bank credit | Sales invoice(s) | exact, net of withholding tax, split (2–3 credits), several invoices in one credit |
| Purchases | Bank debit | Purchase invoice(s) or receipt | receipts paid by card or transfer only |
| Ledger cash | Bank line | Ledger entry on a mapped bank account | same date ±3 days and same amount |
| Ledger documents | Invoice or receipt | Ledger entry (receivable, payable or expense) | invoice number in the reference, or party + amount + date |

A bank line is matched when its amount is fully explained by documents or ledger entries; a document
is paid when its total is fully covered by bank lines (net-of-tax counts as fully covered).

### 6.3 Scoring and assignment

Candidate eligibility requires amounts accepted in the fixed workspace currency, valid positive document totals, matching
cash direction and no held inputs. Bank-to-ledger candidates additionally require the same confirmed
bank-account mapping. Cash or unknown-method receipts cannot automatically be treated as bank
debits. Different or missing printed currency requires an explicit audited agreement to treat the
unchanged numbers as the workspace currency; no FX conversion. Without agreement, no candidate or
contribution to totals. Missing required amount/date means no candidate; conflicting readings permit a
proposal but never automation. Document-to-ledger links establish a booking, not proof of payment.

For each left item, candidates within the window (`[issue − 3 days, due + graceDays]` for invoices,
`±3 days` for receipts and ledger entries) are scored:

- `amount_score` = 1.0 if within tol (max(currency floor, 0.5%)); 0.8 for a possible withholding
  shortfall on a bank-to-invoice pair (`T·(1 − maxWithholding) ≤ c < T`); else no candidate.
  Floors are policy values in major units: IDR 1,000; MYR/SGD/USD 0.01; JPY 1. Always
  use the **workspace** currency, never the printed foreign currency. Unsupported workspace
  currencies have no fallback. Net-of-tax candidates require review until an explicit adjustment is confirmed;
  amount proximity alone does not establish a tax treatment. Receipts and ledger amounts do not
  receive this withholding exception.
- `party_score` = `token_set_ratio(party, counterparty or description) / 100`, both upper-cased with
  accents and punctuation removed (`Daybreak Café` = `DAYBREAK CAFE`).
- `reference_score` = 1.0 if the whole invoice number or ledger reference appears in the description,
  case/punctuation normalized, else 0 (`INV-12` must not match `INV-123`).
- `date_score` = `1 − min(1, distance / window)`. For invoices the distance is the days **after the
  due date** (0 for a payment from `issue − 3 days` to the due date) and the window is `graceDays`; for
  receipts and ledger entries it is the days between the two dates and the window is `receiptDays` or
  `ledgerDays`.
- `score = 0.45·amount + 0.25·party + 0.15·reference + 0.15·date`.

Missing due dates use `defaultTermsDays`. Document-to-ledger uses `ledgerDays` around the issue/receipt
date. Every scorer returns the four contributions, signed cash direction eligibility, reason codes
and whether human review is required, without assigning a match. Amount + date alone scores 0.60:
it may be proposed, but cannot auto-confirm. Reason cutoffs and the net-of-tax component score also
live in the policy; code supplies no fallback thresholds.

Assignment is greedy by score, then date, then ID (deterministic); an item is used at most once except
in split or multi-invoice matches (subset sums of up to 3 items within tol, same party ≥ 0.8).
Single, grouped (one bank row, 2–3 invoices of one party) and split (2–3 bank rows, one invoice)
candidates are all scored first and compete; the runner-up for the ambiguity rule is the best other
candidate sharing any record with the best. Groups need the exact total within tolerance and every
part in its date window; they get no net-of-tax allowance. A person's manual matches are placed
first and their records are not offered again; rejected match IDs never return.

| Result | Rule | Status |
|---|---|---|
| **Auto-confirmed** | Best score ≥ `autoConfirmScore` (0.85) **and** the runner-up < best − `ambiguityMargin` (0.10) **and** no conflicting value or unconfirmed adjustment is used | `CONFIRMED`, method `AUTO` |
| **Proposed** | Best score ≥ `proposeScore` (0.60) but not auto-confirmable | `PROPOSED`; becomes a review item with the candidates |
| **None** | Otherwise | Left item stays unmatched |

Every match stores its reason codes (`AMOUNT_EXACT`, `NET_OF_TAX`, `PARTY_MATCH`, `REFERENCE_IN_TEXT`,
`DATE_NEAR`, `SPLIT`, `GROUPED`) shown as plain text in the UI ("Same amount, same client, invoice number in the
transfer description").

---

## 7. Review items

Created and closed by `reconcile_month` and the document workflow; never by a model.

| Kind | Created when | Resolutions |
|---|---|---|
| `UNMATCHED_BANK_LINE` | A bank line has a specific unresolved evidence/support requirement; missing support alone is informational (ADR-025) | Match manually · categorize and mark "no document needed" · ignore with reason |
| `UNMATCHED_DOCUMENT` | An invoice or receipt is unpaid while statements cover its window, or a ledger cash entry has no bank line | Match manually · mark as not yet paid · ignore with reason |
| `PROPOSED_MATCH` | A match is proposed (§6.3) | Confirm · choose another candidate · reject |
| `POSSIBLE_DUPLICATE` | `D02`, `D03`, `D05`, `D06`, `D07` | Confirm duplicate · not a duplicate |
| `LOW_CONFIDENCE_VALUE` | A value needed for matching or a check is `CONFLICT` or `SINGLE_SOURCE` | Correct the value on the page (both readings shown) · accept as read |
| `LEDGER_DIFFERENCE` | `X09` for a month | Explain (note) · match entries · ignore with reason |
| `CONFIRM_TYPE` | `E03` | Choose the document type |
| `CONFIRM_LEDGER_MAPPING` | A ledger file layout seen for the first time | Confirm or edit the proposed column mapping |

One problem, one item: a bank line that is already the subject of a `LEDGER_DIFFERENCE` or
`POSSIBLE_DUPLICATE` item gets no `UNMATCHED_BANK_LINE` item of its own. A month whose statement is
missing keeps documents as "waiting for the bank statement" rather than creating `UNMATCHED_DOCUMENT`
items. Resolving an item writes an event, marks the month dirty and re-runs `reconcile_month`.

---

## 8. Fraud risk level

Policy: [`contracts/policy/risk.v1.yaml`](../contracts/policy/risk.v1.yaml).

**Document level** from its findings: `CRITICAL` if the verdict is `TAMPERED` or an open `S01`;
`HIGH` if `SUSPICIOUS` or an open HIGH finding; `MEDIUM` if an open MEDIUM finding or `UNVERIFIABLE`;
otherwise `LOW`.

**Month level:** the highest of (a) its documents' levels, (b) its month findings mapped the same way,
and (c) these month rules:

| Rule | Level |
|---|---|
| Any `X08_SUPPLIER_ACCOUNT_CHANGED` open | `HIGH` |
| `D07_DOUBLE_PAYMENT` open | `HIGH` |
| `X09` month difference > 5% | `HIGH` |

Support coverage and auto-match rate are progress measures, not fraud findings by themselves
(ADR-025). Bank-only rows therefore do not raise the month risk solely for lacking an invoice.

A **risk score** 0–100 is stored for sorting only: `min(100, 40·critical + 20·high + 8·medium +
2·low)` over open findings. The level, not the score, is shown.

**Next steps** come from a deterministic catalog keyed by finding code (e.g. `A01` → "Ask the bank
for the original statement or download it again from internet banking"; `X08` → "Confirm the new
account with the supplier using a phone number you already have"; `D07` → "Ask the supplier to refund
the second payment"). The explainer (Gemini) phrases the month summary and orders the steps; it may
only cite findings and facts that exist (grounding guard, [`06`](06-agent-design.md) §5.1).

---

## 9. Determinism and testing

- Every function here is pure: same inputs, same outputs, no clock, no I/O.
- Unit tests cover every threshold (just below, at, above); **hypothesis** property tests cover
  arithmetic (a consistent statement never yields `A01`; one changed balance always does) and
  matching (**any permutation of the inputs gives the same matches**; adding an unrelated document
  never removes a confirmed match).
- Scenario ground truth ([`18`](18-synthetic-data.md)) lists expected findings, duplicates, matches and
  review items; the scenario test asserts exactly those for P0 codes and **zero wrong automatic
  matches**.
