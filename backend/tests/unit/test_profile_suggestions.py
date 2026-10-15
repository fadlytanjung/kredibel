"""Profile suggestions from documents (spec 014, T014-02; AC-014-4, AC-014-6; docs/08 §4.3): the
three P0 fields, confidence, deterministic IDs, a rejected value never returns, conflicts show both
values. Synthetic names and numbers only."""

from datetime import date

from app.core.ids import content_id
from app.domain.accounts import mask_tax_id
from app.domain.models.workspace import Address, BankAccount, Profile
from app.domain.profile_suggestions import (
    InvoiceFacts,
    StatementFacts,
    build_profile_suggestions,
)

OWN = ["Sunrise Coffee Roasters"]
ACB = StatementFacts(
    doc_id="doc_feb",
    page=1,
    bank_name="Archipelago Commerce Bank",
    account_masked="••••4821",
    account_hash="hash-4821",
    holder_name="SUNRISE COFFEE ROASTERS",
    holder_address="12 Roastery Lane\nBandung 40135",
    period_start=date(2026, 2, 1),
    agreed=True,
)
DECLARED = BankAccount(
    account_id="acc_1",
    bank_name="Archipelago Commerce Bank",
    account_masked="••••4821",
    holder_name="SUNRISE COFFEE ROASTERS",
)


def sales(iid: str, tax_id: str | None, issued: date, agreed: bool = True) -> InvoiceFacts:
    return InvoiceFacts(
        invoice_id=iid,
        doc_id=f"doc_{iid}",
        page=1,
        kind="SALES",
        issuer_name="Sunrise Coffee Roasters",
        issuer_tax_id=mask_tax_id(tax_id) if tax_id else None,
        issue_date=issued,
        agreed=agreed,
    )


def test_a_statement_account_the_workspace_has_not_declared_is_suggested_with_its_hash():
    other = StatementFacts(
        doc_id="doc_sav",
        page=1,
        bank_name="Archipelago Commerce Bank",
        account_masked="••••9907",
        account_hash="hash-9907",
        holder_name="SUNRISE COFFEE ROASTERS",
        holder_address=None,
        period_start=date(2026, 3, 1),
        agreed=False,
    )
    out = build_profile_suggestions(
        profile=Profile(
            legal_name=OWN[0],
            tax_id_masked=mask_tax_id("99-731.204.5-018.000"),
            address=Address(line1="12 Roastery Lane", city="Bandung"),
        ),
        accounts=[DECLARED],
        statements=[ACB, other],
        invoices=[],
        own_names=OWN,
        rejected=set(),
    )
    [bank] = out
    assert bank.field == "BANK_ACCOUNT" and bank.status == "PENDING"
    assert bank.value == {
        "bankName": "Archipelago Commerce Bank",
        "accountMasked": "••••9907",
        "holderName": "SUNRISE COFFEE ROASTERS",
    }
    assert bank.secret == {"accountHash": "hash-9907"}
    assert bank.confidence == "MEDIUM"  # the header was read by one reading only
    assert bank.display == "Archipelago Commerce Bank ••••9907"
    assert bank.evidence == [{"docId": "doc_sav", "page": 1}]
    assert bank.suggestion_id == content_id("sug", "BANK_ACCOUNT", "hash-9907")


def test_the_tax_id_and_address_come_from_the_workspace_s_own_documents_when_the_profile_has_none():
    invoices = [
        sales("inv-1", "99-731.204.5-018.000", date(2026, 1, 6)),
        sales("inv-2", "99-731.204.5-018.000", date(2026, 2, 4)),
        sales("inv-3", "99-731.204.5-018.000", date(2026, 3, 12)),
        InvoiceFacts(
            "inv-p",
            "doc_p",
            1,
            "PURCHASE",
            "Green Valley Farms",
            "11-222.333.4-555.000",
            date(2026, 3, 3),
            True,
        ),
    ]
    out = build_profile_suggestions(
        profile=Profile(legal_name=OWN[0]),
        accounts=[DECLARED],
        statements=[ACB],
        invoices=invoices,
        own_names=OWN,
        rejected=set(),
    )
    by_field = {s.field: s for s in out}
    assert set(by_field) == {"TAX_ID", "ADDRESS"}
    tax = by_field["TAX_ID"]
    assert tax.value == {"taxIdMasked": mask_tax_id("99-731.204.5-018.000")}
    assert tax.confidence == "HIGH"
    assert tax.display == mask_tax_id("99-731.204.5-018.000"), "a tax ID is shown masked"
    assert tax.basis and "3" in tax.basis
    assert [e["docId"] for e in tax.evidence] == ["doc_inv-1", "doc_inv-2", "doc_inv-3"]
    address = by_field["ADDRESS"]
    assert address.value == {"line1": "12 Roastery Lane", "city": "Bandung", "postalCode": "40135"}
    assert address.confidence == "MEDIUM" and address.display == "12 Roastery Lane, Bandung 40135"
    assert address.evidence == [{"docId": "doc_feb", "page": 1}]
    assert all(s.status == "PENDING" for s in out)
    # The same facts give the same IDs on every run.
    again = build_profile_suggestions(
        profile=Profile(legal_name=OWN[0]),
        accounts=[DECLARED],
        statements=[ACB],
        invoices=invoices,
        own_names=OWN,
        rejected=set(),
    )
    assert [s.suggestion_id for s in again] == [s.suggestion_id for s in out]


def test_a_single_invoice_gives_a_medium_tax_id_and_a_rejected_value_never_returns():
    invoices = [sales("inv-1", "99-731.204.5-018.000", date(2026, 1, 6))]
    [tax, _address] = build_profile_suggestions(
        profile=Profile(legal_name=OWN[0]),
        accounts=[DECLARED],
        statements=[ACB],
        invoices=invoices,
        own_names=OWN,
        rejected=set(),
    )
    assert tax.confidence == "MEDIUM"
    out = build_profile_suggestions(
        profile=Profile(legal_name=OWN[0]),
        accounts=[DECLARED],
        statements=[ACB],
        invoices=invoices,
        own_names=OWN,
        rejected={tax.suggestion_id},
    )
    assert [s.field for s in out] == ["ADDRESS"]


def test_a_value_that_contradicts_the_profile_is_a_conflict_that_shows_both():
    invoices = [
        sales("inv-1", "99-731.204.5-018.000", date(2026, 1, 6)),
        sales("inv-2", "99-731.204.5-018.000", date(2026, 2, 4)),
    ]
    out = build_profile_suggestions(
        profile=Profile(
            legal_name=OWN[0],
            tax_id_masked=mask_tax_id("88-000.000.0-000.111"),
            address=Address(line1="Other", city="Jakarta"),
        ),
        accounts=[DECLARED],
        statements=[ACB],
        invoices=invoices,
        own_names=OWN,
        rejected=set(),
    )
    by_field = {s.field: s for s in out}
    assert by_field["TAX_ID"].status == "CONFLICT"
    assert by_field["TAX_ID"].conflict_with == mask_tax_id("88-000.000.0-000.111")
    assert by_field["ADDRESS"].status == "CONFLICT"
    assert by_field["ADDRESS"].conflict_with == "Other, Jakarta"
    # A profile that already says what the documents say gets no suggestion at all.
    same = build_profile_suggestions(
        profile=Profile(
            legal_name=OWN[0],
            tax_id_masked=mask_tax_id("99-731.204.5-018.000"),
            address=Address(line1="12 Roastery Lane", city="Bandung"),
        ),
        accounts=[DECLARED],
        statements=[ACB],
        invoices=invoices,
        own_names=OWN,
        rejected=set(),
    )
    assert same == []
