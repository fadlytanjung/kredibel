# Spec 002 — Synthetic Data Generator

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 (S1–S5, T1, T7–T13, scan and photo variants, fixtures) · P1 (S6, T4) |
| **Owner role** | B: Risk engine |
| **Depends on** | 001 (repo layout only) |
| **Requirements** | P0-16, NFR-04, NFR-05, SD-1…SD-9 ([`docs/18`](../../18-synthetic-data.md) §1), constitution P8 |

## Summary

A deterministic generator of realistic, clearly marked synthetic books for one business (Sunrise
Coffee Roasters, Jan–Jun 2026): bank statements, sales and purchase invoices, receipts and a ledger
export, with tampered and duplicated variants, an upload order and a `truth.json` per scenario.
Every test, eval and demo depends on it.

## User stories

### US-002-1: Generate a scenario (developer)

- **AC-002-1** `kredibel-synth generate --scenario S1 --seed 1 --out <dir>` writes to
  `<dir>/S1/seed-1/`: 6 statement PDFs, 24 sales and 16 purchase invoice PDFs, 24 receipts (JPEG and
  PDF), `ledger-2026-H1.csv`, `truth.json`, `upload-order.txt` and `README.md`.
- **AC-002-2** Running the same command twice produces byte-identical files (same SHA-256).
- **AC-002-3** Every page and image shows the diagonal watermark and the footer "SYNTHETIC — FOR
  TESTING"; the ledger file's first row is a comment with the same text.

### US-002-2: Realistic books

- **AC-002-4** Statements follow [`docs/18`](../../18-synthetic-data.md) §3.1: English format
  (`1,250,000.00`), 2–3 pages; every row satisfies `balance[i-1] + credit − debit = balance[i]`; each
  month's opening equals the previous closing; `Producer` `ACB CoreBanking ReportEngine 4.2`, single
  revision.
- **AC-002-5** Invoices and receipts satisfy line, subtotal, VAT and total arithmetic; suppliers have
  their own layouts and a pay-to account; receipts carry a payment method.
- **AC-002-6** Every bank line has exactly one ledger cash entry on account `1110` (same amount, date
  ± 0–2 days) except those `truth.json` marks as missing; invoices and receipts post to the accounts of
  [`docs/18`](../../18-synthetic-data.md) §3.5.
- **AC-002-7** The matching cases of [`docs/18`](../../18-synthetic-data.md) §3.6 exist (net of 2%
  withholding, split payment, one transfer for two invoices, an ambiguous pair, a deposit missing from
  the ledger, a not-yet-due invoice) and are recorded in `truth.json.matches`.

### US-002-3: Tampering and duplicates

- **AC-002-8** S2 (T1 on March): exactly 2 revisions; the edited credit shows `7,250,000.00` in
  Helvetica; balances unchanged; `ModDate` = creation + 3 days; `Producer` = `PDF Editor 11`.
- **AC-002-9** S3: T7 (exact copy, same SHA-256), T8 (re-exported February statement: identical rows,
  different SHA-256), T9 (a purchase invoice re-scanned), T10 (a receipt re-photographed, perceptual
  hash distance ≤ 8, different SHA-256), T11 (one ledger row duplicated).
- **AC-002-10** S4: T12 (Roastline Equipment Service's May invoice and payment to a new Meridian
  Savings Bank account while earlier ones used ACB) and T13 (two Bluewater Trading Co. invoices with no
  bank or ledger history).
- **AC-002-11** S5 contains S1's files and an `upload-order.txt` in reverse order (statements first).

### US-002-4: Ground truth

- **AC-002-12** `truth.json` follows [`docs/18`](../../18-synthetic-data.md) §6: the workspace as
  onboarded (no tax ID, no address), the upload order, every value with a stable `key`, tampering and
  duplicates, intended matches (`AUTO` or `PROPOSED`), and expected outcomes per document and per
  month, plus `expectedSuggestions`, `expectedCounterparties` and `expectedFlows`.
- **AC-002-13** The generator's own tests ([`docs/18`](../../18-synthetic-data.md) §7) pass for S1–S5
  and seeds 1–5, including: every `AUTO` match is unambiguous under `reconciliation.v1.yaml` and every
  `PROPOSED` one is ambiguous by construction.

### US-002-5: Variants and fixtures

- **AC-002-14** `--scan` writes image-only PDFs (200 dpi, mild noise, 0.4° skew) with the same truth.
- **AC-002-15** The fixtures of [`docs/18`](../../18-synthetic-data.md) §3.7 exist, each with its own
  `truth.json`: undeclared account, holder mismatch, regenerated statement, double payment, white-out
  overlay, cid glyphs, gambling and returns, ledger XLSX.

### US-002-6: Hidden instructions (P1)

- **AC-002-16** S6: S1 + T4 (1-pt white footer text in one purchase invoice) with expectations for
  Model Armor on and off.

## Out of scope

Other banks' layouts, multi-currency, handwritten documents, tax e-invoice QR codes.
