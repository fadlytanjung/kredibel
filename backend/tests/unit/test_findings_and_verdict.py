"""Re-run rules for findings (docs/08 §1), the integrity verdict (§3), and P6 for A01."""

from datetime import UTC, date, datetime
from decimal import Decimal

from app.domain.checks.base import CheckContext
from app.domain.checks.policy import ForensicsPolicy
from app.domain.findings import (
    Category,
    Evidence,
    Finding,
    FindingStatus,
    Severity,
    finding_id,
    merge_findings,
)
from app.domain.models.bank_line import BankLine
from app.domain.models.document import DocType, Document
from app.domain.verdict import integrity_verdict

POLICY = ForensicsPolicy(enabled={"A01_RUNNING_BALANCE_BREAK", "E01_LOW_EXTRACTION_AGREEMENT"})


def _f(
    code: str,
    severity: Severity = "MEDIUM",
    status: FindingStatus = "OPEN",
    category: Category = "STRUCTURE",
) -> Finding:
    return Finding(
        finding_id=finding_id(code, "doc_1"),
        code=code,
        category=category,
        severity=severity,
        title=code,
        facts={},
        evidence=[Evidence(doc_id="doc_1")],
        status=status,
    )


def test_a_rerun_resolves_what_no_longer_applies_and_keeps_decisions():
    existing = [_f("M01", status="DISMISSED"), _f("M02", status="ACKNOWLEDGED"), _f("M03")]
    merged = {f.code: f.status for f in merge_findings(existing, [_f("M01"), _f("M02"), _f("M04")])}
    assert merged == {"M01": "DISMISSED", "M02": "ACKNOWLEDGED", "M03": "RESOLVED", "M04": "OPEN"}


def test_the_verdict_is_decided_top_down():
    assert integrity_verdict([], POLICY) == "CLEAN"
    assert (
        integrity_verdict([_f("E01_LOW_EXTRACTION_AGREEMENT", category="EXTRACTION")], POLICY)
        == "UNVERIFIABLE"
    )
    two_e01 = [_f("E01_LOW_EXTRACTION_AGREEMENT", category="EXTRACTION")] * 2
    assert integrity_verdict(two_e01, POLICY) == "UNVERIFIABLE"  # reading quality is not tampering
    assert integrity_verdict([_f("M01"), _f("M02")], POLICY) == "SUSPICIOUS"
    assert integrity_verdict([_f("M04", "HIGH")], POLICY) == "SUSPICIOUS"
    tampered = [_f("A01_RUNNING_BALANCE_BREAK", "CRITICAL", category="ARITHMETIC"), _f("M01")]
    assert integrity_verdict(tampered, POLICY) == "TAMPERED"
    dismissed = [_f("A01_RUNNING_BALANCE_BREAK", "CRITICAL", "DISMISSED", "ARITHMETIC")]
    assert integrity_verdict(dismissed, POLICY) == "CLEAN"
    assert integrity_verdict([_f("X05", "HIGH", category="CROSS_DOCUMENT")], POLICY) == "CLEAN"


def _line(i: int, amount: str, balance: str, status: str = "AGREED") -> BankLine:
    c = {"status": status, "page": 1, "bbox": None, "raw": {}}
    return BankLine(
        tx_id=f"tx_{i}",
        doc_id="doc_1",
        page=1,
        row_index=i,
        date=date(2026, 3, i + 1),
        month="2026-03",
        description="X",
        amount=Decimal(amount),
        balance=Decimal(balance),
        consensus={"amount": c, "balance": c},
    )


def _ctx(lines: list[BankLine]) -> CheckContext:
    doc = Document(
        doc_id="doc_1",
        file_name="s.pdf",
        content_type="application/pdf",
        size_bytes=1,
        page_count=1,
        sha256="0" * 64,
        gcs_path="orgs/o/documents/doc_1/original.pdf",
        uploaded_by="u",
        uploaded_at=datetime(2026, 4, 1, tzinfo=UTC),
        doc_type=DocType.BANK_STATEMENT,
    )
    return CheckContext(doc=doc, policy=POLICY, lines=lines, opening=Decimal("100.00"))


def test_a_break_among_agreed_values_is_critical_otherwise_uncertain():
    from app.domain.checks.arithmetic import running_balance

    agreed = running_balance(_ctx([_line(1, "50.00", "150.00"), _line(2, "10.00", "999.00")]))
    assert [(f.code, f.severity) for f in agreed] == [("A01_RUNNING_BALANCE_BREAK", "CRITICAL")]
    unsure = running_balance(
        _ctx([_line(1, "50.00", "150.00"), _line(2, "10.00", "999.00", "SINGLE_SOURCE")])
    )
    assert [(f.code, f.severity) for f in unsure] == [("E01_LOW_EXTRACTION_AGREEMENT", "MEDIUM")]
    assert running_balance(_ctx([_line(1, "50.00", "150.00"), _line(2, "10.00", "160.00")])) == []


def test_a_break_right_after_a_dropped_row_is_uncertain_not_critical():
    from app.domain.checks.arithmetic import running_balance

    after_drop = _line(2, "10.00", "999.00")
    after_drop.notes = ["ROW_DROPPED_ABOVE"]
    found = running_balance(_ctx([_line(1, "50.00", "150.00"), after_drop]))
    assert [(f.code, f.severity) for f in found] == [("E01_LOW_EXTRACTION_AGREEMENT", "MEDIUM")]
