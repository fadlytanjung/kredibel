"""Six months of books for Sunrise Coffee Roasters (docs/18 §3.6), generated as data.

Documents come first (invoices, receipts), then the bank lines that pay them and the lines with no
document, then balances, then the ledger, so every file rendered later agrees by construction. The
special matching cases of §3.6 are built here; `matching_cases.py` checks they are what they claim.
"""

import calendar
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_CEILING, Decimal
from typing import Any

from . import world
from .matching_cases import amount_tolerance, intended_matches
from .model import (
    ZERO,
    BankRow,
    Books,
    InvoiceData,
    LedgerRow,
    Line,
    ReceiptData,
    StatementData,
    money,
)
from .rng import Rng
from .volume import extra
from .world import MONTH_ABBR, MONTH_NAME, MONTHS, YEAR, month_parts


@dataclass
class _Payment:
    """A bank line that pays one or more invoices (or part of one)."""

    date: date
    amount: Decimal
    invoices: list[InvoiceData]
    with_ref: bool
    instant: bool = False


def _month_end(month: str) -> date:
    year, mon = month_parts(month)
    return date(year, mon, calendar.monthrange(year, mon)[1])


def _lines_for(rng: Rng, target: Decimal) -> list[Line]:
    """1–3 products whose subtotal lands near `target`."""
    products = rng.sample(list(world.PRODUCTS), rng.between(1, 3))
    share = target / len(products)
    return [
        Line(description, max(1, int((share / price).to_integral_value())), price)
        for description, price in products
    ]


def _bump(lines: list[Line]) -> list[Line]:
    first = lines[0]
    return [Line(first.description, first.quantity + 1, first.unit_price), *lines[1:]]


def _thousands(amount: Decimal) -> Decimal:
    return (amount / 1000).to_integral_value() * 1000 + Decimal("0.00")


def _same(a: Decimal, b: Decimal) -> bool:
    """Within twice the matching tolerance: a payment of one would fit the other."""
    return abs(a - b) <= max(amount_tolerance(a), amount_tolerance(b)) * 2


def _in_band(a: Decimal, b: Decimal) -> bool:
    """`a` sits in b's withholding band (b·0.98 ≤ a < b, docs/08 §6.3), with a margin. It matters
    only for the same party: for another party the score stays below proposeScore."""
    return b * Decimal("0.975") - amount_tolerance(b) * 2 <= a <= b


def _clashes(
    amount: Decimal, any_party: list[Decimal], same_party: list[Decimal] | None = None
) -> bool:
    return any(_same(amount, o) for o in any_party) or any(
        _in_band(amount, o) or _in_band(o, amount) for o in same_party or []
    )


def _net_of_withholding(total: Decimal) -> Decimal:
    """2% withheld, rounded up to a whole rupiah: stays within T·0.98 ≤ c < T (docs/08 §6.3)."""
    net = (total * Decimal("0.98")).to_integral_value(rounding=ROUND_CEILING)
    return net.quantize(Decimal("0.01"))


# ---------------------------------------------------------------------------- sales invoices


def _sales_invoice(
    rng: Rng,
    month: str,
    seq: int,
    client: world.Client,
    issue: date,
    terms: int,
) -> InvoiceData:
    number = MONTHS.index(month) * 4 + seq
    return InvoiceData(
        key=f"inv-sales-{month}-{seq:02d}",
        kind="SALES",
        number=f"INV/SCR/{YEAR}/{month[5:]}/{number:04d}",
        issue_date=issue,
        due_date=issue + timedelta(days=terms),
        issuer=world.BUSINESS,
        bill_to=client.party,
        lines=_lines_for(rng, rng.amount(client.lo, client.hi)),
        vat_rate=world.VAT_RATE,
        pay_to=world.OWN_PAY_TO,
        layout="sales",
        terms_days=terms,
    )


def _sales(rng: Rng) -> list[InvoiceData]:
    out: list[InvoiceData] = []
    for month in MONTHS:
        r = rng.stream(month, "sales")
        year, mon = month_parts(month)
        clients = r.sample(world.CLIENTS, 4)
        for seq in range(1, 5):
            client = clients[seq - 1]
            if seq == 4 and month == "2026-06":
                # NOT_DUE: issued 25 Jun, due 25 Jul (docs/18 §3.6).
                out.append(_sales_invoice(r, month, seq, client, date(year, mon, 25), 30))
            elif seq == 4:
                # 30-day terms, paid the next month.
                out.append(_sales_invoice(r, month, seq, client, r.day(year, mon, 14, 20), 30))
            else:
                out.append(_sales_invoice(r, month, seq, client, r.day(year, mon, 1, 12), 14))
    _special_sales(rng, out)
    _dedupe_totals(out, lambda inv: inv.total)
    _separate_special_payments(out)
    _extra_sales(rng, out)
    return out


# ---------------------------------------------------------------------------- the demo's volume

# Spec 024: the clients of the planted sales cases get no extra invoices in those months.
_SPECIAL_CLIENT = {
    "2026-02": "Daybreak Café",
    "2026-03": "Highland Resort & Spa",
    "2026-04": "Spice Route Restaurant",
    "2026-05": "Harborview Hotel Group",
}


def _date_of(item: Any) -> date:
    return item.issue_date if isinstance(item, InvoiceData) else item.date


def _place(
    item: Any,
    existing: list[Any],
    reroll: Callable[[], None],
    reserved: list[Decimal],
    whole_party: bool = True,
) -> None:
    """An extra document whose total no nearby document of its kind could be taken for (the
    same rule as _dedupe_totals, but drawn again instead of nudged, and only within six weeks),
    and, for an invoice, that no other invoice of the same party in the books comes close to: two
    equal bills a few months apart read as one paid twice (D07). Receipts are paid at the till."""
    when = _date_of(item)
    near = [o for o in existing if abs((_date_of(o) - when).days) <= 45]
    party = [o.total for o in existing if whole_party and _party_of(o) == _party_of(item)]
    for _ in range(80):
        totals = [o.total for o in near] + party + reserved
        same = [o.total for o in near if _party_of(o) == _party_of(item)]
        if not _clashes(item.total, totals, same):
            return
        reroll()
    while _clashes(item.total, [o.total for o in near] + party + reserved):
        if isinstance(item, ReceiptData):
            item.items = _bump(item.items)
        else:
            item.lines = _bump(item.lines)


def _extra_sales(rng: Rng, out: list[InvoiceData]) -> None:
    if not extra()[0]:
        return
    by_key = {inv.key: inv for inv in out}
    pair = by_key["inv-sales-2026-05-02"].total + by_key["inv-sales-2026-05-03"].total
    reserved = [_net_of_withholding(by_key["inv-sales-2026-03-02"].total), pair]
    for month in MONTHS:
        r = rng.stream(month, "sales-extra")
        year, mon = month_parts(month)
        # Not in the month of a planted case or next to it: its weeks stay unambiguous.
        i = MONTHS.index(month)
        busy = {_SPECIAL_CLIENT.get(m) for m in MONTHS[max(0, i - 1) : i + 2]}
        pool = [c for c in (*world.CLIENTS, *world.EXTRA_CLIENTS) if c.party.name not in busy]
        for seq in range(5, 5 + extra()[0]):
            client = r.choice(pool)
            inv = _sales_invoice(r, month, seq, client, r.day(year, mon, 1, 12), 14)

            def reroll(inv: InvoiceData = inv, client: world.Client = client, r: Rng = r) -> None:
                inv.lines = _lines_for(r, r.amount(client.lo, client.hi))

            _place(inv, out, reroll, reserved)
            out.append(inv)


def _client(name: str) -> world.Client:
    return next(c for c in world.CLIENTS if c.party.name == name)


def _special_sales(rng: Rng, invoices: list[InvoiceData]) -> None:
    by_key = {inv.key: inv for inv in invoices}
    r = rng.stream("special-sales")
    # February: two invoices to the same client, same amount, same week (PROPOSED_MATCH).
    daybreak = _client("Daybreak Café")
    issue = date(YEAR, 2, r.between(2, 4))
    lines = _lines_for(r, r.amount(daybreak.lo, daybreak.hi))
    for key, offset in (("inv-sales-2026-02-01", 0), ("inv-sales-2026-02-02", 3)):
        inv = by_key[key]
        inv.bill_to = daybreak.party
        inv.issue_date = issue + timedelta(days=offset)
        inv.due_date = inv.issue_date + timedelta(days=14)
        inv.lines = list(lines)
    _replace_clients(r, invoices, "2026-02", exclude=daybreak.party.name, keep={"01", "02"})
    # May: one transfer pays two invoices of one client.
    harborview = _client("Harborview Hotel Group")
    for key, day in (
        ("inv-sales-2026-05-02", r.between(2, 4)),
        ("inv-sales-2026-05-03", r.between(5, 8)),
    ):
        inv = by_key[key]
        inv.bill_to = harborview.party
        inv.issue_date = date(YEAR, 5, day)
        inv.due_date = inv.issue_date + timedelta(days=14)
    _replace_clients(r, invoices, "2026-05", exclude=harborview.party.name, keep={"02", "03"})
    # March: Highland Resort & Spa pays net of 2% withholding tax.
    highland = _client("Highland Resort & Spa")
    by_key["inv-sales-2026-03-02"].bill_to = highland.party
    _replace_clients(r, invoices, "2026-03", exclude=highland.party.name, keep={"02"})
    # April: Spice Route Restaurant pays one invoice in two transfers.
    spice = _client("Spice Route Restaurant")
    by_key["inv-sales-2026-04-01"].bill_to = spice.party
    by_key["inv-sales-2026-04-01"].lines = _lines_for(r, r.amount(18_000_000, 26_000_000))
    _replace_clients(r, invoices, "2026-04", exclude=spice.party.name, keep={"01"})


def _replace_clients(
    rng: Rng, invoices: list[InvoiceData], month: str, *, exclude: str, keep: set[str]
) -> None:
    """Give the month's other invoices distinct clients other than `exclude`."""
    others = [
        inv
        for inv in invoices
        if inv.key.startswith(f"inv-sales-{month}-") and inv.key[-2:] not in keep
    ]
    pool = [c for c in world.CLIENTS if c.party.name != exclude]
    for inv, client in zip(others, rng.sample(pool, len(others)), strict=True):
        inv.bill_to = client.party
        inv.lines = _lines_for(rng, rng.amount(client.lo, client.hi))


def _is_feb_pair(a: str, b: str) -> bool:
    return {a, b} == {"inv-sales-2026-02-01", "inv-sales-2026-02-02"}


def _party_of(item: Any) -> str:
    return item.merchant.name if isinstance(item, ReceiptData) else item.party


def _dedupe_totals(
    items: list[Any], total_of: Callable[[Any], Decimal], fixed: tuple[Decimal, ...] = ()
) -> None:
    """No two documents of a kind may be close enough that one could pass for a payment of the
    other (same amount, or for the same party a withholding-sized gap); ambiguity is built only
    where docs/18 §3.6 asks for it. Nor may a document equal a fixed monthly debit. The later one
    gains a unit until they separate."""
    for i, item in enumerate(items):
        while _clashes(total_of(item), list(fixed)) or any(
            _clashes(
                total_of(item),
                [total_of(other)],
                [total_of(other)] if _party_of(other) == _party_of(item) else [],
            )
            for other in items[:i]
            if not _is_feb_pair(other.key, item.key)
        ):
            if isinstance(item, ReceiptData):
                item.items = _bump(item.items)
            else:
                item.lines = _bump(item.lines)


def _separate_special_payments(invoices: list[InvoiceData]) -> None:
    """The net-of-tax payment and the May two-invoice transfer must not fit another invoice."""
    by_key = {inv.key: inv for inv in invoices}
    net = by_key["inv-sales-2026-03-02"]
    others = [inv.total for inv in invoices if inv.key != net.key]
    same = [inv.total for inv in invoices if inv.key != net.key and inv.party == net.party]
    while _clashes(_net_of_withholding(net.total), others, same) or _clashes(net.total, others):
        net.lines = _bump(net.lines)
    first, second = by_key["inv-sales-2026-05-02"], by_key["inv-sales-2026-05-03"]
    rest = [inv.total for inv in invoices if inv.key not in {first.key, second.key}]
    while _clashes(first.total + second.total, rest):
        second.lines = _bump(second.lines)


_SPECIAL_SALES = {
    "inv-sales-2026-02-01",
    "inv-sales-2026-02-02",
    "inv-sales-2026-03-02",
    "inv-sales-2026-04-01",
    "inv-sales-2026-05-02",
    "inv-sales-2026-05-03",
    "inv-sales-2026-06-04",
}


def _sales_payments(rng: Rng, sales: list[InvoiceData]) -> list[_Payment]:
    payments: list[_Payment] = []
    by_key = {inv.key: inv for inv in sales}
    for inv in sales:
        if inv.key in _SPECIAL_SALES:
            continue
        r = rng.stream(inv.key, "payment")
        with_ref = r.chance(0.6)
        # Late only when the description names the invoice, so the match stays automatic.
        pay = inv.due_date + timedelta(days=r.between(-5, 3 if with_ref else 0))
        pay = max(pay, inv.issue_date + timedelta(days=1))
        payments.append(_Payment(pay, inv.total, [inv], with_ref, instant=r.chance(0.3)))

    r = rng.stream("special-payments")
    # February: the reference-less transfer fits both invoices; a later one names the second.
    first, second = by_key["inv-sales-2026-02-01"], by_key["inv-sales-2026-02-02"]
    payments.append(
        _Payment(second.issue_date + timedelta(days=r.between(1, 3)), first.total, [first], False)
    )
    payments.append(
        _Payment(second.due_date - timedelta(days=r.between(0, 2)), second.total, [second], True)
    )
    # March: net of 2% withholding, invoice number in the description.
    net = by_key["inv-sales-2026-03-02"]
    paid_on = net.due_date - timedelta(days=r.between(0, 3))
    payments.append(_Payment(paid_on, _net_of_withholding(net.total), [net], True))
    # April: one invoice in two transfers; neither part may fit another invoice.
    split = by_key["inv-sales-2026-04-01"]
    totals = [inv.total for inv in sales if inv.key != split.key]
    same = [inv.total for inv in sales if inv.key != split.key and inv.party == split.party]
    if extra()[0]:  # spec 024: at volume, only invoices paid in the same weeks can be confused
        near = [
            i
            for i in sales
            if i.key != split.key and abs((i.issue_date - split.issue_date).days) <= 45
        ]
        totals = [i.total for i in near]
        same = [i.total for i in near if i.party == split.party]
    # Shares in tenths of a percent: at volume the whole percents can all be taken.
    shares = (600, 550, 650, 500, 700, 450, 750, 400, 580, 620, 520, 680, *range(300, 801))
    part = next(
        candidate
        for share in shares
        if not _clashes(candidate := _thousands(split.total * share / 1000), totals, same)
        and not _clashes(split.total - candidate, totals, same)
    )
    payments.append(
        _Payment(split.issue_date + timedelta(days=r.between(3, 5)), part, [split], True)
    )
    payments.append(
        _Payment(
            split.due_date - timedelta(days=r.between(0, 2)), split.total - part, [split], True
        )
    )
    # May: one transfer for two invoices, both numbers in the description.
    pair = [by_key["inv-sales-2026-05-02"], by_key["inv-sales-2026-05-03"]]
    paid_on = pair[0].due_date - timedelta(days=r.between(0, 2))
    payments.append(_Payment(paid_on, pair[0].total + pair[1].total, pair, True))
    return payments


# ---------------------------------------------------------------------------- purchases


def purchase_invoice(
    rng: Rng, supplier: world.Supplier, key: str, number: str, issue: date
) -> InvoiceData:
    return InvoiceData(
        key=key,
        kind="PURCHASE",
        number=number,
        issue_date=issue,
        due_date=issue + timedelta(days=30),
        issuer=supplier.party,
        bill_to=world.BUSINESS,
        lines=[Line(d, rng.between(lo, hi), price) for d, price, lo, hi in supplier.products],
        vat_rate=world.VAT_RATE,
        pay_to=supplier.pay_to,
        layout=supplier.layout,
        terms_days=30,
    )


def _purchases(rng: Rng) -> tuple[list[InvoiceData], dict[str, world.Supplier]]:
    out: list[InvoiceData] = []
    supplier_of: dict[str, world.Supplier] = {}
    roastline_no = 41
    for month in MONTHS:
        r = rng.stream(month, "purchases")
        year, mon = month_parts(month)
        schedule = world.SUPPLIER_SCHEDULE[month]
        days = sorted(r.sample(list(range(2, 16)), len(schedule)))
        for seq, (supplier, day) in enumerate(zip(schedule, days, strict=True), 1):
            issue = date(year, mon, day)
            if supplier.code == "gvf":
                number = f"GVF-{YEAR}-{issue:%m%d}"
            elif supplier.code == "primepack":
                number = f"PP/26/{issue:%m}{10 + MONTHS.index(month) + seq:02d}"
            else:
                number = f"RES-{roastline_no:04d}"
                roastline_no += 1
            inv = purchase_invoice(r, supplier, f"inv-purchase-{month}-{seq:02d}", number, issue)
            out.append(inv)
            supplier_of[inv.key] = supplier
    fixed = (world.RENT, world.LOAN_INSTALLMENT, world.INTERNET)
    _dedupe_totals(out, lambda inv: inv.total, fixed)
    # Spec 024: the demo's volume, bills of the same and more suppliers, paid 5 to 12 days later.
    suppliers = [*world.SUPPLIERS, *world.EXTRA_SUPPLIERS]
    for month in MONTHS if extra()[1] else []:
        r = rng.stream(month, "purchases-extra")
        year, mon = month_parts(month)
        # From 05: S4 adds its unknown supplier's bills as -03 and -04 (docs/18 §3.6, T13).
        first = max(len(world.SUPPLIER_SCHEDULE[month]), 4) + 1
        for seq in range(first, first + extra()[1]):
            supplier = r.choice(suppliers)
            issue = date(year, mon, r.between(2, 16))
            if supplier.code == "gvf":
                number = f"GVF-{YEAR}-{issue:%m%d}-{seq:02d}"
            elif supplier.code == "primepack":
                number = f"PP/26/{issue:%m}{50 + seq:02d}"
            elif supplier.code == "roastline":
                number = f"RES-{500 + MONTHS.index(month) * 100 + seq:04d}"
            else:
                number = f"{supplier.code.upper()}/{issue:%Y/%m}/{seq:03d}"  # moved by the shift
            key = f"inv-purchase-{month}-{seq:02d}"
            inv = purchase_invoice(r, supplier, key, number, issue)

            def reroll(
                inv: InvoiceData = inv, supplier: world.Supplier = supplier, r: Rng = r
            ) -> None:
                inv.lines = [
                    Line(d, r.between(lo, hi), price) for d, price, lo, hi in supplier.products
                ]

            _place(inv, out, reroll, list(fixed))
            out.append(inv)
            supplier_of[inv.key] = supplier
    return out, supplier_of


def purchase_payment(rng: Rng, inv: InvoiceData) -> date:
    return inv.issue_date + timedelta(days=rng.stream(inv.key, "payment").between(5, 12))


# ---------------------------------------------------------------------------- receipts


def _receipts(rng: Rng) -> list[ReceiptData]:
    out: list[ReceiptData] = []
    for month in MONTHS:
        r = rng.stream(month, "receipts")
        year, mon = month_parts(month)
        cash_slot = r.between(0, 3) if r.between(0, 1) else -1
        for i, day in enumerate(sorted(r.sample(list(range(2, 28)), 4))):
            merchant = r.choice(world.MERCHANTS)
            description, price, lo, hi = r.choice(list(merchant.items))
            form = "pdf" if i == 1 else "jpeg"
            if i == cash_slot:
                payment = "CASH"
            elif form == "pdf" or r.chance(0.3):
                payment = "QRIS"
            else:
                payment = "DEBIT CARD ••4821"
            issued = datetime(year, mon, day, r.between(8, 18), r.between(0, 59))
            initials = "".join(word[0] for word in merchant.party.name.split())
            out.append(
                ReceiptData(
                    key=f"receipt-{month}-{i + 1:02d}",
                    merchant=merchant.party,
                    issued_at=issued,
                    items=[Line(description, r.between(lo, hi), price)],
                    vat_rate=world.VAT_RATE,
                    payment=payment,
                    form=form,
                    expense_account=merchant.account,
                    receipt_no=f"{initials}-{issued:%m%d}-{r.between(100, 999)}",
                )
            )
    _dedupe_totals(out, lambda rec: rec.total)
    # Spec 024: the demo's volume, half photos and half PDFs, mostly paid by card or QRIS.
    for month in MONTHS if extra()[2] else []:
        r = rng.stream(month, "receipts-extra")
        year, mon = month_parts(month)
        for i in range(4, 4 + extra()[2]):
            merchant = r.choice(world.MERCHANTS)
            description, price, lo, hi = r.choice(list(merchant.items))
            issued = datetime(year, mon, r.between(2, 27), r.between(8, 18), r.between(0, 59))
            initials = "".join(word[0] for word in merchant.party.name.split())
            rec = ReceiptData(
                key=f"receipt-{month}-{i + 1:02d}",
                merchant=merchant.party,
                issued_at=issued,
                items=[Line(description, r.between(lo, hi), price)],
                vat_rate=world.VAT_RATE,
                payment=r.choice(["QRIS", "DEBIT CARD ••4821", "DEBIT CARD ••4821", "CASH"]),
                form="pdf" if i % 2 else "jpeg",
                expense_account=merchant.account,
                receipt_no=f"{initials}-{issued:%m%d}-{r.between(100, 999)}",
            )

            def reroll(
                rec: ReceiptData = rec, merchant: world.Merchant = merchant, r: Rng = r
            ) -> None:
                d, p_, lo_, hi_ = r.choice(list(merchant.items))
                rec.items = [Line(d, r.between(lo_, hi_), p_)]

            _place(rec, out, reroll, [], whole_party=False)
            out.append(rec)
    return out


# ---------------------------------------------------------------------------- bank lines


def bank_name(name: str) -> str:
    """How a bank prints a party: upper case, no accents, no dots ("DAYBREAK CAFE")."""
    folded = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return folded.upper().replace(".", "")


def supplier_payment_row(inv: InvoiceData, paid_on: date, category: str) -> BankRow:
    return BankRow(
        "",
        paid_on,
        f"TRANSFER OUT {bank_name(inv.issuer.name)} {inv.pay_to.account_number[-4:]}",
        "supplier",
        category,
        debit=inv.total,
        party=inv.issuer.name,
        documents=[inv.key],
    )


def _bank_rows(
    rng: Rng,
    sales: list[InvoiceData],
    purchases: list[InvoiceData],
    receipts: list[ReceiptData],
    supplier_of: dict[str, world.Supplier],
) -> dict[str, list[BankRow]]:
    rows: dict[str, list[BankRow]] = {m: [] for m in MONTHS}

    def add(row: BankRow) -> None:
        rows[f"{row.date:%Y-%m}"].append(row)

    for p in _sales_payments(rng, sales):
        client = bank_name(p.invoices[0].bill_to.name)
        refs = " ".join(inv.number for inv in p.invoices) if p.with_ref else ""
        prefix = "INSTANT TRANSFER IN" if p.instant else "TRANSFER IN"
        add(
            BankRow(
                "",
                p.date,
                f"{prefix} {client} {refs}".strip(),
                "sale",
                "SALES_RECEIPT",
                credit=p.amount,
                party=p.invoices[0].bill_to.name,
                documents=[inv.key for inv in p.invoices],
                invoice_refs=[inv.number for inv in p.invoices] if p.with_ref else [],
            )
        )
    for inv in purchases:
        category = supplier_of[inv.key].category
        add(supplier_payment_row(inv, purchase_payment(rng, inv), category))
    for rec in receipts:
        if rec.payment == "CASH":
            continue
        channel = "QRIS" if rec.payment == "QRIS" else "DEBIT CARD"
        description = f"{channel} {bank_name(rec.merchant.name)}"
        add(
            BankRow(
                "",
                rec.date,
                description,
                "card",
                "OTHER_OPERATING_EXPENSE",
                debit=rec.total,
                party=rec.merchant.name,
                documents=[rec.key],
            )
        )
    for month in MONTHS:
        _fixed_rows(rng.stream(month, "fixed"), month, add)
        _deposits(rng.stream(month, "deposits"), month, add)
    dedupe_bank(rows)
    return rows


def _fixed_rows(r: Rng, month: str, add: Callable[[BankRow], None]) -> None:
    year, mon = month_parts(month)
    abbr, prev = MONTH_ABBR[mon - 1], MONTH_ABBR[(mon - 2) % 12]
    add(BankRow("", date(year, mon, 1), f"WAREHOUSE RENT {abbr}", "rent", "RENT", debit=world.RENT))
    add(
        BankRow(
            "",
            date(year, mon, 5),
            f"LOAN INSTALLMENT {world.LOAN_REF}",
            "loan",
            "LOAN_REPAYMENT",
            debit=world.LOAN_INSTALLMENT,
            party=world.BANK_NAME,
        )
    )
    add(
        BankRow(
            "",
            r.day(year, mon, 9, 11),
            f"VAT PAYMENT {prev}",
            "vat",
            "TAX_PAYMENT",
            debit=r.amount(3_500_000, 7_500_000),
        )
    )
    add(
        BankRow(
            "",
            date(year, mon, 12),
            "INTERNET BILL 0227814455",
            "utility",
            "UTILITIES",
            debit=world.INTERNET,
        )
    )
    add(
        BankRow(
            "",
            r.day(year, mon, 14, 16),
            "WATER BILL 4471-0938",
            "utility",
            "UTILITIES",
            debit=r.amount(280_000, 520_000),
        )
    )
    add(
        BankRow(
            "",
            r.day(year, mon, 18, 20),
            "ELECTRICITY BILL 532110987421",
            "utility",
            "UTILITIES",
            debit=r.amount(1_900_000, 3_200_000),
        )
    )
    add(
        BankRow(
            "",
            date(year, mon, 25),
            f"PAYROLL {abbr}",
            "payroll",
            "PAYROLL",
            debit=r.amount(38_000_000, 46_000_000, 50_000),
        )
    )
    for _ in range(r.between(1, 2)):
        add(
            BankRow(
                "",
                r.day(year, mon, 6, 27),
                f"TRANSFER OUT {bank_name(world.PARTNER)}",
                "drawing",
                "OWNER_DRAWING",
                debit=r.amount(3_000_000, 8_000_000, 500_000),
                party=world.PARTNER,
            )
        )
    add(BankRow("", _month_end(month), "ADMIN FEE", "fee", "BANK_FEES", debit=world.ADMIN_FEE))


def _deposits(r: Rng, month: str, add: Callable[[BankRow], None]) -> None:
    year, mon = month_parts(month)
    for day in sorted(r.sample(list(range(2, 29)), r.between(4, 8))):
        if (mon, day) in {(3, 14), (6, 21)}:
            continue
        add(
            BankRow(
                "",
                date(year, mon, day),
                "CASH DEPOSIT",
                "deposit",
                "SALES_RECEIPT",
                credit=r.amount(800_000, 4_500_000, 50_000),
            )
        )
    if month == "2026-03":
        # The row T1 edits in S2 (docs/18 §3.6).
        add(
            BankRow(
                "",
                world.T1_ANCHOR_DATE,
                "CASH DEPOSIT",
                "deposit",
                "SALES_RECEIPT",
                credit=world.T1_ANCHOR_AMOUNT,
            )
        )
    if month == "2026-06":
        # Deposited but never booked: UNMATCHED_BANK_LINE and X09 (docs/18 §3.6).
        add(
            BankRow(
                "",
                date(year, mon, 21),
                "CASH DEPOSIT",
                "deposit",
                "SALES_RECEIPT",
                credit=r.amount(800_000, 4_500_000, 50_000),
                in_ledger=False,
            )
        )


# Lines without a document can move; the T1 anchor and the fixed internet bill cannot.
_ADJUSTABLE = {"deposit", "drawing", "payroll", "vat", "utility"}
_WINDOW_DAYS = 6  # bank lines and their ledger entries (posted up to 2 days later) stay apart


def _movable(row: BankRow) -> bool:
    if row.flow == "deposit" and row.date == world.T1_ANCHOR_DATE:
        return False
    if row.flow == "utility" and row.description.startswith("INTERNET"):
        return False
    return row.flow in _ADJUSTABLE


def dedupe_bank(rows: dict[str, list[BankRow]]) -> None:
    """Lines of one direction within a few days never share an amount within tolerance, so every
    bank line has exactly one ledger candidate. Only lines without documents move."""
    every = sorted((r for month in rows.values() for r in month), key=lambda r: r.date)
    reserved = {world.T1_ANCHOR_AMOUNT, world.T1_EDITED_AMOUNT}
    for row in every:
        # The values T1 swaps appear nowhere else, so the edit is unambiguous on the page.
        while _movable(row) and row.amount in reserved:
            _shift(row)
    for i, row in enumerate(every):
        while True:
            clash = next(
                (
                    other
                    for other in every[:i]
                    if other.direction == row.direction
                    and abs((other.date - row.date).days) <= _WINDOW_DAYS
                    and _same(other.amount, row.amount)
                ),
                None,
            )
            if clash is None:
                break
            target = row if _movable(row) else clash
            if not _movable(target):
                raise ValueError(f"cannot separate {clash.description} and {row.description}")
            _shift(target)


def _shift(row: BankRow) -> None:
    step = Decimal("37000.00") if row.flow in {"vat", "utility"} else Decimal("50000.00")
    if row.credit is not None:
        row.credit += step
    else:
        row.debit = (row.debit or ZERO) + step


# ---------------------------------------------------------------------------- statements


def build_statements(opening: Decimal, rows: dict[str, list[BankRow]]) -> dict[str, StatementData]:
    statements: dict[str, StatementData] = {}
    balance = opening
    for month in MONTHS:
        year, mon = month_parts(month)
        ordered = sorted(rows[month], key=lambda r: (r.date, 0 if r.flow == "rent" else 1))
        month_opening = balance
        for index, row in enumerate(ordered, 1):
            row.row_index = index
            row.key = f"st-{month[5:]}#{index}"
            balance = balance + (row.credit or ZERO) - (row.debit or ZERO)
            row.balance = balance
            if balance < Decimal("1000000"):
                raise ValueError(f"balance too low on {row.date}: {balance}")
        end = _month_end(month)
        statements[month] = StatementData(
            month=month,
            period_start=date(year, mon, 1),
            period_end=end,
            opening=month_opening,
            rows=ordered,
            created_at=datetime(end.year, end.month, end.day, 2, 0) + timedelta(days=1),
            account_number=world.ACCOUNT,
            holder=world.HOLDER,
            holder_address=list(world.BUSINESS.address),
            bank_name=world.BANK_NAME,
            branch=world.BRANCH,
        )
    return statements


# ---------------------------------------------------------------------------- ledger


class _Journals:
    def __init__(self) -> None:
        self.counters: dict[tuple[str, str], int] = {}

    def next(self, prefix: str, d: date) -> str:
        key = (prefix, f"{d:%Y-%m}")
        self.counters[key] = self.counters.get(key, 0) + 1
        return f"{prefix}-{d:%Y-%m}-{self.counters[key]:03d}"


def _entry(
    d: date,
    journal: str,
    account: str,
    description: str,
    reference: str,
    *,
    debit: Decimal | None = None,
    credit: Decimal | None = None,
    bank_key: str | None = None,
    document_key: str | None = None,
) -> LedgerRow:
    return LedgerRow(
        d,
        journal,
        account,
        world.ACCOUNTS[account],
        description,
        reference,
        debit=money(debit) if debit is not None else None,
        credit=money(credit) if credit is not None else None,
        bank_key=bank_key,
        document_key=document_key,
    )


def build_ledger(
    rng: Rng,
    statements: dict[str, StatementData],
    sales: list[InvoiceData],
    purchases: list[InvoiceData],
    receipts: list[ReceiptData],
    expense_account_of: dict[str, str],
) -> list[LedgerRow]:
    out: list[LedgerRow] = []
    journals = _Journals()
    invoices = {d.key: d for d in [*sales, *purchases]}
    receipt_of = {r.key: r for r in receipts}

    for inv in sales:
        j = journals.next("SJ", inv.issue_date)
        desc, ref, d = f"Invoice - {inv.bill_to.name}", inv.number, inv.issue_date
        out += [
            _entry(d, j, "1200", desc, ref, debit=inv.total, document_key=inv.key),
            _entry(d, j, "4000", desc, ref, credit=inv.subtotal),
            _entry(d, j, "2200", desc, ref, credit=inv.vat),
        ]
    for inv in purchases:
        j = journals.next("PJ", inv.issue_date)
        desc, ref, d = f"Bill - {inv.issuer.name}", inv.number, inv.issue_date
        out += [
            _entry(d, j, expense_account_of[inv.key], desc, ref, debit=inv.subtotal),
            _entry(d, j, "1400", desc, ref, debit=inv.vat),
            _entry(d, j, "2100", desc, ref, credit=inv.total, document_key=inv.key),
        ]
    for rec in receipts:
        if rec.payment != "CASH":
            continue
        j = journals.next("PC", rec.date)
        desc = f"{world.ACCOUNTS[rec.expense_account]} - {rec.merchant.name}"
        out += [
            _entry(
                rec.date,
                j,
                rec.expense_account,
                desc,
                rec.receipt_no,
                debit=rec.total,
                document_key=rec.key,
            ),
            _entry(rec.date, j, "1000", desc, rec.receipt_no, credit=rec.total),
        ]

    for st in statements.values():
        for row in st.rows:
            if not row.in_ledger:
                continue
            r = rng.stream(row.key, "ledger")
            lag = r.between(0, 1) if row.flow == "sale" else r.between(0, 2)
            posted = min(row.date + timedelta(days=lag), st.period_end)
            j = journals.next("BNK", posted)
            out += _bank_entries(r, row, posted, j, invoices, receipt_of)

    out.sort(key=lambda e: (e.date, e.journal))
    for n, entry in enumerate(out, 1):
        entry.key = f"lg#{n}"
    return out


def _bank_entries(
    r: Rng,
    row: BankRow,
    d: date,
    j: str,
    invoices: dict[str, InvoiceData],
    receipt_of: dict[str, ReceiptData],
) -> list[LedgerRow]:
    month_name = f"{MONTH_NAME[row.date.month - 1]} {row.date.year}"
    cash = row.key
    if row.flow == "sale":
        paid = [invoices[k] for k in row.documents]
        ref = " ".join(inv.number for inv in paid) if r.chance(0.7) else ""
        desc = f"Receipt - {paid[0].bill_to.name}"
        lines = [_entry(d, j, "1110", desc, ref, debit=row.credit, bank_key=cash)]
        if len(paid) > 1:
            return lines + [
                _entry(d, j, "1200", desc, inv.number, credit=inv.total) for inv in paid
            ]
        total = paid[0].total
        received = row.credit or ZERO
        if total * Decimal("0.98") <= received < total - amount_tolerance(total):
            withheld = total - received
            return lines + [
                _entry(d, j, "1300", desc, ref, debit=withheld),
                _entry(d, j, "1200", desc, ref, credit=total),
            ]
        return lines + [_entry(d, j, "1200", desc, ref, credit=received)]
    if row.flow == "deposit":
        return [
            _entry(d, j, "1110", "Cash sales deposit", "", debit=row.credit, bank_key=cash),
            _entry(d, j, "4100", "Cash sales deposit", "", credit=row.credit),
        ]
    amount = row.debit
    if row.flow == "supplier":
        inv = invoices[row.documents[0]]
        ref = inv.number if r.chance(0.7) else ""
        desc = f"Payment - {inv.issuer.name}"
        return [
            _entry(d, j, "2100", desc, ref, debit=amount),
            _entry(d, j, "1110", desc, ref, credit=amount, bank_key=cash),
        ]
    if row.flow == "card":
        rec = receipt_of[row.documents[0]]
        ref = rec.receipt_no if r.chance(0.7) else ""
        desc = f"{world.ACCOUNTS[rec.expense_account]} - {rec.merchant.name}"
        return [
            _entry(d, j, rec.expense_account, desc, ref, debit=amount, document_key=rec.key),
            _entry(d, j, "1110", desc, ref, credit=amount, bank_key=cash),
        ]
    if row.flow == "loan":
        desc, ref = f"Loan installment {month_name}", world.LOAN_REF
        principal = (amount or ZERO) - world.LOAN_INTEREST
        return [
            _entry(d, j, "2300", desc, ref, debit=principal),
            _entry(d, j, "7100", desc, ref, debit=world.LOAN_INTEREST),
            _entry(d, j, "1110", desc, ref, credit=amount, bank_key=cash),
        ]
    previous = MONTH_NAME[(row.date.month - 2) % 12]
    account, desc, ref = {
        "payroll": ("6000", f"Payroll {month_name}", f"PAY-{row.date:%Y-%m}"),
        "rent": ("6050", f"Warehouse rent {month_name}", ""),
        "vat": ("2200", f"VAT payment {previous}", ""),
        "drawing": ("3100", f"Owner drawing - {world.PARTNER}", ""),
        "fee": ("6900", f"Bank admin fee {month_name}", ""),
        "utility": ("6150", f"{row.description.split()[0].capitalize()} {month_name}", ""),
    }[row.flow]
    return [
        _entry(d, j, account, desc, ref, debit=amount),
        _entry(d, j, "1110", desc, ref, credit=amount, bank_key=cash),
    ]


# ---------------------------------------------------------------------------- entry point


def opening_balance(rng: Rng, rows: dict[str, list[BankRow]]) -> Decimal:
    """The January opening, large enough that the account never dips below IDR 20 million (S1 has
    no negative or near-empty days; those belong to the gambling-and-returns fixture)."""
    running, lowest = ZERO, ZERO
    for month in MONTHS:
        for row in sorted(rows[month], key=lambda r: (r.date, 0 if r.flow == "rent" else 1)):
            running += (row.credit or ZERO) - (row.debit or ZERO)
            lowest = min(lowest, running)
    cushion = ((-lowest + Decimal("20000000")) / 1_000_000).to_integral_value(
        ROUND_CEILING
    ) * 1_000_000
    base = world.OPENING_JANUARY + rng.stream("opening").amount(0, 8_000_000, 50_000)
    return max(base, cushion.quantize(Decimal("0.01")))


def generate_books(seed: int) -> Books:
    """The S1 books for `seed`; scenarios S2–S6 start from these (docs/18 §5)."""
    rng = Rng(seed)
    sales = _sales(rng)
    purchases, supplier_of = _purchases(rng)
    receipts = _receipts(rng)
    rows = _bank_rows(rng, sales, purchases, receipts, supplier_of)
    statements = build_statements(opening_balance(rng, rows), rows)
    expense_of = {key: s.expense_account for key, s in supplier_of.items()}
    ledger = build_ledger(rng, statements, sales, purchases, receipts, expense_of)
    books = Books(seed, statements, sales, purchases, receipts, ledger)
    books.matches = intended_matches(books)
    return books
