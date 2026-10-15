"""Clients and suppliers from the books (docs/08 §4.2; spec 014, AC-014-1). Pure.

Bank lines, invoices and receipts mention parties. Mentions with the same name, or a spelling the
token-set ratio puts at 90 or more, are one counterparty; a document's spelling names it. Roles come
from the books (who bought, who issued) and from each category's role in `categories.v1.yaml`.
Rows with no party name go to the category's bucket ("Bank fees"), so totals stay complete.
Accounts seen are the masked accounts purchase invoices asked to be paid to; `X08` reads them.
"""

import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Literal, cast

from rapidfuzz import fuzz

from app.core.ids import content_id
from app.domain.categorize import CategoryPolicy
from app.domain.models.bank_line import BankLine
from app.domain.models.invoice import Invoice, Receipt

Role = Literal[
    "CLIENT", "SUPPLIER", "LENDER", "OWNER", "OWN_ACCOUNT", "RELATED_PARTY", "GOVERNMENT", "OTHER"
]
Kind = Literal["PERSON", "BUSINESS", "GOVERNMENT", "BANK", "UNKNOWN"]

ROLE_ORDER: tuple[Role, ...] = (
    "CLIENT",
    "SUPPLIER",
    "LENDER",
    "OWNER",
    "OWN_ACCOUNT",
    "RELATED_PARTY",
    "GOVERNMENT",
    "OTHER",
)
MERGE_SCORE = 90
SAMPLE_EVIDENCE = 3
ZERO = Decimal("0")
_PAID = ("PAID_BANK", "PAID_CASH", "CONFIRMED_BY_YOU")


@dataclass(frozen=True)
class MonthTotals:
    in_amount: Decimal = ZERO
    out_amount: Decimal = ZERO
    count: int = 0


@dataclass(frozen=True)
class AccountSeen:
    account_masked: str
    first_seen: date
    last_seen: date


@dataclass(frozen=True)
class Counterparty:
    counterparty_id: str
    name: str
    aliases: tuple[str, ...]
    kind: Kind
    roles: tuple[Role, ...]
    totals_by_month: dict[str, MonthTotals]
    accounts_seen: tuple[AccountSeen, ...]
    open_invoices: int
    first_date: date | None
    last_date: date | None
    sample_evidence: tuple[dict[str, Any], ...]
    bank_line_ids: tuple[str, ...] = ()
    invoice_ids: tuple[str, ...] = ()
    receipt_ids: tuple[str, ...] = ()
    bucket: bool = False  # a category's bucket, not a named party

    @property
    def total_in(self) -> Decimal:
        return sum((t.in_amount for t in self.totals_by_month.values()), ZERO)

    @property
    def total_out(self) -> Decimal:
        return sum((t.out_amount for t in self.totals_by_month.values()), ZERO)


def fold_name(text: str | None) -> str:
    """Accents, case, punctuation and spacing do not make a different party."""
    plain = unicodedata.normalize("NFKD", text or "")
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    kept = "".join(c if c.isalnum() or c == "&" else " " for c in plain)
    return " ".join(kept.casefold().split())


def same_name(a: str, b: str, min_score: int = MERGE_SCORE) -> bool:
    return bool(a and b) and (a == b or fuzz.token_set_ratio(a, b) >= min_score)


@dataclass(frozen=True)
class Mention:
    """One appearance of a party in the books."""

    name: str  # as the book spells it, or the bucket's wording
    key: str  # folded name
    role: Role
    kind: Kind
    day: date
    month: str
    amount: Decimal = ZERO  # signed: money in to the business is positive; documents carry none
    counted: bool = False  # a bank line: part of the totals
    from_document: bool = False  # a document's spelling names the party over a bank line's
    tx_id: str | None = None
    invoice_id: str | None = None
    receipt_id: str | None = None
    doc_id: str | None = None
    page: int | None = None
    account_masked: str | None = None
    open_invoice: bool = False
    bucket: bool = False


def _role_of(category_id: str, policy: CategoryPolicy) -> Role:
    cat = policy.categories.get(category_id)
    role = (cat.role if cat else None) or "OTHER"
    return cast(Role, role) if role in ROLE_ORDER else "OTHER"


def _kind_for(role: Role, category_id: str | None, *, bucket: bool) -> Kind:
    if role == "GOVERNMENT":
        return "GOVERNMENT"
    if category_id == "BANK_FEES" or category_id == "INTEREST_RECEIVED":
        return "BANK"
    if bucket:
        return "UNKNOWN"
    if role in ("OWNER", "RELATED_PARTY"):
        return "PERSON"
    return "BUSINESS"


def _own(name: str, own_keys: list[str]) -> bool:
    return any(same_name(name, own) for own in own_keys)


def mentions(
    lines: list[BankLine],
    invoices: list[Invoice],
    receipts: list[Receipt],
    *,
    policy: CategoryPolicy,
    own_names: list[str],
) -> list[Mention]:
    own_keys = [fold_name(n) for n in own_names if n and n.strip()]
    out: list[Mention] = []
    for ln in lines:
        cat = policy.categories.get(ln.category)
        name = (ln.counterparty_name or "").strip()
        key = fold_name(name)
        role = _role_of(ln.category, policy)
        if key and _own(key, own_keys):
            own_name = (
                next(n for n in own_names if fold_name(n) == key)
                if any(fold_name(n) == key for n in own_names)
                else name
            )
            out.append(
                Mention(
                    own_name,
                    key,
                    "OWN_ACCOUNT",
                    "BUSINESS",
                    ln.date,
                    ln.month,
                    ln.amount,
                    counted=True,
                    tx_id=ln.tx_id,
                    doc_id=ln.doc_id,
                    page=ln.page,
                )
            )
            continue
        if not key:
            wording = (cat.bucket or cat.label) if cat else ln.category
            out.append(
                Mention(
                    wording,
                    f"bucket:{ln.category}",
                    role,
                    _kind_for(role, ln.category, bucket=True),
                    ln.date,
                    ln.month,
                    ln.amount,
                    counted=True,
                    tx_id=ln.tx_id,
                    doc_id=ln.doc_id,
                    page=ln.page,
                    bucket=True,
                )
            )
            continue
        out.append(
            Mention(
                name,
                key,
                role,
                _kind_for(role, ln.category, bucket=False),
                ln.date,
                ln.month,
                ln.amount,
                counted=True,
                tx_id=ln.tx_id,
                doc_id=ln.doc_id,
                page=ln.page,
            )
        )
    for inv in invoices:
        party = (inv.buyer_name if inv.kind == "SALES" else inv.issuer_name) or ""
        key = fold_name(party)
        day = inv.issue_date
        if not key or day is None:
            continue
        role: Role = "CLIENT" if inv.kind == "SALES" else "SUPPLIER"
        payment = (inv.evidence or {}).get("payment")
        out.append(
            Mention(
                party.strip(),
                key,
                role,
                "BUSINESS",
                day,
                inv.month or f"{day:%Y-%m}",
                from_document=True,
                invoice_id=inv.invoice_id,
                doc_id=inv.doc_id,
                page=inv.pages[0] if inv.pages else 1,
                account_masked=inv.pay_to_masked if inv.kind == "PURCHASE" else None,
                open_invoice=payment not in _PAID,
            )
        )
    for rc in receipts:
        key = fold_name(rc.merchant_name)
        if not key or rc.date is None:
            continue
        out.append(
            Mention(
                (rc.merchant_name or "").strip(),
                key,
                "SUPPLIER",
                "BUSINESS",
                rc.date,
                rc.month or f"{rc.date:%Y-%m}",
                from_document=True,
                receipt_id=rc.receipt_id,
                doc_id=rc.doc_id,
                page=rc.pages[0] if rc.pages else 1,
            )
        )
    return out


def _group(ms: list[Mention]) -> list[list[Mention]]:
    """Mentions with the same or a near-identical name, in a deterministic order."""
    ordered = sorted(
        ms,
        key=lambda m: (
            m.bucket,
            m.key,
            m.day,
            m.tx_id or "",
            m.invoice_id or "",
            m.receipt_id or "",
        ),
    )
    groups: list[list[Mention]] = []
    keys: list[str] = []
    for m in ordered:
        found = None
        for i, key in enumerate(keys):
            if m.bucket or key.startswith("bucket:"):
                if m.key == key:
                    found = i
                    break
                continue
            if same_name(m.key, key):
                found = i
                break
        if found is None:
            groups.append([m])
            keys.append(m.key)
        else:
            groups[found].append(m)
    return groups


def _evidence(m: Mention) -> dict[str, Any]:
    ref: dict[str, Any] = {"docId": m.doc_id, "page": m.page}
    if m.tx_id:
        ref["txId"] = m.tx_id
    if m.invoice_id:
        ref["invoiceId"] = m.invoice_id
    if m.receipt_id:
        ref["receiptId"] = m.receipt_id
    return ref


def _build(group: list[Mention]) -> Counterparty:
    spellings: dict[str, int] = defaultdict(int)
    document_spellings: dict[str, int] = defaultdict(int)
    for m in group:
        spellings[m.name] += 1
        if m.from_document:
            document_spellings[m.name] += 1
    chosen = document_spellings or spellings
    name = sorted(chosen.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    aliases = tuple(sorted(s for s in spellings if s != name))
    found = {m.role for m in group}
    if len(found) > 1:
        found.discard("OTHER")  # a refund or a fee does not make a client "other" too
    roles: tuple[Role, ...] = tuple(r for r in ROLE_ORDER if r in found)
    kind_order = ("GOVERNMENT", "BANK", "PERSON", "BUSINESS", "UNKNOWN")
    kind = cast(Kind, sorted({m.kind for m in group}, key=kind_order.index)[0])
    totals: dict[str, MonthTotals] = {}
    for m in sorted(group, key=lambda m: m.month):
        if not m.counted:
            continue
        t = totals.get(m.month, MonthTotals())
        totals[m.month] = MonthTotals(
            t.in_amount + (m.amount if m.amount > 0 else ZERO),
            t.out_amount + (-m.amount if m.amount < 0 else ZERO),
            t.count + 1,
        )
    seen: dict[str, tuple[date, date]] = {}
    for m in sorted(group, key=lambda m: m.day):
        if m.account_masked:
            first, last = seen.get(m.account_masked, (m.day, m.day))
            seen[m.account_masked] = (min(first, m.day), max(last, m.day))
    accounts = tuple(
        AccountSeen(masked, first, last)
        for masked, (first, last) in sorted(seen.items(), key=lambda kv: (kv[1][0], kv[0]))
    )
    days = [m.day for m in group]
    by_day = sorted(
        group, key=lambda m: (m.day, m.invoice_id or "", m.receipt_id or "", m.tx_id or "")
    )
    samples = tuple(_evidence(m) for m in by_day[:SAMPLE_EVIDENCE])
    key = min(m.key for m in group)
    bucket = all(m.bucket for m in group)
    return Counterparty(
        counterparty_id=content_id("cp", key),
        name=name,
        aliases=aliases,
        kind=kind,
        roles=roles,
        totals_by_month=dict(sorted(totals.items())),
        accounts_seen=accounts,
        open_invoices=sum(1 for m in group if m.open_invoice),
        first_date=min(days) if days else None,
        last_date=max(days) if days else None,
        sample_evidence=samples,
        bank_line_ids=tuple(m.tx_id for m in by_day if m.tx_id),
        invoice_ids=tuple(m.invoice_id for m in by_day if m.invoice_id),
        receipt_ids=tuple(m.receipt_id for m in by_day if m.receipt_id),
        bucket=bucket,
    )


def build_counterparties(
    lines: list[BankLine],
    invoices: list[Invoice],
    receipts: list[Receipt],
    *,
    policy: CategoryPolicy,
    own_names: list[str],
) -> list[Counterparty]:
    """Every party the books mention, named parties and buckets alike, sorted by name."""
    groups = _group(mentions(lines, invoices, receipts, policy=policy, own_names=own_names))
    return sorted((_build(g) for g in groups), key=lambda c: (c.name.casefold(), c.counterparty_id))
