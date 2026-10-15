#!/usr/bin/env python3
"""Prepare a compact, clean 2-month demo package of synthetic documents (May and June 2026).

Creates a folder `demo-pack/` in the project root containing:
- Bank statements for May and June (statement-2026-05.pdf, statement-2026-06.pdf)
- Sales invoices for May and June
- Purchase invoices for May and June
- Receipts for May and June
- Filtered ledger-2026-05-06.csv covering only May and June 2026

Usage:
    uv run python -m scripts.prepare_demo_pack
    uv run python -m scripts.prepare_demo_pack --months 2026-05,2026-06
"""

import argparse
import shutil
from pathlib import Path

DEMO_SOURCE = (
    Path(__file__).resolve().parents[2] / "tools" / "synthetic" / "out" / "demo" / "S1" / "seed-1"
)
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "demo-pack"


def prepare_pack(months: tuple[str, ...], source_dir: Path, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for existing in output_dir.iterdir():
        if existing.is_file():
            existing.unlink()

    copied: list[Path] = []
    # 1. Copy statements, invoices, and receipts matching the months
    for file in sorted(source_dir.iterdir()):
        if file.name.startswith("ledger-") or file.name == "truth.json":
            continue
        if any(m in file.name for m in months):
            dest = output_dir / file.name
            shutil.copy2(file, dest)
            copied.append(dest)

    # 2. Filter ledger to only include the target months
    ledger_source = source_dir / "ledger-2026-H1.csv"
    if ledger_source.exists():
        # Match e.g. /05/2026 or /06/2026
        month_suffixes = tuple(f"/{m.split('-')[1]}/{m.split('-')[0]}" for m in months)
        out_ledger = output_dir / f"ledger-{'_'.join(months)}.csv"
        lines_written = 0
        with (
            ledger_source.open(encoding="utf-8") as src,
            out_ledger.open("w", encoding="utf-8") as dst,
        ):
            for line in src:
                if line.startswith("#") or line.startswith("Date,"):
                    dst.write(line)
                    continue
                # Date is first column, e.g. 01/05/2026
                parts = line.split(",", 1)
                date_str = parts[0].strip()
                if any(date_str.endswith(suffix) for suffix in month_suffixes):
                    dst.write(line)
                    lines_written += 1
        copied.append(out_ledger)

    return copied


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare a 2-month demo pack for video recordings."
    )
    parser.add_argument(
        "--months",
        default="2026-05,2026-06",
        help="Comma-separated months (default: 2026-05,2026-06)",
    )
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR, help="Output folder")
    args = parser.parse_args()

    months = tuple(m.strip() for m in args.months.split(","))
    results = prepare_pack(months, DEMO_SOURCE, args.output)
    print(f"Demo pack created in: {args.output}")
    print(f"Total files: {len(results)}")
    for p in results:
        print(f"  • {p.name}")


if __name__ == "__main__":
    main()
