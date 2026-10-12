"""Invoice and receipt pages become grounded records (docs/07 §6.2, docs/09 §3.7)."""

from datetime import date
from decimal import Decimal

from app.domain.invoice_records import build_invoices, build_receipts, invoice_kind, is_own_name
from app.domain.reading import (
    InvoiceLineReading,
    InvoicePageReading,
    ReceiptItemReading,
    ReceiptPageReading,
)
from tests.unit.test_verify_invoice import PAGE, _line

OWN = ["Acme Sdn Bhd", "Acme Studio"]


def _invoice(page: int, number: str | None = "INV-2026-0042", **kw) -> InvoicePageReading:
    base = dict(
        page=page,
        invoice_number=number,
        issuer_name="ACME SDN BHD",
        buyer_name="Kopi Kita Enterprise",
        issue_date_text="22/12/2025",
        currency="RM",
        subtotal_text="1,800.00",
        tax_text="108.00",
        total_text="1,908.00",
        payment_account_text="5140 1234 5678",
        lines=[
            InvoiceLineReading(
                description="Website design", quantity_text="1", amount_text="1,200.00"
            ),
            InvoiceLineReading(
                description="Hosting (12 months)", quantity_text="1", amount_text="300.00"
            ),
            InvoiceLineReading(
                description="Hosting setup", quantity_text="1", amount_text="300.00"
            ),
        ],
    )
    return InvoicePageReading(**{**base, **kw})


def test_an_invoice_is_grounded_and_masked():
    result = build_invoices(
        "doc_1", [_invoice(1)], {1: PAGE}, classified="PURCHASE_INVOICE", own_names=OWN
    )
    [inv] = result.records
    assert (inv.kind, inv.number, inv.currency) == ("SALES", "INV-2026-0042", "MYR")
    assert (inv.issue_date, inv.month) == (date(2025, 12, 22), "2025-12")
    assert (inv.subtotal, inv.tax, inv.total) == (
        Decimal("1800.00"),
        Decimal("108.00"),
        Decimal("1908.00"),
    )
    assert [ln.amount for ln in inv.lines] == [
        Decimal("1200.00"),
        Decimal("300.00"),
        Decimal("300.00"),
    ]
    assert inv.pay_to_masked == "••••5678"
    assert "5140" not in str(inv.consensus)
    assert (
        inv.consensus["total"]["status"] == "AGREED" and inv.consensus["total"]["bbox"] is not None
    )
    assert inv.consensus["lines.2.amount"]["status"] == "AGREED"
    assert inv.notes == []
    assert result.months == ["2025-12"]
    # payTo is not printed on this page: single source; everything else agreed
    assert result.compared - result.agreed == 1


def test_a_pdf_with_several_invoices_gives_one_record_per_printed_number():
    pages = [_invoice(1, "INV-1"), _invoice(2, None), _invoice(3, "INV-2")]
    result = build_invoices("doc_1", pages, {}, classified="SALES_INVOICE", own_names=OWN)
    assert [(i.number, i.pages) for i in result.records] == [("INV-1", [1, 2]), ("INV-2", [3])]
    assert len({i.invoice_id for i in result.records}) == 2


def test_sales_or_purchase_is_decided_from_the_workspace_names():
    assert is_own_name("ACME SDN. BHD.", OWN)
    assert not is_own_name("Kopi Kita Enterprise", OWN)
    assert invoice_kind("Acme Studio", "Kopi Kita", OWN, "PURCHASE_INVOICE") == "SALES"
    assert invoice_kind("Supplier Co", "ACME SDN BHD", OWN, "SALES_INVOICE") == "PURCHASE"
    assert invoice_kind("Supplier Co", "Someone", OWN, "SALES_INVOICE") == "SALES"


def test_a_total_that_does_not_add_up_is_noted():
    page = _invoice(1, total_text="1,999.00")
    [inv] = build_invoices(
        "doc_1", [page], {1: PAGE}, classified="SALES_INVOICE", own_names=OWN
    ).records
    assert inv.notes == ["subtotal plus tax differs from the printed total"]
    assert inv.consensus["total"]["status"] == "SINGLE_SOURCE"


RECEIPT = [
    *_line(0.05, ("KEDAI", 0.10), ("RUNCIT", 0.17), ("MAJU", 0.25)),
    *_line(0.08, ("12/09/2026", 0.10), ("14:32", 0.30)),
    *_line(0.12, ("Teh", 0.10), ("tarik", 0.14), ("3.50", 0.40)),
    *_line(0.15, ("Roti", 0.10), ("canai", 0.15), ("2.00", 0.40)),
    *_line(0.20, ("TOTAL", 0.10), ("5.50", 0.40)),
    *_line(0.23, ("DUITNOW", 0.10), ("QR", 0.18)),
]


def test_a_receipt_is_grounded_with_its_payment_method():
    page = ReceiptPageReading(
        page=1,
        merchant_name="KEDAI RUNCIT MAJU",
        date_text="12/09/2026",
        time_text="14:32",
        total_text="5.50",
        payment_method_text="DUITNOW QR",
        currency="RM",
        items=[
            ReceiptItemReading(description="Teh tarik", amount_text="3.50"),
            ReceiptItemReading(description="Roti canai", amount_text="2.00"),
        ],
    )
    result = build_receipts("doc_9", [page], {1: RECEIPT})
    [r] = result.records
    assert (r.merchant_name, r.date, r.month, r.total) == (
        "KEDAI RUNCIT MAJU",
        date(2026, 9, 12),
        "2026-09",
        Decimal("5.50"),
    )
    assert (r.payment_method, r.currency) == ("TRANSFER", "MYR")
    assert result.agreement == 1.0
    assert r.consensus["items.1.amount"]["status"] == "AGREED"


def test_an_amount_printed_as_a_word_is_not_an_amount():
    page = _invoice(1, number="INV-9", total_text="1,908.00")
    page.lines.append(InvoiceLineReading(description="Domain", amount_text="Included"))
    [inv] = build_invoices(
        "doc_1", [page], {1: PAGE}, classified="SALES_INVOICE", own_names=OWN
    ).records
    assert inv.lines[-1].amount is None
    assert "lines.3.amount" not in inv.consensus
    assert not any("Included" in n for n in inv.notes)
