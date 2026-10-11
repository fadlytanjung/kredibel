# kredibel-synth

Deterministic synthetic books for Kredibel's tests, evals and demo ([`docs/18`](../../docs/18-synthetic-data.md),
spec [002](../../docs/specs/002-synthetic-data/spec.md)). One fictional business, Sunrise Coffee Roasters,
January–June 2026: bank statements, sales and purchase invoices, receipts and a ledger export, with
tampered and duplicated variants and a `truth.json` per scenario. Every page and image is watermarked
**SYNTHETIC — FOR TESTING**; every name, account and tax ID is invented.

## Run

```bash
make synth                                   # S1–S5 × seeds 1–5, S1 scanned, fixtures, demo set (≈ 1 min)
cd tools/synthetic
uv run kredibel-synth generate --scenario S2 --seed 1 --out out
uv run kredibel-synth generate --all --seeds 1-5 --out out
uv run kredibel-synth generate --scenario S1 --seed 1 --scan --out out   # image-only PDFs
uv run kredibel-synth fixtures --out out/fixtures
uv run kredibel-synth demo --out out/demo    # S1–S4, seed 1
uv run pytest -q                             # the generator's own checks (also in `make check`)
```

Output: `out/<scenario>/seed-<n>/` (or `seed-<n>-scan/`) with the documents, `truth.json`,
`upload-order.txt` and a `README.md`. Same scenario and seed, same bytes.

## Scenarios

| ID | Name | What changes from S1 | Kredibel should |
|---|---|---|---|
| S1 | A normal half-year | — (6 statements, 24 sales and 16 purchase invoices, 24 receipts, 1 ledger CSV) | Mark everything clean; one proposed match (Feb); one unmatched deposit and `X09` (Jun, MEDIUM) |
| S2 | The edited statement | T1: March credit of 14 Mar shows 7,250,000.00 in Helvetica, second revision, `PDF Editor 11` | March statement `TAMPERED`, March `CRITICAL`, one ledger difference |
| S3 | Duplicates | T7 Feb statement uploaded twice, T8 Feb re-exported, T9 a GVF invoice scanned, T10 a June receipt photographed again, T11 a May ledger journal keyed twice | Hold four possible duplicates; figures equal S1's |
| S4 | Payment diversion and unpaid bills | T12 Roastline's May invoice paid to a new Meridian Savings Bank account; T13 two Bluewater invoices nobody paid | May `HIGH` (`X08`); two `R02` and two unmatched documents (Apr) |
| S5 | Reverse order | S1's files, statements first and invoices last | End exactly as S1 |

Fixtures (`out/fixtures/`, each with its own `truth.json`): `undeclared-account`, `holder-mismatch`,
`regenerated-statement`, `double-payment`, `whiteout-overlay`, `cid-glyphs`, `gambling-and-returns`,
`ledger-xlsx`.

## How it works

1. `books.py` generates the half-year as data (Decimal money, seeded streams per purpose).
2. `matching_cases.py` scores every intended match with docs/08 §6.3 and
   `contracts/policy/reconciliation.v1.yaml`, so `AUTO` and `PROPOSED` in `truth.json` are proven.
3. `render_*.py` turn data into PDFs, JPEGs, CSV and XLSX (reportlab invariant mode, fixed dates).
4. `tamper.py` and `scenarios.py` apply T1–T13; `truth.py` writes the expectations from the data and
   the tamper log, never from the files.

Fonts: DejaVu (Bitstream Vera licence, `fonts/LICENSE-DejaVu.txt`).
