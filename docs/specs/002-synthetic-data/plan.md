# Plan 002 — Synthetic Data Generator

## Approach

A separate `uv` project under `tools/synthetic/` (package `kredibel_synth`) so the backend image does
not carry `reportlab`. Pure generation functions produce **data first** (bank lines, invoices,
receipts, ledger rows, intended matches), then renderers turn data into files, then tamperers and
duplicators modify files. `truth.json` is written from the data plus the tamper log, never re-derived
from files.

## Modules

| File | Responsibility |
|---|---|
| `tools/synthetic/pyproject.toml` | deps: reportlab, pypdf (≥ 5 for `incremental=True`), pikepdf, Pillow, imagehash, openpyxl, click; dev: pytest, hypothesis; script `kredibel-synth` |
| `kredibel_synth/world.py` | fictional entities and constants ([`docs/18`](../../18-synthetic-data.md) §2) |
| `kredibel_synth/rng.py` | seeded `random.Random`; deterministic dates and amounts; **no** wall clock |
| `kredibel_synth/model.py` | dataclasses `StatementData`, `BankRow`, `InvoiceData`, `ReceiptData`, `LedgerRow`, `IntendedMatch`, `TamperRecord` (Decimal money) |
| `kredibel_synth/books.py` | monthly flow generator (§3.6) producing bank rows, documents and ledger rows together, so they agree by construction |
| `kredibel_synth/matching_cases.py` | inserts the special cases (net of tax, split, two-in-one, ambiguous pair, missing ledger row, not due) and checks ambiguity against `contracts/policy/reconciliation.v1.yaml` |
| `kredibel_synth/render_statement.py` | reportlab; embedded DejaVu Sans; pagination; watermark; fixed metadata; `invariant=1`; sidecar coordinate map per amount |
| `kredibel_synth/render_invoice.py` | sales layout and three supplier layouts |
| `kredibel_synth/render_receipt.py` | till-roll layout; JPEG "photo" (rotation, perspective, noise) or clean PDF |
| `kredibel_synth/render_ledger.py` | CSV (and the XLSX variant with a signed amount column) |
| `kredibel_synth/tamper.py` | T1 (pypdf incremental), T4 (P1), T7–T13 |
| `kredibel_synth/scenarios.py` | S1…S6 builders and fixtures; upload orders |
| `kredibel_synth/truth.py` | writes `truth.json` |
| `kredibel_synth/cli.py` | `generate --scenario/--all --seed/--seeds --scan --out` |
| `tools/synthetic/tests/` | invariants of [`docs/18`](../../18-synthetic-data.md) §7 |

## Determinism notes

- reportlab: `canvas.Canvas(..., invariant=1)` and fixed `setCreator/setProducer`; creation date set
  explicitly.
- pypdf incremental write: set `/ModDate` and `/Producer` explicitly; fix the trailer `/ID` from a hash
  of scenario + seed.
- Images: Pillow with a seeded noise generator; JPEG quality fixed; no EXIF timestamps.
- Fonts: DejaVu Sans TTF bundled in `tools/synthetic/fonts/` (permissive licence).

## T1 technique detail

1. Locate the target row's credit text operation from the renderer's sidecar map (page, string,
   coordinates); each amount is its own text object.
2. With pypdf `PdfWriter(clone_from=original, incremental=True)`: rewrite that page's content stream
   without the target `Tj`, add `/Helv` to the page font resources, append a content stream drawing
   `7,250,000.00` at the recorded coordinates, update `/ModDate` and `/Producer`, write.
3. Verify: 2 `%%EOF` markers; pdfplumber reads the new value in Helvetica at the row's position, and
   the old string is gone.

## Constitution check

P8 ✔ (fictional, watermarked) · P3 ✔ (truth enables evidence checks) · P10 ✔ (ground truth for tests and evals)
