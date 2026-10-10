# Spec 002 — Synthetic Data Generator

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 (S1–S3, T1, T3) · P1 (S4–S6, T2, T4–T6) |
| **Owner role** | B: Risk engine |
| **Depends on** | 001 (repo layout only) |
| **Requirements** | P0-16, SD-1…SD-6 ([`docs/18`](../../18-synthetic-data.md) §1), constitution P8 |

## Summary

A deterministic generator of realistic, clearly-marked synthetic bank statements and invoices, with
tampered variants and a `truth.json` per scenario. Every test, eval and demo depends on it.

## User stories

### US-002-1: Generate a scenario (developer)

- **AC-002-1** `kredibel-synth generate --scenario S1 --seed 1 --out <dir>` writes 6 monthly statement
  PDFs (Jan–Jun 2026), 10 sales-invoice PDFs, `truth.json` and `README.md` to `<dir>/S1/seed-1/`.
- **AC-002-2** Running the same command twice produces byte-identical files (same SHA-256).
- **AC-002-3** Every page shows the diagonal watermark and the footer "SYNTHETIC — FOR TESTING".

### US-002-2: Realistic statements

- **AC-002-4** Each statement has the header, columns and summary of [`docs/18`](../../18-synthetic-data.md) §3.1;
  amounts use English format (`1,250,000.00`); everything on the page is in English; statements
  span 2–3 pages.
- **AC-002-5** In untampered statements, every row satisfies `balance[i-1] + credit − debit = balance[i]`,
  and each month's opening equals the previous month's closing.
- **AC-002-6** PDF metadata: `Producer` = `ACB CoreBanking ReportEngine 4.2`, `Creator` = `ACB e-Statement`,
  creation date = period end + 1 day 02:00 (UTC+7), single revision.

### US-002-3: Realistic invoices

- **AC-002-7** Invoices satisfy line, subtotal, VAT 11% and total arithmetic; each S1 invoice is paid by
  a matching credit in the statements; one is paid net of 2% withholding, one in two transfers, one is
  not yet due.

### US-002-4: Tampering (P0: T1, T3)

- **AC-002-8** T1 on the March statement of S2: exactly 2 revisions; the edited credit displays
  `7,250,000.00` drawn in Helvetica; balances unchanged; `ModDate` = creation + 3 days; `Producer` =
  `PDF Editor 11`.
- **AC-002-9** S3 contains 5 genuine and 5 T3 invoices; T3 invoices have no matching credits and their
  total exceeds 1.5 × the operating inflows of the coverage window when combined with genuine ones.

### US-002-5: Ground truth

- **AC-002-10** `truth.json` follows [`docs/18`](../../18-synthetic-data.md) §6 and lists expected
  P0 findings per document and per case, verdicts, hard stops and recommendation for S1–S3.

### US-002-6: P1 scenarios

- **AC-002-11** S4 (T5), S5 (T2), S6 (T4) generated with truth as in [`docs/18`](../../18-synthetic-data.md) §5.

### US-002-7: Applicant profiles and scanned variants

- **AC-002-12** `truth.json` contains the `applicant` as onboarded in the scenario (type, names, declared
  accounts, related parties), `expectedSuggestions` and `expectedCounterparties` per
  [`docs/18`](../../18-synthetic-data.md) §6; S1–S3 use a company applicant, S4 an individual applicant.
- **AC-002-13** `--scan` writes a scanned variant of a scenario: every page rasterized at 200 dpi with
  mild noise and a 0.4° skew, saved as an image-only PDF (no text layer), same truth.
- **AC-002-14** Fixtures: a statement from an undeclared second account (for `X06`), a T6 statement held
  by "Sunrise Trading Partners" (for `X05`), and a white-out + overlay cell (text layer ≠ visible value,
  for the verifier).
- **AC-002-15** (P1) S7: owner transfers from the declared beneficial owner labelled as sales
  (`TRANSFER IN ANDI PRATAMA`), for the related-party rule and `B07`.

## Out of scope

Receipts, tax invoices, other banks' layouts, handwritten documents.
