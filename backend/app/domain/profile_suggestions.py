"""Profile suggestions from documents (docs/08 §4.3; spec 014, AC-014-4, AC-014-6). Pure.

Documents say things about the workspace itself: the account a statement belongs to, the tax ID
printed on its own sales invoices, the address under the holder's name. Each becomes a suggestion
with a deterministic ID, so a run upserts it and a rejected value never comes back. Nothing changes
until a person accepts (constitution: the AI suggests, the user accepts).
"""

import re
from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import date
from typing import Any, Literal

from rapidfuzz import fuzz

from app.core.ids import content_id
from app.domain.models.workspace import BankAccount, Profile

SuggestionField = Literal["BANK_ACCOUNT", "TAX_ID", "ADDRESS", "ALIAS", "RELATED_PARTY"]
SuggestionStatus = Literal["PENDING", "CONFLICT", "ACCEPTED", "REJECTED"]
Confidence = Literal["HIGH", "MEDIUM", "LOW"]

OWN_NAME_MIN_SCORE = 90
_POSTAL = re.compile(r"^(?P<city>.*?)[\s,]+(?P<postal>\d{4,6})$")


@dataclass(frozen=True)
class StatementFacts:
    """What a read statement's header says (the hash comes from the digits the reader saw)."""

    doc_id: str
    page: int
    bank_name: str | None
    account_masked: str | None
    account_hash: str | None
    holder_name: str | None
    holder_address: str | None
    period_start: date | None
    agreed: bool  # the header values were agreed by both readings


@dataclass(frozen=True)
class InvoiceFacts:
    invoice_id: str
    doc_id: str
    page: int
    kind: Literal["SALES", "PURCHASE"]
    issuer_name: str | None
    issuer_tax_id: str | None  # masked, as invoice records store it
    issue_date: date | None
    agreed: bool
    issuer_address: str | None = None


@dataclass(frozen=True)
class Suggestion:
    suggestion_id: str
    field: SuggestionField
    value: dict[str, Any]
    display: str
    confidence: Confidence
    basis: str
    evidence: list[dict[str, Any]]
    status: SuggestionStatus = "PENDING"
    conflict_with: str | None = None
    secret: dict[str, str] = dc_field(default_factory=dict)  # orgPrivate only (account hashes)
    decided_by: str | None = None
    decided_at: Any = None


def _fold(text: str | None) -> str:
    return " ".join((text or "").casefold().split())


def _is_own(name: str | None, own_names: list[str]) -> bool:
    return bool(name) and any(
        fuzz.token_set_ratio(_fold(name), _fold(own)) >= OWN_NAME_MIN_SCORE
        for own in own_names
        if own
    )


def parse_address(text: str | None) -> dict[str, str] | None:
    """ "12 Roastery Lane\\nBandung 40135" → line1, city, postalCode; one line stays line1."""
    parts = [p.strip() for p in re.split(r"[\n,]+", text or "") if p.strip()]
    if not parts:
        return None
    out: dict[str, str] = {"line1": parts[0]}
    if len(parts) > 1:
        last = parts[-1]
        m = _POSTAL.match(last)
        if m:
            out["city"] = m.group("city").strip() or " ".join(parts[1:-1])
            out["postalCode"] = m.group("postal")
        else:
            out["city"] = last
    return out


def _address_display(value: dict[str, str]) -> str:
    tail = " ".join(x for x in (value.get("city"), value.get("postalCode")) if x)
    return ", ".join(x for x in (value.get("line1"), tail) if x)


def _same_address(a: dict[str, str], line1: str | None, city: str | None) -> bool:
    return _fold(a.get("line1")) == _fold(line1) and (
        not city or _fold(a.get("city")) == _fold(city)
    )


def build_profile_suggestions(
    *,
    profile: Profile,
    accounts: list[BankAccount],
    statements: list[StatementFacts],
    invoices: list[InvoiceFacts],
    own_names: list[str],
    rejected: set[str],
) -> list[Suggestion]:
    """The P0 suggestions the documents support, in a stable order; rejected IDs are left out."""
    out: list[Suggestion] = []

    # BANK_ACCOUNT: a statement account the workspace has not declared, held by the workspace.
    declared = {a.account_masked[-4:] for a in accounts if a.account_masked}
    seen_accounts: dict[str, list[StatementFacts]] = {}
    for st in sorted(statements, key=lambda s: (s.period_start or date.min, s.doc_id)):
        if not st.account_masked or not st.account_hash or st.account_masked[-4:] in declared:
            continue
        if st.holder_name and not _is_own(st.holder_name, own_names):
            continue  # someone else's statement is X05's business, not a profile suggestion
        seen_accounts.setdefault(st.account_hash, []).append(st)
    for account_hash, sts in seen_accounts.items():
        first = sts[0]
        bank = (first.bank_name or "").strip()
        value = {
            "bankName": bank,
            "accountMasked": first.account_masked,
            "holderName": (first.holder_name or "").strip(),
        }
        out.append(
            Suggestion(
                suggestion_id=content_id("sug", "BANK_ACCOUNT", account_hash),
                field="BANK_ACCOUNT",
                value=value,
                display=" ".join(x for x in (bank, first.account_masked) if x),
                confidence="HIGH" if any(s.agreed for s in sts) else "MEDIUM",
                basis=(
                    f"The account on {len(sts)} statement(s) is not among the workspace's "
                    "accounts yet"
                ),
                evidence=[{"docId": s.doc_id, "page": s.page} for s in sts],
                secret={"accountHash": account_hash},
            )
        )

    # TAX_ID: the issuer tax ID on the workspace's own sales invoices, the most frequent one;
    # records keep it masked (docs/14 §6), so the suggestion carries the masked form.
    own_sales = [
        inv
        for inv in invoices
        if inv.kind == "SALES" and inv.issuer_tax_id and _is_own(inv.issuer_name, own_names)
    ]
    by_tax: dict[str, list[InvoiceFacts]] = {}
    for inv in sorted(own_sales, key=lambda i: (i.issue_date or date.min, i.invoice_id)):
        by_tax.setdefault(re.sub(r"\s", "", inv.issuer_tax_id or ""), []).append(inv)
    if by_tax:
        masked, invs = sorted(by_tax.items(), key=lambda kv: (-len(kv[1]), kv[0]))[0]
        current = profile.tax_id_masked
        if current != masked:
            agreed = sum(1 for i in invs if i.agreed)
            out.append(
                Suggestion(
                    suggestion_id=content_id("sug", "TAX_ID", masked),
                    field="TAX_ID",
                    value={"taxIdMasked": masked},
                    display=masked,
                    confidence="HIGH" if agreed >= 2 else "MEDIUM",
                    basis=(
                        f"Printed as the issuer's tax ID on {len(invs)} of the workspace's "
                        "sales invoice(s)"
                    ),
                    evidence=[{"docId": i.doc_id, "page": i.page} for i in invs],
                    status="CONFLICT" if current else "PENDING",
                    conflict_with=current if current else None,
                )
            )

    # ADDRESS: the statement holder's address, else the issuer address on own sales invoices.
    sources: list[tuple[str | None, str, int]] = [
        (st.holder_address, st.doc_id, st.page)
        for st in sorted(statements, key=lambda s: (s.period_start or date.min, s.doc_id))
        if st.holder_address and (not st.holder_name or _is_own(st.holder_name, own_names))
    ]
    sources += [
        (inv.issuer_address, inv.doc_id, inv.page)
        for inv in sorted(own_sales, key=lambda i: (i.issue_date or date.min, i.invoice_id))
        if inv.issuer_address
    ]
    by_address: dict[str, tuple[dict[str, str], list[dict[str, Any]]]] = {}
    for text, doc_id, page in sources:
        parsed = parse_address(text)
        if parsed is None:
            continue
        key = _fold(parsed.get("line1")) + "|" + _fold(parsed.get("city"))
        value, refs = by_address.setdefault(key, (parsed, []))
        refs.append({"docId": doc_id, "page": page})
    if by_address:
        key, (value, refs) = sorted(by_address.items(), key=lambda kv: (-len(kv[1][1]), kv[0]))[0]
        current = profile.address
        if current is None or not _same_address(value, current.line1, current.city):
            conflict = (
                _address_display({"line1": current.line1 or "", "city": current.city or ""})
                if current and (current.line1 or current.city)
                else None
            )
            out.append(
                Suggestion(
                    suggestion_id=content_id("sug", "ADDRESS", key),
                    field="ADDRESS",
                    value=value,
                    display=_address_display(value),
                    confidence="MEDIUM",
                    basis=(
                        "Printed under the holder's name on the statement or as the issuer "
                        "address on the sales invoices"
                    ),
                    evidence=refs,
                    status="CONFLICT" if conflict else "PENDING",
                    conflict_with=conflict,
                )
            )

    return [s for s in out if s.suggestion_id not in rejected]
