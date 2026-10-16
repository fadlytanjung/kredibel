"""Scenarios S1–S5 (docs/18 §5): S1's books, plus one story each, plus an upload order."""

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from . import world
from .books import generate_books
from .matching_cases import intended_matches
from .model import Books
from .output import render_books
from .render_ledger import render_ledger_csv
from .render_receipt import photo_variant
from .render_statement import render_statement, statement_file
from .rng import Rng
from .scan import scan_pdf
from .shift import day, ledger_file, month, months, shift_books, text
from .tamper import (
    TamperRecord,
    change_supplier_account,
    duplicate_ledger_journal,
    edit_amount,
    unpaid_supplier_invoices,
)

SCENARIOS = {
    "S1": (
        "A normal half-year",
        "Six months of clean books: statements, sales and purchase invoices, receipts and the "
        "ledger. One proposed match in February and one deposit missing from the ledger in June.",
    ),
    "S2": (
        "The edited statement",
        "S1, but the March statement was edited in a PDF editor: the credit of 14 March now shows "
        "7,250,000.00 instead of 1,250,000.00, drawn in Helvetica and saved as a second revision.",
    ),
    "S3": (
        "Duplicates",
        "S1 plus copies made the way they happen: the February statement uploaded twice and "
        "exported again, a purchase invoice scanned, a receipt photographed again, and one ledger "
        "journal keyed in twice.",
    ),
    "S4": (
        "Payment diversion and unpaid bills",
        "S1, but Roastline Equipment Service's May invoice asks to be paid into a new account at "
        "another bank, and two Bluewater Trading Co. invoices arrive that nobody has ever paid.",
    ),
    "S5": (
        "Reverse order",
        "S1's files uploaded in reverse: statements first, then the ledger, invoices and receipts "
        "last. Everything must end the same as S1.",
    ),
}


@dataclass
class Duplicate:
    code: str
    of: str
    held: bool
    severity: str | None


@dataclass
class Scenario:
    name: str
    seed: int
    books: Books
    files: dict[str, bytes]
    upload_order: list[str]
    tampering: list[TamperRecord] = field(default_factory=list)
    duplicates: dict[str, Duplicate] = field(default_factory=dict)
    ledger_duplicates: list[str] = field(default_factory=list)
    changed: dict[str, Any] = field(default_factory=dict)
    scanned: bool = False
    row_pages: dict[str, int] = field(default_factory=dict)

    @property
    def title(self) -> str:
        return SCENARIOS[self.name][0]

    @property
    def summary(self) -> str:
        return SCENARIOS[self.name][1]


def upload_order(books: Books, extra: dict[str, str] | None = None) -> list[str]:
    """The ledger first, then month by month: invoices, receipts, the statement (docs/18 §6).
    `extra` places added files right after an existing one."""
    order = [ledger_file()]
    for key in months():
        order += [inv.file for inv in books.sales if inv.issue_date.strftime("%Y-%m") == key]
        order += [inv.file for inv in books.purchases if inv.issue_date.strftime("%Y-%m") == key]
        order += [rec.file for rec in books.receipts if rec.date.strftime("%Y-%m") == key]
        order.append(statement_file(key))
    for added, after in (extra or {}).items():
        order.insert(order.index(after) + 1, added)
    return order


def reverse_order(books: Books) -> list[str]:
    """S5: statements first, then the ledger, then invoices and receipts, all newest first."""
    statements = [statement_file(m) for m in reversed(months())]
    documents = [
        f for f in reversed(upload_order(books)) if f not in statements and f != ledger_file()
    ]
    return [*statements, ledger_file(), *documents]


def build(name: str, seed: int, *, scan: bool = False) -> Scenario:
    books = generate_books(seed)
    rng = Rng(seed, "scenario", name)
    if name == "S4":
        _s4_books(books, rng)
    shift_books(books)  # the demo's books end last month (docs/18 §5); no-op otherwise
    bundle = render_books(books)
    sc = Scenario(name, seed, books, dict(bundle.files), upload_order(books))
    sc.row_pages = {k: p for r in bundle.statements.values() for k, p in r.row_pages.items()}
    if name == "S2":
        _s2(sc, bundle.statements)
    elif name == "S3":
        _s3(sc, rng)
    elif name == "S4":
        sc.changed = {
            "T12": text("inv-purchase-2026-05-03"),
            "T13": [text("inv-purchase-2026-04-03"), text("inv-purchase-2026-04-04")],
        }
        sc.tampering += [
            TamperRecord(
                "T12",
                text("inv-purchase-2026-05-03.pdf"),
                {
                    "supplier": world.ROASTLINE.party.name,
                    "before": world.ROASTLINE.pay_to.account_number,
                    "after": world.ROASTLINE_NEW_PAY_TO.account_number,
                    "bank": world.ROASTLINE_NEW_PAY_TO.bank_name,
                },
            ),
            TamperRecord(
                "T13", text("inv-purchase-2026-04-03.pdf"), {"supplier": world.BLUEWATER.party.name}
            ),
            TamperRecord(
                "T13", text("inv-purchase-2026-04-04.pdf"), {"supplier": world.BLUEWATER.party.name}
            ),
        ]
    elif name == "S5":
        sc.upload_order = reverse_order(books)
    if scan:
        _scan_all(sc, rng)
    return sc


def _s2(sc: Scenario, statements: dict) -> None:
    march = sc.books.statements[month("2026-03")]
    anchor = next(
        r
        for r in march.rows
        if r.date == day(world.T1_ANCHOR_DATE) and r.credit == world.T1_ANCHOR_AMOUNT
    )
    placed = next(
        p for p in statements[month("2026-03")].amounts[anchor.key] if p.field == "credit"
    )
    file = statement_file(month("2026-03"))
    sc.files[file] = edit_amount(
        sc.files[file],
        placed,
        world.T1_EDITED_AMOUNT,
        created=march.created_at,
        file_id=f"S2|{sc.seed}|{file}",
    )
    sc.tampering.append(
        TamperRecord(
            "T1",
            file,
            {
                "rowKey": anchor.key,
                "rowIndex": anchor.row_index,
                "field": "credit",
                "before": str(world.T1_ANCHOR_AMOUNT),
                "after": str(world.T1_EDITED_AMOUNT),
                "font": "Helvetica",
                "producer": "PDF Editor 11",
                "modDate": (march.created_at + timedelta(days=3)).isoformat(),
            },
        )
    )


def _s3(sc: Scenario, rng: Rng) -> None:
    books = sc.books
    feb = statement_file(month("2026-02"))
    # T7: the same file again under the name a browser gives a second download.
    copy_name = f"statement-{month('2026-02')} (1).pdf"
    sc.files[copy_name] = sc.files[feb]
    # T8: the same month exported again nine days later: identical rows, new bytes.
    reexport = f"statement-{month('2026-02')}-reexport.pdf"
    st = books.statements[month("2026-02")]
    sc.files[reexport] = render_statement(
        st, created=st.created_at + timedelta(days=9, hours=7, minutes=41)
    ).pdf
    # T9: Green Valley Farms' March invoice printed and scanned.
    gvf = next(
        i
        for i in books.purchases
        if i.issuer == world.GREEN_VALLEY.party and i.key[13:20] == month("2026-03")
    )
    scanned = f"{gvf.key}-scan.pdf"
    sc.files[scanned] = scan_pdf(
        sc.files[gvf.file], rng.stream("T9"), scanned_at=_noon(gvf.issue_date, 20)
    )
    # T10: a June receipt photographed again at another angle.
    receipt = next(
        r
        for r in books.receipts
        if r.key.startswith(f"receipt-{month('2026-06')}") and r.form == "jpeg"
    )
    again = f"{receipt.key}-photo2.jpg"
    sc.files[again] = photo_variant(receipt, Rng(sc.seed, "render"))
    # T11: one ledger journal keyed in twice.
    books.ledger, copied = duplicate_ledger_journal(books.ledger, day(world.T11_FROM))
    sc.files[ledger_file()] = render_ledger_csv(books.ledger)
    books.matches = intended_matches(books)
    sc.ledger_duplicates = copied
    sc.duplicates = {
        copy_name: Duplicate("D01_EXACT_FILE_DUPLICATE", feb, held=False, severity="INFO"),
        reexport: Duplicate("D02_STATEMENT_PERIOD_DUPLICATE", feb, held=True, severity="MEDIUM"),
        scanned: Duplicate("D03_INVOICE_DUPLICATE", gvf.file, held=True, severity="MEDIUM"),
        again: Duplicate("D05_RECEIPT_DUPLICATE", receipt.file, held=True, severity="MEDIUM"),
    }
    sc.upload_order = upload_order(
        books,
        {
            copy_name: feb,
            reexport: statement_file(month("2026-03")),
            scanned: statement_file(month("2026-05")),
            again: receipt.file,
        },
    )
    sc.tampering += [
        TamperRecord("T7", copy_name, {"of": feb}),
        TamperRecord("T8", reexport, {"of": feb}),
        TamperRecord("T9", scanned, {"of": gvf.file}),
        TamperRecord("T10", again, {"of": receipt.file}),
        TamperRecord("T11", ledger_file(), {"entries": copied}),
    ]


def _s4_books(books: Books, rng: Rng) -> None:
    change_supplier_account(books, "inv-purchase-2026-05-03")
    unpaid_supplier_invoices(books, rng)
    books.matches = intended_matches(books)


def _scan_all(sc: Scenario, rng: Rng) -> None:
    sc.scanned = True
    for name in sorted(sc.files):
        if name.endswith(".pdf"):
            sc.files[name] = scan_pdf(
                sc.files[name], rng.stream("scan", name), scanned_at=_noon(day(world.T11_FROM), 0)
            )


def _noon(d, days: int):
    from datetime import datetime, time

    return datetime.combine(d + timedelta(days=days), time(12, 0))
