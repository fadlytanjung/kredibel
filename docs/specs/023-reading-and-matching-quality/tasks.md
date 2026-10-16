# Tasks 023 — Reading and matching quality

## Phase A — matching rules and the Markdown tabs (P0)

- [x] **T023-01** **TDD** `shared/lib/markdown.ts` parser and `MarkdownTabs` (Preview, Markdown) in the
  Labels drawer and the label mock; per-viewer tab memory; visual baselines. (AC-023-1) Built 16 Oct 2026: `shared/lib/markdown.ts`, `shared/ui/MarkdownTabs.tsx`, `tools/design/mocks/markdown_view.py`; the Labels drawer opens on Preview.
- [x] **T023-02** **TDD** Receipt and ledger windows ±5 days. (AC-023-2) Built 16 Oct 2026: `receiptDays` 5 and `invoiceBeforeIssueDays` 5 (H±5 between bank lines and documents); `ledgerDays` stays 3: ±5 made monthly ledger bookings of the same amount rivals in the synthetic books.
- [x] **T023-03** **TDD** Fee allowance and known withholding rates, proposals only. (AC-023-3) Built 16 Oct 2026: `feeAllowance` per currency (money in, sales), `withholdingRates` above the 2% band (PPh 4(2) 10%); the 2% band stays `NET_OF_TAX`. Contract `MatchReason` gains `WITHHOLDING_RATE`, `FEE_DEDUCTED`.
- [x] **T023-04** **TDD** Grouped matches by subset sum, up to 8 parts, more than 3 never automatic.
  (AC-023-4) Built 16 Oct 2026: `reconcile.subsets_summing` over `part_of` candidates; the backend suite went from about 195 s to 70 s with it.
- [x] **T023-05** **TDD** Party score from description, cleaned name and confirmed aliases. (AC-023-5) Built 16 Oct 2026: `MatchRecord.aliases` from the month's counterparties.

## Phase B — prompts and ranking (P1)

- [ ] **T023-06** Statement reader v4, categorizer v4, classifier v3; synthetic *rekening koran*
  scenario; measured by the eval suite before shipping. (AC-023-6) Partly built 16 Oct 2026: classifier v3 and categorizer v5 shipped; statement v4 (procedure, local words, balance self-check) read the demo the same but lost 14 rows' amounts on a real scan, so it was rolled back with the invoice and receipt self-checks (docs/07 §5a). Open: a statement version that passes both.
- [x] **T023-07** **TDD** The model ranks a proposal's candidates; shown on the review item. (AC-023-7) Built 16 Oct 2026: `Allocation.rivals`, `rank_candidates` prompt v1 and reader call, `month_nodes.rank_proposals`, candidates' `aiRank`/`aiReason` and `rankedBy` (contract, Firestore, schema snapshot), the review panel's AI view and its mock.
- [x] **T023-09** **TDD** Cash withdrawals are money out (`CASH_WITHDRAWAL`); Indonesian and Malay
  words for cash, fees, tax and interest in `categorization-rules.v1.yaml`; `categorize_transactions`
  v4. (AC-023-10)
- [x] **T023-10** **TDD** A value corrected on the Labels page reaches the record and reconciles its
  months; a value corrected anywhere settles its label. (AC-023-8)
- [x] **T023-11** **TDD** Matching tries the other reading of an amount the readings disagreed on
  (`OTHER_READING`, a proposal). (AC-023-9)
- [ ] **T023-08** Update `docs/07`, `docs/08`, `docs/20`.
