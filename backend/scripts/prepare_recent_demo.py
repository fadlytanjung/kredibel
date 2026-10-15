#!/usr/bin/env python3
"""Generate a clean 3-month demo pack for August to October 2026 (spec 018 / demo alignment).

Shifts Q2 synthetic books (Apr–Jun) by +4 months to Aug–Oct 2026, rendering fresh:
- ACB Bank Statements (statement-2026-08.pdf, statement-2026-09.pdf, statement-2026-10.pdf)
- Sales and Purchase Invoices for Aug, Sep, Oct 2026
- Receipts (JPEG / PDF) for Aug, Sep, Oct 2026
- Filtered General Ledger CSV (ledger-2026-08_2026-09_2026-10.csv)
- truth.json and upload-order.txt

Usage:
    uv run --project tools/synthetic python backend/scripts/prepare_recent_demo.py \
        --out tools/synthetic/out/demo/S1/seed-recent
"""

import argparse
import calendar
import json
import sys
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

# Add synthetic tools to path
SYNTH_DIR = Path(__file__).resolve().parents[2] / "tools" / "synthetic"
if str(SYNTH_DIR) not in sys.path:
    sys.path.insert(0, str(SYNTH_DIR))

import kredibel_synth.world as world  # noqa: E402
from kredibel_synth.books import generate_books  # noqa: E402
from kredibel_synth.model import (  # noqa: E402
    BankRow,
    Books,
    InvoiceData,
    LedgerRow,
    Line,
    Party,
    PayTo,
    ReceiptData,
    StatementData,
)
from kredibel_synth.render_invoice import render_invoice  # noqa: E402
from kredibel_synth.render_ledger import render_ledger_csv  # noqa: E402
from kredibel_synth.render_receipt import render_receipt_jpeg, render_receipt_pdf  # noqa: E402
from kredibel_synth.render_statement import render_statement, statement_file  # noqa: E402
from kredibel_synth.rng import Rng  # noqa: E402


def _shift_date(d: date, delta_months: int = 4) -> date:
    new_month = d.month + delta_months
    year = d.year
    while new_month > 12:
        new_month -= 12
        year += 1
    max_days = calendar.monthrange(year, new_month)[1]
    new_day = min(d.day, max_days)
    return date(year, new_month, new_day)


def _shift_month_str(m: str, delta_months: int = 4) -> str:
    parts = m.split("-")
    year = int(parts[0])
    mon = int(parts[1]) + delta_months
    while mon > 12:
        mon -= 12
        year += 1
    return f"{year}-{mon:02d}"


def shift_books_to_recent(
    base: Books, source_months: tuple[str, ...], delta_months: int = 4
) -> Books:
    month_map = {m: _shift_month_str(m, delta_months) for m in source_months}

    # 1. Statements
    new_statements: dict[str, StatementData] = {}
    for old_m, new_m in month_map.items():
        if old_m in base.statements:
            st = base.statements[old_m]
            new_rows: list[BankRow] = []
            for r in st.rows:
                new_date = _shift_date(r.date, delta_months)
                new_key = r.key.replace(old_m, new_m)
                inv_refs = [
                    ref.replace(f"/{old_m[5:]}/", f"/{new_m[5:]}/") for ref in r.invoice_refs
                ]
                new_rows.append(
                    replace(
                        r,
                        key=new_key,
                        date=new_date,
                        documents=[d.replace(old_m, new_m) for d in r.documents],
                        invoice_refs=inv_refs,
                    )
                )
            new_statements[new_m] = replace(
                st,
                month=new_m,
                period_start=_shift_date(st.period_start, delta_months),
                period_end=_shift_date(st.period_end, delta_months),
                rows=new_rows,
            )

    # 2. Invoices
    new_invoices: list[InvoiceData] = []
    for inv in base.invoices:
        inv_m = inv.issue_date.strftime("%Y-%m")
        if inv_m in month_map:
            new_m = month_map[inv_m]
            new_invoices.append(
                replace(
                    inv,
                    key=inv.key.replace(inv_m, new_m),
                    number=inv.number.replace(f"/{inv_m[5:]}/", f"/{new_m[5:]}/"),
                    issue_date=_shift_date(inv.issue_date, delta_months),
                    due_date=_shift_date(inv.due_date, delta_months),
                )
            )

    # 3. Receipts
    new_receipts: list[ReceiptData] = []
    for rec in base.receipts:
        rec_m = rec.issued_at.strftime("%Y-%m")
        if rec_m in month_map:
            new_m = month_map[rec_m]
            d = _shift_date(rec.issued_at.date(), delta_months)
            new_issued = rec.issued_at.replace(year=d.year, month=d.month, day=d.day)
            new_receipts.append(
                replace(
                    rec,
                    key=rec.key.replace(rec_m, new_m),
                    issued_at=new_issued,
                )
            )

    # 4. Ledger
    new_ledger: list[LedgerRow] = []
    for row in base.ledger:
        row_m = row.date.strftime("%Y-%m")
        if row_m in month_map:
            new_ledger.append(
                replace(
                    row,
                    date=_shift_date(row.date, delta_months),
                )
            )

    return Books(
        seed=base.seed,
        statements=new_statements,
        sales=[inv for inv in new_invoices if inv.kind == "SALES"],
        purchases=[inv for inv in new_invoices if inv.kind == "PURCHASE"],
        receipts=new_receipts,
        ledger=new_ledger,
    )


def enrich_books_for_high_match(books: Books, target_rate: float = 0.85) -> Books:
    """Enrich books with valid utility receipts, tax payment slips and cash sales invoices
    so that clean months achieve an automatic match rate of ~85% (docs/18 §5 / demo alignment)."""
    new_statements = dict(books.statements)
    new_sales = list(books.sales)
    new_purchases = list(books.purchases)
    new_receipts = list(books.receipts)

    for m, st in sorted(books.statements.items()):
        m_clean = m.replace("-", "")
        target_count = int(round(len(st.rows) * target_rate))
        current_count = sum(1 for r in st.rows if r.documents)
        needed = target_count - current_count
        if needed <= 0:
            continue

        new_rows: list[BankRow] = []
        cash_idx = 1
        for r in st.rows:
            if r.documents or needed <= 0:
                new_rows.append(r)
                continue

            if r.description.startswith("WAREHOUSE RENT") and r.debit:
                inv_key = f"inv-purchase-rent-{m}"
                inv_num = f"RENT/{m_clean}/001"
                amt = r.debit
                inv = InvoiceData(
                    key=inv_key,
                    kind="PURCHASE",
                    number=inv_num,
                    issue_date=r.date,
                    due_date=r.date,
                    issuer=Party(
                        "PT Graha Properti Nusantara",
                        ("Jl. Soekarno-Hatta 412, Bandung",),
                        "02.345.678.9-422.000",
                    ),
                    bill_to=world.BUSINESS,
                    lines=[Line("Warehouse Monthly Rental Lease", 1, amt)],
                    vat_rate=Decimal("0"),
                    pay_to=PayTo(
                        "Archipelago Commerce Bank", "8821990412", "PT Graha Properti Nusantara"
                    ),
                    layout="gvf",
                    terms_days=0,
                )
                new_purchases.append(inv)
                new_rows.append(
                    replace(
                        r,
                        description=f"{r.description} {inv_num}",
                        documents=[inv.file],
                        invoice_refs=[inv_num],
                    )
                )
                needed -= 1
            elif r.description.startswith("INTERNET BILL") and r.debit:
                rec_key = f"receipt-internet-{m}"
                rec_no = f"TELKOM-{m_clean}-022781"
                amt = r.debit
                rec = ReceiptData(
                    key=rec_key,
                    merchant=Party(
                        "PT Telkom Indonesia (Persero) Tbk",
                        ("Bandung",),
                        "01.000.013.1-093.000",
                    ),
                    issued_at=datetime(r.date.year, r.date.month, r.date.day, 10, 0, 0),
                    items=[Line("IndiBiz Fiber Internet Subscription", 1, amt)],
                    vat_rate=Decimal("0"),
                    payment="TRANSFER",
                    form="pdf",
                    expense_account="6150",
                    receipt_no=rec_no,
                )
                new_receipts.append(rec)
                new_rows.append(replace(r, documents=[rec.file]))
                needed -= 1
            elif r.description.startswith("WATER BILL") and r.debit:
                rec_key = f"receipt-water-{m}"
                rec_no = f"PDAM-{m_clean}-4471"
                amt = r.debit
                rec = ReceiptData(
                    key=rec_key,
                    merchant=Party(
                        "Perumda Tirtawening Kota Bandung",
                        ("Bandung",),
                        "01.234.567.8-421.000",
                    ),
                    issued_at=datetime(r.date.year, r.date.month, r.date.day, 11, 0, 0),
                    items=[Line("Commercial Water Supply", 1, amt)],
                    vat_rate=Decimal("0"),
                    payment="TRANSFER",
                    form="pdf",
                    expense_account="6150",
                    receipt_no=rec_no,
                )
                new_receipts.append(rec)
                new_rows.append(replace(r, documents=[rec.file]))
                needed -= 1
            elif r.description.startswith("ELECTRICITY BILL") and r.debit:
                rec_key = f"receipt-electricity-{m}"
                rec_no = f"PLN-{m_clean}-5321"
                amt = r.debit
                rec = ReceiptData(
                    key=rec_key,
                    merchant=Party(
                        "PT PLN (Persero) UID Jawa Barat",
                        ("Bandung",),
                        "01.001.623.6-051.000",
                    ),
                    issued_at=datetime(r.date.year, r.date.month, r.date.day, 14, 0, 0),
                    items=[Line("Electricity Tariff B2/6600VA", 1, amt)],
                    vat_rate=Decimal("0"),
                    payment="TRANSFER",
                    form="pdf",
                    expense_account="6150",
                    receipt_no=rec_no,
                )
                new_receipts.append(rec)
                new_rows.append(replace(r, documents=[rec.file]))
                needed -= 1
            elif r.description.startswith("VAT PAYMENT") and r.debit:
                rec_key = f"receipt-vat-{m}"
                rec_no = f"NTPN-{m_clean}-9182"
                amt = r.debit
                rec = ReceiptData(
                    key=rec_key,
                    merchant=Party(
                        "Kementerian Keuangan RI - DJP",
                        ("Jakarta",),
                        "00.000.000.0-000.000",
                    ),
                    issued_at=datetime(r.date.year, r.date.month, r.date.day, 9, 30, 0),
                    items=[Line("Bukti Penerimaan Negara (BPN) - PPN Masa", 1, amt)],
                    vat_rate=Decimal("0"),
                    payment="TRANSFER",
                    form="pdf",
                    expense_account="2100",
                    receipt_no=rec_no,
                )
                new_receipts.append(rec)
                new_rows.append(replace(r, documents=[rec.file]))
                needed -= 1
            elif r.description.startswith("CASH DEPOSIT") and r.credit:
                inv_key = f"inv-sales-cash-{m}-{cash_idx:02d}"
                inv_num = f"INV/SCR/CS/{m_clean}/{cash_idx:02d}"
                amt = r.credit
                inv = InvoiceData(
                    key=inv_key,
                    kind="SALES",
                    number=inv_num,
                    issue_date=r.date,
                    due_date=r.date,
                    issuer=world.BUSINESS,
                    bill_to=Party("Walk-in Retail Cash Sales", ("Bandung",), None),
                    lines=[Line("Daily Espresso & Coffee Sales", 1, amt)],
                    vat_rate=Decimal("0"),
                    pay_to=world.OWN_PAY_TO,
                    layout="sales",
                    terms_days=0,
                )
                new_sales.append(inv)
                cash_idx += 1
                new_rows.append(
                    replace(
                        r,
                        description=f"{r.description} {inv_num}",
                        documents=[inv.file],
                        invoice_refs=[inv_num],
                    )
                )
                needed -= 1
            else:
                new_rows.append(r)

        new_statements[m] = replace(st, rows=new_rows)

    return replace(
        books,
        statements=new_statements,
        sales=new_sales,
        purchases=new_purchases,
        receipts=new_receipts,
    )


def generate_recent_pack(out_dir: Path, target_match_rate: float = 0.85) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)

    base = generate_books(1)
    # Shift Q2 (Apr, May, Jun 2026) -> Aug, Sep, Oct 2026 (+4 months)
    shifted = shift_books_to_recent(
        base, source_months=("2026-04", "2026-05", "2026-06"), delta_months=4
    )
    shifted = enrich_books_for_high_match(shifted, target_rate=target_match_rate)

    rng = Rng(1, "render_recent")
    rendered_files: dict[str, bytes] = {}

    # Statements
    for month, st in sorted(shifted.statements.items()):
        rendered = render_statement(st)
        fname = statement_file(month)
        rendered_files[fname] = rendered.pdf

    # Invoices
    for inv in shifted.invoices:
        rendered_files[inv.file] = render_invoice(inv)

    # Receipts
    for rec in shifted.receipts:
        if rec.form == "jpeg":
            rendered_files[rec.file] = render_receipt_jpeg(rec, rng)
        else:
            rendered_files[rec.file] = render_receipt_pdf(rec)

    # Ledger
    ledger_filename = f"ledger-{'--'.join(sorted(shifted.statements.keys()))}.csv"
    rendered_files[ledger_filename] = render_ledger_csv(shifted.ledger)
    rendered_files["ledger-2026-H1.csv"] = rendered_files[ledger_filename]

    # Save all files
    for fname, data in rendered_files.items():
        (out_dir / fname).write_bytes(data)

    upload_order = [f for f in sorted(rendered_files.keys()) if not f.startswith("ledger-")]
    upload_order.append(ledger_filename)

    (out_dir / "upload-order.txt").write_text("\n".join(upload_order) + "\n", encoding="utf-8")

    truth_doc = {
        "workspace": {
            "name": "Sunrise Coffee Roasters",
            "profile": {"legalName": "Sunrise Coffee Roasters"},
            "bankAccounts": [
                {
                    "bankName": "Archipelago Commerce Bank",
                    "accountNumber": "9900004821",
                    "holderName": "SUNRISE COFFEE ROASTERS",
                }
            ],
        },
        "uploadOrder": upload_order,
        "months": list(sorted(shifted.statements.keys())),
    }
    (out_dir / "truth.json").write_text(json.dumps(truth_doc, indent=2) + "\n", encoding="utf-8")

    return list(rendered_files.keys())


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate recent Aug-Oct 2026 synthetic books")
    parser.add_argument(
        "--out", type=Path, default=Path("demo-pack-recent"), help="Output directory"
    )
    parser.add_argument(
        "--match-rate",
        type=float,
        default=0.85,
        help="Target auto match rate (default: 0.85 for ~85% match)",
    )
    args = parser.parse_args()

    files = generate_recent_pack(args.out, target_match_rate=args.match_rate)
    pct = int(args.match_rate * 100)
    print(f"Generated {len(files)} files in {args.out} (target match rate: {pct}%):")
    for f in sorted(files):
        print(f"  • {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
