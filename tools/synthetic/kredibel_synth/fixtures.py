"""The fixtures of docs/18 §3.7 (AC-002-15).

Small folders, each with its own truth.json, for the checks the five scenarios do not reach.
"""

import copy
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from . import world
from .books import generate_books
from .model import ZERO, BankRow, StatementData
from .render_invoice import render_invoice
from .render_ledger import render_ledger_csv, render_ledger_xlsx
from .render_statement import render_statement, statement_file
from .tamper import EDITOR_PRODUCER, cover_amount, strip_unicode_maps
from .truth import workspace_as_onboarded


@dataclass
class Fixture:
    name: str
    description: str
    files: dict[str, bytes] = field(default_factory=dict)
    expected: dict[str, Any] = field(default_factory=dict)
    documents: list[dict[str, Any]] = field(default_factory=list)

    def truth(self) -> dict[str, Any]:
        return {
            "fixture": self.name,
            "description": self.description,
            "watermark": world.WATERMARK,
            "workspace": workspace_as_onboarded(),
            "files": sorted(self.files),
            "documents": self.documents,
            "expected": self.expected,
        }


def _restate(st: StatementData, rows: list[BankRow], opening: Decimal) -> StatementData:
    """A statement with these rows from this opening; balances, keys and indexes recomputed."""
    out = copy.copy(st)
    out.opening = opening
    out.rows = []
    balance = opening
    for index, row in enumerate(sorted(rows, key=lambda r: r.date), 1):
        new = copy.copy(row)
        new.row_index = index
        new.key = f"st-{st.month[5:]}#{index}"
        balance = balance + (new.credit or ZERO) - (new.debit or ZERO)
        new.balance = balance
        out.rows.append(new)
    return out


def _doc(st: StatementData) -> dict[str, Any]:
    return {
        "file": statement_file(st.month),
        "accountNumber": st.account_number,
        "holder": st.holder,
        "period": {"start": st.period_start.isoformat(), "end": st.period_end.isoformat()},
        "opening": f"{st.opening:.2f}",
        "closing": f"{st.closing:.2f}",
        "rows": [
            {
                "key": r.key,
                "date": r.date.isoformat(),
                "description": r.description,
                "debit": None if r.debit is None else f"{r.debit:.2f}",
                "credit": None if r.credit is None else f"{r.credit:.2f}",
                "balance": f"{r.balance:.2f}",
                "riskTags": r.risk_tags,
            }
            for r in st.rows
        ],
    }


def build_fixtures(seed: int = 1) -> list[Fixture]:
    books = generate_books(seed)
    march, april, may = (books.statements[m] for m in ("2026-03", "2026-04", "2026-05"))
    return [
        _undeclared_account(march),
        _holder_mismatch(march),
        _regenerated_statement(april, may),
        _double_payment(books, march),
        _whiteout_overlay(march),
        _cid_glyphs(march),
        _gambling_and_returns(april),
        _ledger_xlsx(books),
    ]


def _undeclared_account(march: StatementData) -> Fixture:
    st = copy.copy(march)
    st.account_number = world.SECOND_ACCOUNT
    rows = [
        BankRow(
            "",
            date(2026, 3, 3),
            "TRANSFER IN SUNRISE COFFEE ROASTERS 4821",
            "deposit",
            "INTERNAL_TRANSFER",
            credit=Decimal("15000000.00"),
            party=world.BUSINESS.name,
        ),
        BankRow(
            "",
            date(2026, 3, 12),
            "CASH DEPOSIT",
            "deposit",
            "SALES_RECEIPT",
            credit=Decimal("2350000.00"),
        ),
        BankRow(
            "",
            date(2026, 3, 20),
            "DEBIT CARD LOTUS HARDWARE",
            "card",
            "OTHER_OPERATING_EXPENSE",
            debit=Decimal("412500.00"),
        ),
        BankRow("", date(2026, 3, 31), "ADMIN FEE", "fee", "BANK_FEES", debit=world.ADMIN_FEE),
    ]
    st = _restate(st, rows, Decimal("12500000.00"))
    fx = Fixture(
        "undeclared-account", "One month from a second ACB account held by Sunrise, never declared."
    )
    fx.files[statement_file(st.month)] = render_statement(st).pdf
    fx.documents.append(_doc(st))
    fx.expected = {
        "findingsP0": ["X06_UNDECLARED_ACCOUNT"],
        "suggestions": [
            {
                "field": "BANK_ACCOUNT",
                "confidence": "HIGH",
                "value": {
                    "bankName": world.BANK_NAME,
                    "accountNumber": world.SECOND_ACCOUNT,
                    "holderName": world.HOLDER,
                },
            }
        ],
    }
    return fx


def _holder_mismatch(march: StatementData) -> Fixture:
    st = copy.copy(march)
    st.holder = "SUNRISE TRADING PARTNERS"
    st.holder_address = ["7 Harbour Lane", "Cirebon 45111"]
    fx = Fixture("holder-mismatch", "A statement for the declared account held by another name.")
    fx.files[statement_file(st.month)] = render_statement(st).pdf
    fx.documents.append(_doc(st))
    fx.expected = {"findingsP0": ["X05_ACCOUNT_HOLDER_MISMATCH"], "riskLevel": "HIGH"}
    return fx


def _regenerated_statement(april: StatementData, may: StatementData) -> Fixture:
    rows = []
    for row in may.rows:
        new = copy.copy(row)
        if new.credit is not None:
            new.credit = (new.credit * Decimal("1.6")).quantize(Decimal("1"))
            new.credit = new.credit.quantize(Decimal("0.01"))
        rows.append(new)
    wrong_opening = april.closing + Decimal("23400000.00")
    fake = _restate(may, rows, wrong_opening)
    fx = Fixture(
        "regenerated-statement",
        "May rebuilt in an editor: credits x1.6, balances consistent, opening not April's closing.",
    )
    fx.files[statement_file(april.month)] = render_statement(april).pdf
    fx.files[statement_file(fake.month)] = render_statement(fake, producer=EDITOR_PRODUCER).pdf
    fx.documents += [_doc(april), _doc(fake)]
    fx.expected = {
        "findingsP0": ["X01_STATEMENT_DISCONTINUITY", "M01_EDITING_SOFTWARE_PRODUCER"],
        "absent": ["A01_RUNNING_BALANCE_BREAK", "A02_OPENING_CLOSING_MISMATCH"],
        "anchoredTo": statement_file(fake.month),
    }
    return fx


def _double_payment(books, march: StatementData) -> Fixture:
    inv = next(
        i
        for i in books.purchases
        if i.issuer == world.GREEN_VALLEY.party and i.key[13:20] == "2026-03"
    )
    first = next(r for r in march.rows if r.documents == [inv.key])
    second = copy.copy(first)
    second.date = first.date + timedelta(days=6)
    st = _restate(march, [*march.rows, second], march.opening)
    fx = Fixture(
        "double-payment", f"Green Valley Farms' invoice {inv.number} paid twice, 6 days apart."
    )
    fx.files[statement_file(st.month)] = render_statement(st).pdf
    fx.files[inv.file] = render_invoice(inv)
    fx.documents.append(_doc(st))
    fx.expected = {
        "findingsP0": ["D07_DOUBLE_PAYMENT"],
        "riskLevel": "HIGH",
        "invoice": inv.number,
        "reviewItems": {"POSSIBLE_DUPLICATE": 1},
    }
    return fx


def _whiteout_overlay(march: StatementData) -> Fixture:
    rendered = render_statement(march)
    target = next(r for r in march.rows if r.flow == "deposit" and r.date != world.T1_ANCHOR_DATE)
    placed = next(p for p in rendered.amounts[target.key] if p.field == "credit")
    new_value = (target.credit or ZERO) + Decimal("5000000.00")
    fx = Fixture(
        "whiteout-overlay", "One credit covered by a white rectangle with a new value drawn on top."
    )
    fx.files[statement_file(march.month)] = cover_amount(rendered.pdf, placed, new_value)
    fx.documents.append(_doc(march))
    fx.expected = {
        "rowKey": target.key,
        "underneath": placed.text,
        "drawnOnTop": f"{new_value:,.2f}",
        "verifier": "CONFLICT",
        "findingsP1": ["M05_COVERED_TEXT"],
    }
    return fx


def _cid_glyphs(march: StatementData) -> Fixture:
    fx = Fixture(
        "cid-glyphs", "A statement whose fonts carry no Unicode map: the text layer is unusable."
    )
    fx.files[statement_file(march.month)] = strip_unicode_maps(render_statement(march).pdf)
    fx.documents.append(_doc(march))
    fx.expected = {"triage": "UNUSABLE", "witness": "OCR"}
    return fx


def _gambling_and_returns(april: StatementData) -> Fixture:
    rows = [copy.copy(r) for r in april.rows]
    extra = [
        (6, "JACKPOT ARENA TOPUP", "debit", "3500000.00", ["GAMBLING"]),
        (13, "JACKPOT ARENA TOPUP", "debit", "5000000.00", ["GAMBLING"]),
        (22, "JACKPOT ARENA TOPUP", "debit", "4200000.00", ["GAMBLING"]),
        (8, "RETURNED TRANSFER HILLSIDE COFFEE BAR", "debit", "9800000.00", ["RETURNED_ITEM"]),
        (15, "RETURNED ITEM CHQ 004512", "debit", "6400000.00", ["RETURNED_ITEM"]),
        (24, "RETURNED TRANSFER SOUVENIR CORNER", "debit", "7300000.00", ["RETURNED_ITEM"]),
    ]
    for day, text, _side, amount, tags in extra:
        category = "OWNER_DRAWING" if "JACKPOT" in text else "REVERSAL"
        rows.append(
            BankRow(
                "", date(2026, 4, day), text, "fee", category, debit=Decimal(amount), risk_tags=tags
            )
        )
    # The opening, in steps of 250,000, nearest zero that leaves exactly four days below zero.
    candidates = (Decimal(250_000 * k) for k in sorted(range(-400, 401), key=abs))
    st = next(
        s for opening in candidates if _negative_days(s := _restate(april, rows, opening + 0)) == 4
    )
    fx = Fixture(
        "gambling-and-returns",
        "Gambling top-ups, three returned items and four negative-balance days.",
    )
    fx.files[statement_file(st.month)] = render_statement(st).pdf
    fx.documents.append(_doc(st))
    fx.expected = {
        "findingsP0": [
            "B01_GAMBLING_INDICATORS",
            "B04_RETURNED_ITEMS",
            "C02_NEGATIVE_BALANCE_DAYS",
        ],
        "severities": {
            "B01_GAMBLING_INDICATORS": "MEDIUM",
            "B04_RETURNED_ITEMS": "HIGH",
            "C02_NEGATIVE_BALANCE_DAYS": "MEDIUM",
        },
        "negativeDays": 4,
    }
    return fx


def _negative_days(st: StatementData) -> int:
    end_of_day: dict[date, Decimal] = {}
    for row in st.rows:
        end_of_day[row.date] = row.balance
    return sum(1 for value in end_of_day.values() if value < 0)


def _ledger_xlsx(books) -> Fixture:
    fx = Fixture(
        "ledger-xlsx", "The ledger as XLSX with another header and one signed amount column."
    )
    fx.files["ledger-2026-H1.xlsx"] = render_ledger_xlsx(books.ledger)
    fx.files["ledger-2026-H1.csv"] = render_ledger_csv(books.ledger)
    fx.expected = {
        "mapping": {
            "date": "Posting date",
            "account": "Acct",
            "description": "Narration",
            "reference": "Ref",
            "amount": "Amount",
            "sign": "debit positive, credit negative",
            "dateFormat": "dd/mm/yyyy",
        },
        "sameEntriesAs": "ledger-2026-H1.csv",
        "entries": len(books.ledger),
    }
    return fx
