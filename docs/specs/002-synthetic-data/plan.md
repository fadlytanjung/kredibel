# Plan 002 — Synthetic Data Generator

## Approach

A separate `uv` project under `tools/synthetic/` (package `kredibel_synth`) so the backend image does
not carry `reportlab`. Pure generation functions produce **data first** (rows, invoices), then
renderers turn data into PDFs, then tamperers modify PDFs. `truth.json` is written from the data plus
the tamper log, never re-derived from PDFs.

## Modules

| File | Responsibility |
|---|---|
| `tools/synthetic/pyproject.toml` | deps: reportlab, pypdf (≥ 5 for `incremental=True`), pikepdf, click; dev: pytest; script `kredibel-synth` |
| `kredibel_synth/world.py` | fictional entities, constants ([`docs/18`](../../18-synthetic-data.md) §2) |
| `kredibel_synth/rng.py` | seeded `random.Random`; deterministic dates/amounts; **no** wall-clock |
| `kredibel_synth/model.py` | dataclasses `StatementData`, `Row`, `InvoiceData`, `Line`, `TamperRecord` (Decimal money) |
| `kredibel_synth/transactions.py` | monthly flow generator (§3.3) with economics tuned per scenario profile |
| `kredibel_synth/invoices.py` | invoice generation + payment scheduling into statement rows (exact, net-of-tax, split, not-due) |
| `kredibel_synth/render_statement.py` | reportlab; embedded DejaVu Sans; pagination; watermark; fixed metadata; `invariant=1` for deterministic output |
| `kredibel_synth/render_invoice.py` | reportlab invoice |
| `kredibel_synth/tamper.py` | T1 (pypdf incremental: remove the text op, append Helvetica overlay content stream, update metadata), T3 (data-level), T2/T4/T5/T6 (P1) |
| `kredibel_synth/scenarios.py` | S1…S6 builders composing the above |
| `kredibel_synth/truth.py` | writes `truth.json` |
| `kredibel_synth/cli.py` | `generate --scenario/--all --seed/--seeds --out` |
| `tools/synthetic/tests/` | invariants of [`docs/18`](../../18-synthetic-data.md) §7 |

## Determinism notes

- reportlab: `canvas.Canvas(..., invariant=1)` and fixed `setCreator/setProducer`; set creation date
  explicitly.
- pypdf incremental write: set `/ModDate` and `/Producer` explicitly; avoid random IDs (fix the
  trailer `/ID` from a hash of scenario+seed).
- Fonts: bundle DejaVu Sans TTF in `tools/synthetic/fonts/` (permissive licence).

## T1 technique detail

1. Locate the target row's credit text operation on its page (the renderer records, per row, the page,
   the text string and its coordinates in a sidecar map, so the tamperer doesn't need to parse).
2. With pypdf `PdfWriter(clone_from=original, incremental=True)`: rewrite that page's content stream
   without the target `Tj` (the renderer emits each amount as its own text object to make this
   simple), add `/Helv` to the page font resources, append a content stream drawing `7,250,000.00` at the
   recorded coordinates, update `/ModDate` and `/Producer`, write.
3. Verify: 2 `%%EOF` markers; pdfplumber reads the new value in Helvetica at the row's position, and
   the old string is gone.

## Constitution check

P8 ✔ (fictional, watermarked) · P3 ✔ (truth enables evidence checks) · P10 ✔ (ground truth for tests/evals)
