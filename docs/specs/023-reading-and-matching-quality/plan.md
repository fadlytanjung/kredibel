# Plan 023 — Reading and matching quality

## Phase A (P0): matching rules and the Markdown tabs

1. **Markdown tabs.** `shared/ui/MarkdownTabs.tsx` with a pure parser `shared/lib/markdown.ts`
   (headings, paragraphs, pipe tables, bullet lists, horizontal rules, inline code and bold) that
   returns blocks rendered as React elements: no `dangerouslySetInnerHTML`, no new dependency. The
   tab choice is a per-viewer convenience in `localStorage` (wrapped in try/catch). Used by the
   Labels drawer; the mock source (`tools/design/mocks/screens.py` label drawer) gets the same tabs.
2. **Windows.** `receiptDays` and `ledgerDays` 3 → 5 in `reconciliation.v1.yaml` (a policy change,
   versioned in the file; the date score is already linear in the distance).
3. **Fees and withholding.** `feeAllowance` per currency (IDR 10,000; MYR 2; SGD 2; USD 1; JPY 500)
   for money in only; `withholdingRates: ["0.015", "0.02", "0.10"]` as exact rates within tolerance,
   reason `WITHHOLDING_<rate>`; both `requires_review`.
4. **Groups.** Replace the combinations loop with a subset sum in minor units over the candidates
   that pass party (`partyMinScoreForSplit`) and date for the anchor record, capped at
   `maxGroupParts: 8`; groups above `maxAutoGroupParts: 3` are `requires_review`.
5. **Party.** `MatchRecord.aliases`: the counterparty's confirmed aliases; `_party` takes the best of
   description, cleaned name and aliases.

## Phase B (P1): prompts and the model's ranking

6. **Prompts.** `read_statement_page` v4 (procedure, glossary, balance self-check, sign
   conventions), `categorize_transactions` v4 (glossary; cash withdrawals per the product decision),
   `classify_document` v3 (look-alikes). A synthetic *rekening koran* layout in `tools/synthetic`
   (date once per day, dot-matrix font, a tilted photo variant) joins the recorded scenarios, and
   the eval suite (spec 012) measures each version before it ships.
7. **Ranking.** `suggest_match` v2 receives only the candidates code scored, with their reasons, and
   returns an order and one sentence each; stored on the `PROPOSED_MATCH` review item as `aiRanking`;
   the review page shows it as the AI's view.

## Risks

- A wider window or a fee allowance raises false proposals: both are proposals only, and the eval
  suite's E-REC (wrong automatic matches = 0) guards automation.
- A subset sum can find a coincidental group: the same party and the date window are required, and
  more than 3 parts is never automatic.
