"""Intended matches and what the reconciliation should conclude about them (docs/18 §3.6, AC-002-7).

The scorer is docs/08 §6.3 with the numbers of `contracts/policy/reconciliation.v1.yaml`, so every
`AUTO` in `truth.json` is unambiguous and every `PROPOSED` is ambiguous under the policy the engine
uses; a policy change that would flip an expectation fails `tests/test_matching_cases.py` first.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from .model import BankRow, Expect, IntendedMatch, InvoiceData, LedgerRow, MatchKind, ReceiptData

if TYPE_CHECKING:
    from .model import Books

POLICY_FILE = (
    Path(__file__).resolve().parents[3] / "contracts" / "policy" / "reconciliation.v1.yaml"
)


@dataclass(frozen=True)
class Policy:
    min_tolerance: Decimal
    share_tolerance: Decimal
    max_withholding: Decimal
    before_issue_days: int
    grace_days: int
    receipt_days: int
    ledger_days: int
    w_amount: Decimal
    w_party: Decimal
    w_reference: Decimal
    w_date: Decimal
    auto: Decimal
    margin: Decimal
    propose: Decimal


@cache
def policy() -> Policy:
    raw: dict[str, Any] = yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8"))
    w, t, win = raw["weights"], raw["thresholds"], raw["windows"]
    return Policy(
        min_tolerance=Decimal(raw["amountTolerance"]["minMinor"]) / 100,
        share_tolerance=Decimal(raw["amountTolerance"]["share"]),
        max_withholding=Decimal(raw["maxWithholding"]),
        before_issue_days=win["invoiceBeforeIssueDays"],
        grace_days=win["graceDays"],
        receipt_days=win["receiptDays"],
        ledger_days=win["ledgerDays"],
        w_amount=Decimal(w["amount"]),
        w_party=Decimal(w["party"]),
        w_reference=Decimal(w["reference"]),
        w_date=Decimal(w["date"]),
        auto=Decimal(t["autoConfirmScore"]),
        margin=Decimal(t["ambiguityMargin"]),
        propose=Decimal(t["proposeScore"]),
    )


def amount_tolerance(amount: Decimal) -> Decimal:
    p = policy()
    return max(p.min_tolerance, abs(amount) * p.share_tolerance)


def _tokens(text: str) -> set[str]:
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().upper()
    return set(re.findall(r"[A-Z0-9]+", folded))


def party_score(party: str, description: str) -> Decimal:
    """token_set_ratio when one side's tokens contain the other's is 100; otherwise this share of
    shared tokens is a lower bound good enough to rank rivals that already differ in amount."""
    mine, theirs = _tokens(party), _tokens(description)
    if not mine:
        return Decimal(0)
    if mine <= theirs:
        return Decimal(1)
    return (Decimal(len(mine & theirs)) / len(mine)).quantize(Decimal("0.01"))


def amount_score(paid: Decimal, total: Decimal) -> tuple[Decimal, str | None]:
    if abs(paid - total) <= amount_tolerance(total):
        return Decimal(1), "AMOUNT_EXACT"
    if total * (1 - policy().max_withholding) <= paid < total:
        return Decimal("0.8"), "NET_OF_TAX"
    return Decimal(0), None


def _invoice_date_score(paid_on: date, inv: InvoiceData) -> Decimal | None:
    """None outside the window [issue − 3, due + grace]; distance counts days after the due date."""
    p = policy()
    if (inv.issue_date - paid_on).days > p.before_issue_days:
        return None
    late = (paid_on - inv.due_date).days
    if late > p.grace_days:
        return None
    return 1 - min(Decimal(1), Decimal(max(0, late)) / p.grace_days)


def _near_date_score(a: date, b: date, window: int) -> Decimal | None:
    distance = abs((a - b).days)
    if distance > window:
        return None
    return 1 - min(Decimal(1), Decimal(distance) / window)


@dataclass(frozen=True)
class Scored:
    score: Decimal
    reasons: tuple[str, ...]


def score_invoice(row: BankRow, inv: InvoiceData, paid: Decimal | None = None) -> Scored | None:
    """A bank line (or the sum of a split) against one invoice; None when outside the window."""
    p = policy()
    date_score = _invoice_date_score(row.date, inv)
    if date_score is None:
        return None
    amount, amount_reason = amount_score(paid if paid is not None else row.amount, inv.total)
    party = party_score(inv.party, row.description)
    reference = Decimal(1) if inv.number in row.description else Decimal(0)
    total = (
        p.w_amount * amount + p.w_party * party + p.w_reference * reference + p.w_date * date_score
    )
    reasons = [r for r in (amount_reason,) if r]
    if party >= Decimal("0.8"):
        reasons.append("PARTY_MATCH")
    if reference:
        reasons.append("REFERENCE_IN_TEXT")
    if date_score >= Decimal("0.9"):
        reasons.append("DATE_NEAR")
    return Scored(total.quantize(Decimal("0.001")), tuple(reasons))


def score_receipt(row: BankRow, rec: ReceiptData) -> Scored | None:
    p = policy()
    date_score = _near_date_score(row.date, rec.date, p.receipt_days)
    if date_score is None:
        return None
    amount, amount_reason = amount_score(row.amount, rec.total)
    party = party_score(rec.merchant.name, row.description)
    total = p.w_amount * amount + p.w_party * party + p.w_date * date_score
    reasons = [r for r in (amount_reason,) if r]
    if party >= Decimal("0.8"):
        reasons.append("PARTY_MATCH")
    if date_score >= Decimal("0.9"):
        reasons.append("DATE_NEAR")
    return Scored(total.quantize(Decimal("0.001")), tuple(reasons))


def _decide(best: Scored, rivals: list[Scored]) -> Expect | None:
    p = policy()
    runner_up = max((r.score for r in rivals), default=Decimal(0))
    if best.score >= p.auto and runner_up < best.score - p.margin:
        return "AUTO"
    if best.score >= p.propose:
        return "PROPOSED"
    return None


# ---------------------------------------------------------------------------- intended matches


def intended_matches(books: "Books") -> list[IntendedMatch]:
    matches: list[IntendedMatch] = []
    rows = books.bank_rows
    matches += _bank_document_matches(rows, books.sales, books.purchases, books.receipts)
    matches += _bank_ledger_matches(rows, books.ledger)
    matches += _document_ledger_matches(books)
    return matches


def _month(d: date) -> str:
    return f"{d:%Y-%m}"


def _bank_document_matches(
    rows: list[BankRow],
    sales: list[InvoiceData],
    purchases: list[InvoiceData],
    receipts: list[ReceiptData],
) -> list[IntendedMatch]:
    out: list[IntendedMatch] = []
    invoices = {inv.key: inv for inv in [*sales, *purchases]}
    receipt_of = {rec.key: rec for rec in receipts}
    # Split payments: several bank lines for one invoice.
    parts: dict[str, list[BankRow]] = {}
    for row in rows:
        if row.flow != "sale" or len(row.documents) != 1:
            continue
        inv = invoices[row.documents[0]]
        short = abs(row.amount - inv.total) > amount_tolerance(inv.total)
        if short and amount_score(row.amount, inv.total)[1] != "NET_OF_TAX":
            parts.setdefault(inv.key, []).append(row)

    for row in rows:
        if not row.documents:
            continue
        key = row.documents[0]
        if key in receipt_of:
            out.append(_receipt_match(row, receipt_of[key], receipts))
        elif key in parts:
            continue
        elif len(row.documents) > 1:
            out.append(_multi_match(row, [invoices[k] for k in row.documents]))
        else:
            pool = sales if row.flow == "sale" else purchases
            out.append(_invoice_match(row, invoices[key], pool))
    for key, split_rows in parts.items():
        out.append(_split_match(split_rows, invoices[key]))
    return out


def _kind(inv: InvoiceData) -> MatchKind:
    return "BANK_SALES_INVOICE" if inv.kind == "SALES" else "BANK_PURCHASE_INVOICE"


def _invoice_match(row: BankRow, inv: InvoiceData, pool: list[InvoiceData]) -> IntendedMatch:
    best = score_invoice(row, inv)
    if best is None:
        raise ValueError(f"{row.key} is outside the window of {inv.key}")
    rivals = [(other, score_invoice(row, other)) for other in pool if other.key != inv.key]
    scored = [(other, s) for other, s in rivals if s is not None]
    expect = _decide(best, [s for _, s in scored])
    if expect is None:
        raise ValueError(f"{row.key} → {inv.key} scores {best.score}, below proposeScore")
    documents = [inv.key]
    note = ""
    if expect == "PROPOSED":
        tied = [other.key for other, s in scored if s.score >= best.score - policy().margin]
        documents = [inv.key, *tied]
        note = f"{inv.key} is the invoice paid; the others score within the ambiguity margin"
    return IntendedMatch(
        _month(row.date),
        _kind(inv),
        [row.key],
        documents,
        [],
        expect,
        list(best.reasons),
        best.score,
        note,
    )


def _multi_match(row: BankRow, invs: list[InvoiceData]) -> IntendedMatch:
    """One transfer for several invoices: the sum is exact, same party, every number shown."""
    total = sum((inv.total for inv in invs), Decimal(0))
    assert abs(row.amount - total) <= amount_tolerance(total)
    assert all(party_score(inv.party, row.description) >= Decimal("0.8") for inv in invs)
    assert all(inv.number in row.description for inv in invs)
    return IntendedMatch(
        _month(row.date),
        _kind(invs[0]),
        [row.key],
        [inv.key for inv in invs],
        [],
        "AUTO",
        ["AMOUNT_EXACT", "PARTY_MATCH", "REFERENCE_IN_TEXT"],
        Decimal(1),
        "one transfer pays several invoices",
    )


def _split_match(rows: list[BankRow], inv: InvoiceData) -> IntendedMatch:
    """Several transfers for one invoice (≤ maxSplitParts), sum exact, same party."""
    paid = sum((row.amount for row in rows), Decimal(0))
    assert abs(paid - inv.total) <= amount_tolerance(inv.total), (inv.key, paid, inv.total)
    assert all(party_score(inv.party, row.description) >= Decimal("0.8") for row in rows)
    last = max(rows, key=lambda r: r.date)
    scored = score_invoice(last, inv, paid=paid)
    assert scored is not None
    return IntendedMatch(
        _month(last.date),
        _kind(inv),
        [r.key for r in rows],
        [inv.key],
        [],
        "AUTO",
        ["SPLIT", *scored.reasons],
        scored.score,
        "one invoice paid in several transfers",
    )


def _receipt_match(row: BankRow, rec: ReceiptData, receipts: list[ReceiptData]) -> IntendedMatch:
    best = score_receipt(row, rec)
    if best is None:
        raise ValueError(f"{row.key} is outside the window of {rec.key}")
    rivals = [s for other in receipts if other.key != rec.key if (s := score_receipt(row, other))]
    expect = _decide(best, rivals)
    if expect is None:
        raise ValueError(f"{row.key} → {rec.key} scores {best.score}, below proposeScore")
    return IntendedMatch(
        _month(row.date),
        "BANK_RECEIPT",
        [row.key],
        [rec.key],
        [],
        expect,
        list(best.reasons),
        best.score,
    )


def _bank_ledger_matches(rows: list[BankRow], ledger: list[LedgerRow]) -> list[IntendedMatch]:
    """Ledger cash: same amount, dates within ledgerDays, on the mapped account (docs/08 §6.2)."""
    cash = [e for e in ledger if e.account == "1110"]
    window = policy().ledger_days
    out: list[IntendedMatch] = []
    for row in rows:
        if not row.in_ledger:
            continue
        entry = next(e for e in cash if e.bank_key == row.key)
        signed_ok = (row.credit is not None) == (entry.debit is not None)
        assert signed_ok and entry.amount == row.amount, (row.key, entry.key)
        out.append(
            IntendedMatch(
                _month(row.date),
                "BANK_LEDGER",
                [row.key],
                [],
                [entry.key],
                "AUTO",
                ["AMOUNT_EXACT", "DATE_NEAR"],
                Decimal(1),
            )
        )
        assert abs((entry.date - row.date).days) <= window
    return out


def _document_ledger_matches(books: "Books") -> list[IntendedMatch]:
    """Each invoice and receipt has its booking: receivable, payable or expense (docs/08 §6.2)."""
    out: list[IntendedMatch] = []
    for entry in books.ledger:
        if entry.document_key is None:
            continue
        reasons = (
            ["AMOUNT_EXACT", "REFERENCE_IN_TEXT"]
            if entry.reference
            else ["AMOUNT_EXACT", "PARTY_MATCH", "DATE_NEAR"]
        )
        out.append(
            IntendedMatch(
                _month(entry.date),
                "DOCUMENT_LEDGER",
                [],
                [entry.document_key],
                [entry.key],
                "AUTO",
                reasons,
                Decimal(1),
            )
        )
    return out


# ---------------------------------------------------------------------------- checks used by tests


def unambiguous_amounts(books: "Books") -> list[str]:
    """Problems where a bank line has more than its intended candidates within amount tolerance."""
    problems: list[str] = []
    window = policy().ledger_days
    cash = [e for e in books.ledger if e.account == "1110"]
    for row in books.bank_rows:
        near = [
            e
            for e in cash
            if abs((e.date - row.date).days) <= window
            and abs(e.amount - row.amount) <= amount_tolerance(row.amount)
            and (e.debit is not None) == (row.credit is not None)
        ]
        expected = 1 if row.in_ledger else 0
        if len(near) != expected:
            problems.append(f"{row.key} has {len(near)} ledger candidates")
    return problems
