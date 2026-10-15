"""Clients and suppliers from the books (spec 014, T014-01; AC-014-1; docs/08 §4.2): roles from the
books, spellings merged, unnamed rows in policy-named buckets, accounts seen, order independence.
Synthetic names only."""

import random
from datetime import date
from decimal import Decimal as D
from pathlib import Path

from app.adapters.policy_files import load_category_policy
from app.domain.counterparties import Counterparty, build_counterparties
from app.domain.models.bank_line import BankLine
from app.domain.models.invoice import Invoice, Receipt

ROOT = Path(__file__).resolve().parents[3]
POLICY = load_category_policy(
    ROOT / "contracts" / "policy" / "categories.v1.yaml", ROOT / "contracts" / "policy"
)
OWN = ["Sunrise Coffee Roasters"]


def line(
    tx: str, day: date, amount: str, desc: str, category: str, party: str | None = None
) -> BankLine:
    return BankLine(
        tx_id=tx,
        doc_id="doc_stmt",
        page=1,
        row_index=day.day,
        date=day,
        month=f"{day:%Y-%m}",
        description=desc,
        amount=D(amount),
        balance=None,
        counterparty_name=party,
        category=category,
    )


def invoice(
    iid: str,
    kind: str,
    party: str,
    issued: date,
    total: str,
    *,
    pay_to: str | None = None,
    payment: str | None = "PAID_BANK",
) -> Invoice:
    return Invoice(
        invoice_id=iid,
        doc_id=f"doc_{iid}",
        kind=kind,  # type: ignore[arg-type]
        number=iid.upper(),
        issuer_name=OWN[0] if kind == "SALES" else party,
        buyer_name=party if kind == "SALES" else OWN[0],
        issue_date=issued,
        month=f"{issued:%Y-%m}",
        total=D(total),
        currency="IDR",
        pay_to_masked=pay_to,
        evidence={"payment": payment} if payment else None,
    )


def receipt(rid: str, merchant: str, day: date, total: str) -> Receipt:
    return Receipt(
        receipt_id=rid,
        doc_id=f"doc_{rid}",
        merchant_name=merchant,
        date=day,
        month=f"{day:%Y-%m}",
        total=D(total),
        currency="IDR",
    )


def by_name(parties: list[Counterparty]) -> dict[str, Counterparty]:
    return {p.name: p for p in parties}


def test_roles_come_from_the_books_and_the_policy():
    lines = [
        line(
            "t1",
            date(2026, 3, 2),
            "19597050.00",
            "TRANSFER IN DAYBREAK CAFE",
            "SALES_RECEIPT",
            "DAYBREAK CAFE",
        ),
        line(
            "t2",
            date(2026, 3, 5),
            "-12400000.00",
            "TRANSFER OUT GREEN VALLEY FARMS 0912",
            "INVENTORY_PURCHASE",
            "GREEN VALLEY FARMS",
        ),
        line(
            "t3",
            date(2026, 3, 9),
            "-2500000.00",
            "LOAN INSTALLMENT LN-0071",
            "LOAN_REPAYMENT",
            None,
        ),
        line(
            "t4",
            date(2026, 3, 12),
            "-5000000.00",
            "TRANSFER OUT ANDI PRATAMA",
            "OWNER_DRAWING",
            "ANDI PRATAMA",
        ),
        line("t5", date(2026, 3, 15), "-4410000.00", "VAT PAYMENT FEB", "TAX_PAYMENT", None),
        line("t6", date(2026, 3, 31), "-25000.00", "ADMIN FEE", "BANK_FEES", None),
        line(
            "t7",
            date(2026, 3, 20),
            "-10000000.00",
            "TRANSFER TO SUNRISE COFFEE ROASTERS SAVINGS",
            "INTERNAL_TRANSFER",
            "SUNRISE COFFEE ROASTERS",
        ),
    ]
    invoices = [
        invoice("inv-sales-1", "SALES", "Daybreak Café", date(2026, 3, 1), "19597050.00"),
        invoice(
            "inv-purchase-1",
            "PURCHASE",
            "Green Valley Farms",
            date(2026, 3, 3),
            "12400000.00",
            pay_to="••••7312",
        ),
    ]
    receipts = [receipt("rc-1", "Cendana Fuel Station", date(2026, 3, 6), "513264.00")]

    parties = by_name(build_counterparties(lines, invoices, receipts, policy=POLICY, own_names=OWN))

    assert parties["Daybreak Café"].roles == ("CLIENT",)
    assert parties["Green Valley Farms"].roles == ("SUPPLIER",)
    assert parties["Cendana Fuel Station"].roles == ("SUPPLIER",)
    assert parties["ANDI PRATAMA"].roles == ("OWNER",) and parties["ANDI PRATAMA"].kind == "PERSON"
    assert parties["Sunrise Coffee Roasters"].roles == ("OWN_ACCOUNT",)
    # Unnamed rows go to buckets worded by the policy, so totals stay complete.
    tax = POLICY.categories["TAX_PAYMENT"]
    assert parties[tax.bucket or tax.label].roles == ("GOVERNMENT",)
    assert parties[tax.bucket or tax.label].kind == "GOVERNMENT"
    fees = POLICY.categories["BANK_FEES"]
    assert parties[fees.bucket or fees.label].roles == ("OTHER",)
    loans = POLICY.categories["LOAN_REPAYMENT"]
    assert parties[loans.bucket or loans.label].roles == ("LENDER",)
    assert len(parties) == 8
    for p in parties.values():
        assert p.counterparty_id.startswith("cp_") and len(p.counterparty_id) == 19


def test_spellings_merge_into_one_party_with_the_document_spelling_as_its_name():
    lines = [
        line(
            "t1",
            date(2026, 1, 9),
            "70795800.00",
            "TRANSFER IN HARBORVIEW HOTEL GROUP INV/SCR/2026/01/0001",
            "SALES_RECEIPT",
            "HARBORVIEW HOTEL GROUP",
        ),
        line(
            "t2",
            date(2026, 2, 11),
            "63919350.00",
            "INSTANT TRANSFER IN HARBORVIEW HOTEL GRP",
            "SALES_RECEIPT",
            "HARBORVIEW HOTEL GRP",
        ),
        line(
            "t3",
            date(2026, 2, 20),
            "-1000000.00",
            "REFUND HARBORVIEW HOTEL GROUP",
            "OTHER_OPERATING_EXPENSE",
            "HARBORVIEW HOTEL GROUP",
        ),
    ]
    invoices = [
        invoice("inv-1", "SALES", "Harborview Hotel Group", date(2026, 1, 6), "70795800.00"),
        invoice(
            "inv-2",
            "SALES",
            "Harborview Hotel Group",
            date(2026, 2, 4),
            "63919350.00",
            payment="UNPAID",
        ),
    ]
    [party] = build_counterparties(lines, invoices, [], policy=POLICY, own_names=OWN)

    assert party.name == "Harborview Hotel Group"
    assert set(party.aliases) == {"HARBORVIEW HOTEL GROUP", "HARBORVIEW HOTEL GRP"}
    assert party.roles == ("CLIENT",) and party.kind == "BUSINESS"
    assert party.totals_by_month["2026-01"].in_amount == D("70795800.00")
    assert party.totals_by_month["2026-02"].in_amount == D("63919350.00")
    assert party.totals_by_month["2026-02"].out_amount == D("1000000.00")
    assert party.totals_by_month["2026-02"].count == 2
    assert (party.total_in, party.total_out) == (D("134715150.00"), D("1000000.00"))
    assert party.open_invoices == 1
    assert (party.first_date, party.last_date) == (date(2026, 1, 6), date(2026, 2, 20))
    assert party.bank_line_ids == ("t1", "t2", "t3") and party.invoice_ids == ("inv-1", "inv-2")
    assert party.sample_evidence[0]["invoiceId"] == "inv-1" and len(party.sample_evidence) <= 3


def test_a_supplier_paid_to_two_accounts_shows_both_with_first_and_last_use():
    invoices = [
        invoice(
            "inv-a",
            "PURCHASE",
            "Roastline Equipment Service",
            date(2026, 2, 1),
            "5000000.00",
            pay_to="••••3318",
        ),
        invoice(
            "inv-b",
            "PURCHASE",
            "Roastline Equipment Service",
            date(2026, 4, 1),
            "6000000.00",
            pay_to="••••3318",
        ),
        invoice(
            "inv-c",
            "PURCHASE",
            "Roastline Equipment Service",
            date(2026, 5, 1),
            "7000000.00",
            pay_to="••••3108",
        ),
    ]
    [party] = build_counterparties([], invoices, [], policy=POLICY, own_names=OWN)
    assert [(a.account_masked, a.first_seen, a.last_seen) for a in party.accounts_seen] == [
        ("••••3318", date(2026, 2, 1), date(2026, 4, 1)),
        ("••••3108", date(2026, 5, 1), date(2026, 5, 1)),
    ]
    assert party.open_invoices == 0


def test_the_result_does_not_depend_on_the_order_of_the_books():
    rng = random.Random(14)
    lines = [
        line(
            f"t{i}",
            date(2026, 1 + i % 6, 1 + i % 27),
            str(1000 * (i + 1)) + ".00",
            f"TRANSFER IN CLIENT {i % 5}",
            "SALES_RECEIPT",
            f"CLIENT {i % 5}",
        )
        for i in range(30)
    ]
    invoices = [
        invoice(f"inv-{i}", "SALES", f"Client {i % 5}", date(2026, 1 + i % 6, 2), "1000.00")
        for i in range(10)
    ]
    receipts = [
        receipt(f"rc-{i}", f"Shop {i % 3}", date(2026, 1 + i % 6, 3), "100.00") for i in range(6)
    ]
    first = build_counterparties(lines, invoices, receipts, policy=POLICY, own_names=OWN)
    shuffled = (list(lines), list(invoices), list(receipts))
    for part in shuffled:
        rng.shuffle(part)
    again = build_counterparties(*shuffled, policy=POLICY, own_names=OWN)
    assert first == again
    assert [p.name for p in first] == sorted(p.name for p in first)
