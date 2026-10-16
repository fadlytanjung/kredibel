# Spec 023 — Reading and matching quality

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 (phase A), P1 (phase B) |
| **Owner role** | A: Document intelligence, B: Backend, C: Frontend |
| **Depends on** | 005 (reading), 007 (reconciliation), 016 (labels), 022 (extraction store) |
| **Requirements** | FR-005, FR-007, FR-016, NFR-9 (cost) |
| **Design** | [`docs/07`](../../07-document-intelligence.md) §6; [`docs/08`](../../08-risk-engine.md) §6; `contracts/policy/reconciliation.v1.yaml`; mocks `label.html`, `labels.html` |

## Summary

On 16 Oct 2026 a tester read a real scanned Indonesian statement (*rekening koran*) and the books
"counted wrong": same-day rows were dropped, so balances, totals and findings were off. That was
fixed the same day (spec 005 T005-14, 006 T006-12, 022 T022-05). This spec takes the lessons
further, in three places: the **prompts**, which are short rule lists without a procedure, a
glossary of local banking words or a self-check; the **reconciliation**, which is deterministic and
should stay so, but misses common real cases (card settlements a few days late, a transfer fee
taken from a payment, several receipts paid in one card charge); and the **page Markdown** a person
checks a value against, shown only as raw text.

Numbers, matches and risk stay with code (constitution P1, P5). A model may read, name a
counterparty and rank the candidates code found, never confirm a match or compute an amount.

## Analysis

### Prompts (`backend/app/agents/prompts/*.md`)

What works: every reader treats the document as data, returns values exactly as printed, cites
the chunks it read, and says where the image differs from the text. Code grounds every value.

What is missing:

| Gap | Effect | Where |
|---|---|---|
| No **procedure**: the rules say what to return, not how to work through a page (find the columns, the sign convention, each row, then check) | Layout variants are left to luck: one amount column with `-` or `DB/CR`, columns in another order, rows without a date | `read_statement_page` |
| No **self-check** before answering | A missed row is invisible to the model although the printed running balance proves it: if a balance does not follow from the previous one plus the amount, a row is missing between them | `read_statement_page` |
| No **glossary** of local banking words | `TRK TUNAI` (cash withdrawal), `SETORAN` (deposit), `BIAYA ADM` (fee), `JASA GIRO` (interest), `PPH`/`PAJAK` (tax), `SP2D` (government disbursement), `DB`/`CR`, `Mutasi`, `Saldo` are read or categorized by guess | `read_statement_page`, `categorize_transactions`, `classify_document` |
| No **edge-case rules** for documents that look alike | A proforma, a quotation, a delivery note or a *Faktur Pajak* can be taken for an invoice; an internet-banking *mutasi rekening* printout for something other than a statement | `classify_document` |
| No **calibration** for confidence | Confidences cluster high; the label thresholds of `learning.v1.yaml` lose meaning | all |
| Few **examples** | Only the workspace's verified examples (spec 016), none built in for a first upload | all |

Chain-of-thought text is not the answer: the readers already run with Gemini's own thinking
(`READER_THINKING_LEVEL`), and long reasoning in the output costs tokens and is not grounded. What
helps is a short **procedure**, a **check list** the model runs before answering, a **glossary**,
and a few **built-in examples** of hard layouts, all measured by evals before a version ships.

### Reconciliation (`domain/reconcile*.py`, `reconciliation.v1.yaml`)

What exists: exact and tolerant amounts (the larger of a currency minimum and 0.5%), payments up
to 3 days before an invoice and up to 30 days after its due date, receipts and ledger entries
within 3 days, net of up to 2% withholding (a proposal), one bank row for 2 to 3 documents of the
same party (GROUPED) and several rows for one document (SPLIT), scored on amount, party,
reference and date, automatic only when unique and high.

| Case | Today | Needed |
|---|---|---|
| Card or QR payment settled on the statement H+1 to H+5 (weekends, holidays) | Receipts match within ±3 days only | ±5 days for receipts and ledger entries, scored down with distance |
| A transfer fee taken from the payment (an incoming transfer short by a fixed fee) | Unmatched unless the fee is under the tolerance (IDR 1,000 or 0.5%) | A named allowance per currency (`FEE_DEDUCTED`), a proposal a person confirms |
| A withholding tax at a known rate (PPh 23 2%, PPh 22 1.5%, PPh 4(2) 10%) | Anything up to 2% below is a proposal | Exact known rates as stronger evidence; the 2% band kept |
| Several receipts in one card charge (an Apple or Google subscription batch, a marketplace order) | At most 3 parts, every combination tried | A subset sum over the same party's documents in the window, up to 8 parts; more than 3 parts always a proposal |
| The bank says `TRF M-BKG JAYA TKN`, the invoice says `PT Jaya Teknik Mandiri` | Fuzzy party score on the printed text | Also the counterparty name the categorizer cleaned, and the aliases people confirmed on earlier matches |
| Two candidates within 0.10 of each other | A proposal with alternatives, no help choosing | The model ranks the candidates code found, with a short reason a person reads; it never confirms |

### Page Markdown

The Labels drawer shows a page's Markdown as raw text. People read tables and headings more easily
rendered, and check the raw text when a value looks wrong: two tabs, **Preview** and **Markdown**,
as on GitHub and Azure DevOps.

## Acceptance criteria

- **AC-023-1** The page Markdown shows in two tabs, Preview (rendered: headings, pipe tables, lists,
  rules) and Markdown (as stored); the choice is kept per viewer; rendering builds elements, never
  HTML from the text (documents are adversarial).
- **AC-023-2** Receipts match a bank line up to 5 days apart and an invoice may be paid up to 5 days
  before its issue date (policy), scored down with the distance; ledger cash keeps ±3 days, where a
  wider window makes monthly bookings of the same amount rivals.
- **AC-023-3** An incoming payment short by no more than the currency's fee allowance is a proposal
  with the reason `FEE_DEDUCTED`, never automatic; a payment at a known withholding rate within
  tolerance carries `WITHHOLDING_<rate>`.
- **AC-023-4** One bank line can settle up to 8 documents of one party in its window when their sum
  agrees within tolerance (subset sum); a group of more than 3 parts is always a proposal.
- **AC-023-5** The party score uses the best of the printed description, the cleaned counterparty
  name and the counterparty's confirmed aliases.
- **AC-023-6** The statement reader follows a written procedure with a balance self-check and a
  glossary; the categorizer and classifier get the glossary and edge-case rules; each new prompt
  version is measured by the eval suite (spec 012) before it ships.
- **AC-023-7** For an ambiguous proposal, the model ranks the candidates code found and says why in
  one sentence; the ranking orders the review item's choices and is shown as the AI's view; a
  person still decides.
- **AC-023-8** A value a person corrects on the Labels page changes the line, invoice or receipt and
  reconciles its months, as a correction in the review queue does, with the same validation; a value
  a person corrected anywhere is their decision on its label, which stops asking.
- **AC-023-9** When the two readings disagree on an amount and no person settled it, matching also
  tries the other reading; a match only the other reading explains is a proposal (`OTHER_READING`)
  that says which value to correct.
- **AC-023-10** A cash withdrawal (`TRK TUNAI`, `TARIKAN TUNAI`, `ATM WITHDRAWAL`…) is money out
  (`CASH_WITHDRAWAL`, operating; other spending in the profit and loss), never a transfer between
  own accounts (product decision 16 Oct 2026); Indonesian and Malay words for cash, fees, tax and
  interest are in the categorization rules.

## Out of scope

FX conversion, bank feeds, a model deciding a match, many-to-many groups.
