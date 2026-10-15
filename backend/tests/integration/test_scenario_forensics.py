"""Forensics on the scenarios (spec 006, T006-09; AC-006-12, AC-006-13).

The real synthetic PDFs are inspected (producer, saves, fonts) and the statements' printed rows
checked by the pure document checks; the duplicate rules see the copies as the duplicate node does.
The workflow path on S2's edited statement is `test_integrity_workflow.py`; S3's figures through
the API are in `test_scenario_review_queue_api.py`. Synthetic data only.
"""

import copy
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from app.adapters.pdf_inspector import PdfInspector
from app.adapters.policy_files import load_forensics
from app.domain.checks.base import CheckContext, DeclaredAccount, run_document_checks
from app.domain.duplicates import (
    InvoiceKey,
    ReceiptKey,
    StatementKey,
    invoice_duplicate,
    receipt_duplicate,
    statement_duplicate,
)
from app.domain.models.document import DocType
from app.domain.verdict import integrity_verdict
from tests.integration import scenario_books as books

POLICY = load_forensics(Path(__file__).resolve().parents[3] / "contracts" / "policy")
INSPECTOR = PdfInspector()
OWN = "Sunrise Coffee Roasters"


def _statements(truth: dict) -> list[dict]:
    return [d for d in truth["documents"] if d.get("docType") == "BANK_STATEMENT"]


def _as_printed(entry: dict) -> dict:
    """The rows as the PDF prints them: the truth keeps the genuine values and lists the edits."""
    printed = copy.deepcopy(entry)
    for edit in entry.get("tampering", []):
        row = next(r for r in printed["rows"] if r["rowIndex"] == edit["rowIndex"])
        row[edit["field"]] = edit["after"]
    return printed


def _context(scenario: str, entry: dict, categories) -> CheckContext:
    printed = _as_printed(entry)
    doc = books._document(
        scenario,
        entry,
        DocType.BANK_STATEMENT,
        [entry["period"]["start"][:7]],
        meta=books.statement_meta(entry),
        pages=2,
    )
    return CheckContext(
        doc=doc,
        policy=POLICY,
        pdf=INSPECTOR.inspect_pdf(books.scenario_file(scenario, entry["file"]).read_bytes()),
        lines=books.bank_lines(printed, doc.doc_id, categories, "IFRS"),
        opening=Decimal(entry["opening"]),
        closing=Decimal(entry["closing"]),
        own_names=[OWN],
        accounts=[DeclaredAccount(books.BANK, books.ACCOUNT_MASKED, OWN.upper())],
    )


def test_ac006_12_every_s1_statement_is_clean_and_s2_march_is_tampered():
    categories = books.books_deps().categories
    s1 = books.load_truth("S1")
    for entry in _statements(s1):
        findings = run_document_checks(_context("S1", entry, categories))
        codes = sorted(f.code for f in findings)
        assert integrity_verdict(findings, POLICY) == entry["expected"]["verdict"] == "CLEAN", (
            entry["file"],
            codes,
        )
        assert not [c for c in codes if c[0] in "AM"], (entry["file"], codes)

    s2 = books.load_truth("S2")
    [march] = [d for d in _statements(s2) if d["tampering"]]
    findings = run_document_checks(_context("S2", march, categories))
    codes = {f.code for f in findings}
    assert integrity_verdict(findings, POLICY) == "TAMPERED"
    # M04 needs where each value sits on the page, which only the grounded reading knows: the
    # workflow path proves it on this statement (test_integrity_workflow.py).
    assert set(march["expected"]["findingsP0"]) - {"M04_FONT_ANOMALY_IN_VALUES"} <= codes, codes
    [a01] = [f for f in findings if f.code == "A01_RUNNING_BALANCE_BREAK"]
    edited = march["tampering"][0]
    assert a01.severity == "CRITICAL"
    assert a01.facts["row"] == str(edited["rowIndex"] + 1), a01.facts  # the break shows below it
    for entry in _statements(s2):
        if not entry["tampering"]:
            clean = run_document_checks(_context("S2", entry, categories))
            assert integrity_verdict(clean, POLICY) == "CLEAN", entry["file"]


def test_ac006_13_s3_copies_are_held_with_the_expected_codes():
    """D02, D03 and D05 as the duplicate node sees them; D01 is refused at upload (API gate in the
    review-queue test); D06 (ledger entries) is not built yet (docs/20)."""
    truth = books.load_truth("S3")
    originals = {d["file"]: d for d in truth["documents"] if "copyOf" not in d}
    copies = {d["expected"]["duplicate"]["code"]: d for d in truth["documents"] if "copyOf" in d}
    later = books.UPLOADED_AT + timedelta(days=1)
    policy = POLICY.duplicates

    def statement_key(entry: dict, doc_id: str, uploaded) -> StatementKey:
        return StatementKey(
            doc_id=doc_id,
            uploaded_at=uploaded,
            bank=entry["bank"],
            last4=entry["accountNumber"][-4:],
            start=date.fromisoformat(entry["period"]["start"]),
            end=date.fromisoformat(entry["period"]["end"]),
            rows=frozenset(
                (
                    date.fromisoformat(r["date"]),
                    Decimal(r["credit"]) if r["credit"] else -Decimal(r["debit"]),
                    Decimal(r["balance"]) if r.get("balance") else None,
                )
                for r in entry["rows"]
            ),
        )

    reexport = copies["D02_STATEMENT_PERIOD_DUPLICATE"]
    original = originals[reexport["copyOf"]]
    found = statement_duplicate(
        statement_key(original, "doc_copy", later),
        [statement_key(original, "doc_original", books.UPLOADED_AT)],
        policy,
    )
    assert found is not None and (found.code, found.of_doc_id, found.hold) == (
        "D02_STATEMENT_PERIOD_DUPLICATE",
        "doc_original",
        True,
    )

    def invoice_key(entry: dict, doc_id: str, uploaded) -> InvoiceKey:
        pay_to = (entry.get("payTo") or {}).get("accountNumber")
        return InvoiceKey(
            doc_id=doc_id,
            uploaded_at=uploaded,
            issuer=entry["issuer"]["name"],
            number=entry["number"],
            issue_date=date.fromisoformat(entry["issueDate"]),
            total=Decimal(entry["total"]),
            pay_to=f"••••{pay_to[-4:]}" if pay_to else None,
        )

    scan = copies["D03_INVOICE_DUPLICATE"]
    original = originals[scan["copyOf"]]
    others = [
        invoice_key(d, books.doc_id_of(d["key"]), books.UPLOADED_AT)
        for d in truth["documents"]
        if d.get("docType") in ("SALES_INVOICE", "PURCHASE_INVOICE")
    ]
    found = invoice_duplicate(invoice_key(original, "doc_scan", later), others, policy)
    assert found is not None and (found.code, found.of_doc_id, found.hold) == (
        "D03_INVOICE_DUPLICATE",
        books.doc_id_of(original["key"]),
        True,
    )

    photo = copies["D05_RECEIPT_DUPLICATE"]
    original = originals[photo["copyOf"]]

    def receipt_key(entry: dict, file: str, doc_id: str, uploaded) -> ReceiptKey:
        return ReceiptKey(
            doc_id=doc_id,
            uploaded_at=uploaded,
            merchant=entry["merchant"]["name"],
            day=date.fromisoformat(entry["issuedAt"][:10]),
            total=Decimal(entry["total"]),
            p_hash=INSPECTOR.page_hash(books.scenario_file("S3", file).read_bytes()),
        )

    others = [
        receipt_key(d, d["file"], books.doc_id_of(d["key"]), books.UPLOADED_AT)
        for d in truth["documents"]
        if d.get("docType") == "RECEIPT" and d["file"].endswith(".jpg")
    ]
    found = receipt_duplicate(
        receipt_key(original, photo["file"], "doc_photo", later), others, policy
    )
    assert found is not None and (found.code, found.of_doc_id, found.hold) == (
        "D05_RECEIPT_DUPLICATE",
        books.doc_id_of(original["key"]),
        True,
    )

    exact = copies["D01_EXACT_FILE_DUPLICATE"]
    assert (
        books.scenario_file("S3", exact["file"]).read_bytes()
        == books.scenario_file("S3", exact["copyOf"]).read_bytes()
    ), "the exact copy is the same bytes: SHA-256 refuses it at upload"
