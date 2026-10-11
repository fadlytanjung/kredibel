"""Turn books into files (plan 002: data first, renderers second). Scenarios then tamper with,
duplicate or add to these files; nothing here knows about scenarios."""

from dataclasses import dataclass, field

from .model import Books
from .render_invoice import render_invoice
from .render_ledger import render_ledger_csv
from .render_receipt import render_receipt_jpeg, render_receipt_pdf
from .render_statement import Rendered, render_statement, statement_file
from .rng import Rng

LEDGER_FILE = "ledger-2026-H1.csv"


@dataclass
class Bundle:
    files: dict[str, bytes] = field(default_factory=dict)
    statements: dict[str, Rendered] = field(default_factory=dict)  # by month


def render_books(books: Books) -> Bundle:
    rng = Rng(books.seed, "render")
    bundle = Bundle()
    for month, st in books.statements.items():
        rendered = render_statement(st)
        bundle.statements[month] = rendered
        bundle.files[statement_file(month)] = rendered.pdf
    for inv in books.invoices:
        bundle.files[inv.file] = render_invoice(inv)
    for rec in books.receipts:
        if rec.form == "jpeg":
            bundle.files[rec.file] = render_receipt_jpeg(rec, rng)
        else:
            bundle.files[rec.file] = render_receipt_pdf(rec)
    bundle.files[LEDGER_FILE] = render_ledger_csv(books.ledger)
    return bundle
