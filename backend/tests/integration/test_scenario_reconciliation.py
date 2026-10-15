"""Scenario reconciliation and month check test gates (spec 007, T007-08).

Gates:
- AC-007-8: S1 reconciliation accuracy ≥ 85%, 0 wrong automatic matches,
  February ambiguous pair is PROPOSED.
- AC-007-7: Upload-order independence: S5 (reverse upload order) produces identical matches to S1.
- AC-007-11: S4 risk checks (May X08 supplier account changed, April R02 unknown supplier party)
  and double payment fixture (D07 double payment).
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.adapters.policy_files import load_forensics, load_reconciliation_policy
from app.domain.checks.month import MonthContext, StatementSpan, run_month_checks
from app.domain.models.bank_line import BankLine
from app.domain.models.invoice import Invoice
from app.domain.reconcile import Decisions, assign_matches
from app.domain.reconcile_scoring import MatchRecord

SYNTH_DIR = Path(__file__).resolve().parents[3] / "tools" / "synthetic" / "out"
POLICY_DIR = Path(__file__).resolve().parents[3] / "contracts" / "policy"


@pytest.fixture
def recon_policy():
    return load_reconciliation_policy(POLICY_DIR)


@pytest.fixture
def forensics_policy():
    return load_forensics(POLICY_DIR)


def _records_from_truth(truth: dict) -> tuple[list[MatchRecord], list[MatchRecord]]:
    bank_records: list[MatchRecord] = []
    doc_records: list[MatchRecord] = []
    for d in truth["documents"]:
        if d["docType"] == "BANK_STATEMENT":
            for r in d["rows"]:
                amount = Decimal(r["credit"]) if r["credit"] else -Decimal(r["debit"])
                y, m, day = map(int, r["date"].split("-"))
                bank_records.append(
                    MatchRecord(
                        record_id=r["key"],
                        kind="BANK",
                        amount=amount,
                        date=date(y, m, day),
                        currency="IDR",
                        description=r["description"],
                    )
                )
        elif d["docType"] in ("SALES_INVOICE", "PURCHASE_INVOICE"):
            kind = "SALES_INVOICE" if d["docType"] == "SALES_INVOICE" else "PURCHASE_INVOICE"
            party = d["billTo"]["name"] if kind == "SALES_INVOICE" else d["issuer"]["name"]
            y, m, day = map(int, d["issueDate"].split("-"))
            due_y, due_m, due_day = map(int, d["dueDate"].split("-"))
            doc_records.append(
                MatchRecord(
                    record_id=d["key"],
                    kind=kind,
                    amount=Decimal(d["total"]),
                    date=date(y, m, day),
                    due_date=date(due_y, due_m, due_day),
                    currency="IDR",
                    party=party,
                    reference=d["number"],
                )
            )
        elif d["docType"] == "RECEIPT":
            y, m, day = map(int, d["issuedAt"][:10].split("-"))
            method = "CARD" if "CARD" in d["payment"].upper() else "CASH"
            doc_records.append(
                MatchRecord(
                    record_id=d["key"],
                    kind="RECEIPT",
                    amount=Decimal(d["total"]),
                    date=date(y, m, day),
                    currency="IDR",
                    party=d["merchant"]["name"],
                    payment_method=method,
                )
            )
    return bank_records, doc_records


def test_ac007_8_s1_reconciliation_accuracy_and_ambiguity(recon_policy):
    """S1: Normal half-year has ≥ 85% automatic match rate, 0 wrong automatic matches,
    and February ambiguous pair st-02#8 is PROPOSED (not AUTO)."""
    s1_truth_file = SYNTH_DIR / "S1" / "seed-1" / "truth.json"
    if not s1_truth_file.exists():
        pytest.skip(f"Synthetic scenario S1 not found at {s1_truth_file}")

    with s1_truth_file.open(encoding="utf-8") as f:
        truth = json.load(f)

    bank_records, doc_records = _records_from_truth(truth)
    allocations = assign_matches(
        bank_records, doc_records, recon_policy, workspace_currency="IDR", decisions=Decisions()
    )

    auto_allocs = [a for a in allocations if a.status == "CONFIRMED"]
    truth_matches = [
        m for m in truth["matches"] if m["kind"].startswith("BANK_") and m["kind"] != "BANK_LEDGER"
    ]
    truth_auto_pairs = {
        (tuple(m["bank"]), tuple(m["documents"])) for m in truth_matches if m["expect"] == "AUTO"
    }
    runtime_auto_pairs = {(a.left_ids, a.right_ids) for a in auto_allocs}

    # 1. 0 wrong automatic matches (no false positives)
    wrong_auto = runtime_auto_pairs - truth_auto_pairs
    assert not wrong_auto, f"Found wrong automatic matches: {wrong_auto}"

    # 2. Match rate ≥ 85%
    rate = len(auto_allocs) / len(truth_matches)
    assert rate >= 0.85, f"Expected match rate >= 85%, got {rate:.1%}"

    # 3. February ambiguous pair is PROPOSED, not AUTO
    feb_pair = next((a for a in allocations if "st-02#8" in a.left_ids), None)
    assert feb_pair is not None, "Expected allocation for st-02#8"
    assert feb_pair.status == "PROPOSED"
    assert feb_pair.method is None


def test_ac007_7_s5_equals_s1_order_independence(recon_policy):
    """S5: Exact same documents as S1 in reverse upload order produce identical matches."""
    s1_truth_file = SYNTH_DIR / "S1" / "seed-1" / "truth.json"
    s5_truth_file = SYNTH_DIR / "S5" / "seed-1" / "truth.json"
    if not s1_truth_file.exists() or not s5_truth_file.exists():
        pytest.skip("Synthetic scenarios S1 or S5 not found")

    with s1_truth_file.open(encoding="utf-8") as f:
        truth_s1 = json.load(f)
    with s5_truth_file.open(encoding="utf-8") as f:
        truth_s5 = json.load(f)

    b1, d1 = _records_from_truth(truth_s1)
    b5, d5 = _records_from_truth(truth_s5)

    allocs_s1 = assign_matches(
        b1, d1, recon_policy, workspace_currency="IDR", decisions=Decisions()
    )
    allocs_s5 = assign_matches(
        b5, d5, recon_policy, workspace_currency="IDR", decisions=Decisions()
    )

    s1_tuples = sorted((a.left_ids, a.right_ids, a.status, a.method, a.score) for a in allocs_s1)
    s5_tuples = sorted((a.left_ids, a.right_ids, a.status, a.method, a.score) for a in allocs_s5)

    assert s1_tuples == s5_tuples
    assert len(allocs_s1) > 0


def test_ac007_11_s4_and_double_payment_checks(recon_policy, forensics_policy):
    """S4: May raises X08_SUPPLIER_ACCOUNT_CHANGED (HIGH); April raises two R02 findings.
    Double-payment fixture raises D07_DOUBLE_PAYMENT (HIGH)."""
    s4_truth_file = SYNTH_DIR / "S4" / "seed-1" / "truth.json"
    dp_truth_file = SYNTH_DIR / "fixtures" / "double-payment" / "truth.json"
    s1_truth_file = SYNTH_DIR / "S1" / "seed-1" / "truth.json"
    if not s4_truth_file.exists() or not dp_truth_file.exists():
        pytest.skip("Synthetic S4 or double-payment fixture not found")

    with s4_truth_file.open(encoding="utf-8") as f:
        truth_s4 = json.load(f)

    invoices: list[Invoice] = []
    all_lines: list[BankLine] = []

    for d in truth_s4["documents"]:
        if d["docType"] in ("SALES_INVOICE", "PURCHASE_INVOICE"):
            kind = "SALES" if d["docType"] == "SALES_INVOICE" else "PURCHASE"
            pay_to = d.get("payTo", {}).get("accountNumber")
            if pay_to:
                pay_to = "••••" + pay_to[-4:]
            invoices.append(
                Invoice(
                    invoice_id=d["key"],
                    doc_id="doc_" + d["key"],
                    kind=kind,
                    number=d["number"],
                    issuer_name=d["issuer"]["name"],
                    buyer_name=d["billTo"]["name"],
                    issue_date=date.fromisoformat(d["issueDate"]),
                    month=d["issueDate"][:7],
                    total=Decimal(d["total"]),
                    currency="IDR",
                    due_date=date.fromisoformat(d["dueDate"]),
                    pay_to_masked=pay_to,
                )
            )
        elif d["docType"] == "BANK_STATEMENT":
            for r in d["rows"]:
                amount = Decimal(r["credit"]) if r["credit"] else -Decimal(r["debit"])
                balance = Decimal(r["balance"]) if r.get("balance") else None
                all_lines.append(
                    BankLine(
                        tx_id=r["key"],
                        doc_id="doc_" + d["file"],
                        page=r["page"],
                        row_index=r["rowIndex"],
                        date=date.fromisoformat(r["date"]),
                        month=r["date"][:7],
                        description=r["description"],
                        amount=amount,
                        balance=balance,
                    )
                )

    # 1. S4 May: X08_SUPPLIER_ACCOUNT_CHANGED (HIGH)
    may_lines = [ln for ln in all_lines if ln.month == "2026-05"]
    may_ctx = MonthContext(
        month="2026-05",
        policy=forensics_policy,
        reconciliation=recon_policy,
        workspace_currency="IDR",
        statements=[
            StatementSpan(
                "doc_s4_may",
                "Archipelago Commerce Bank ••••4821",
                date(2026, 5, 1),
                date(2026, 5, 31),
                Decimal(0),
                Decimal(0),
            )
        ],
        lines=may_lines,
        all_lines=all_lines,
        invoices=invoices,
        receipts=[],
        allocations=[],
        negative_days=0,
    )
    may_findings = run_month_checks(may_ctx)
    x08 = [f for f in may_findings if f.code == "X08_SUPPLIER_ACCOUNT_CHANGED"]
    assert len(x08) == 1
    assert x08[0].severity == "HIGH"
    assert x08[0].facts["earlierAccount"] == "••••3318"
    assert x08[0].facts["newAccount"] == "••••3108"

    # 2. S4 April: two R02_SUPPLIER_INVOICE_UNKNOWN_PARTY
    apr_lines = [ln for ln in all_lines if ln.month == "2026-04"]
    apr_ctx = MonthContext(
        month="2026-04",
        policy=forensics_policy,
        reconciliation=recon_policy,
        workspace_currency="IDR",
        statements=[
            StatementSpan(
                "doc_s4_apr",
                "Archipelago Commerce Bank ••••4821",
                date(2026, 4, 1),
                date(2026, 4, 30),
                Decimal(0),
                Decimal(0),
            )
        ],
        lines=apr_lines,
        all_lines=all_lines,
        invoices=invoices,
        receipts=[],
        allocations=[],
        negative_days=0,
    )
    apr_findings = run_month_checks(apr_ctx)
    r02 = [f for f in apr_findings if f.code == "R02_SUPPLIER_INVOICE_UNKNOWN_PARTY"]
    assert len(r02) == 2

    # 3. Double-payment fixture: D07_DOUBLE_PAYMENT (HIGH)
    with dp_truth_file.open(encoding="utf-8") as f:
        truth_dp = json.load(f)
    with s1_truth_file.open(encoding="utf-8") as f:
        truth_s1 = json.load(f)

    dp_lines: list[BankLine] = []
    st_dp = truth_dp["documents"][0]
    for r in st_dp["rows"]:
        amount = Decimal(r["credit"]) if r["credit"] else -Decimal(r["debit"])
        dp_lines.append(
            BankLine(
                tx_id=r["key"],
                doc_id="doc_statement",
                page=1,
                row_index=int(r["key"].split("#")[1]),
                date=date.fromisoformat(r["date"]),
                month="2026-03",
                description=r["description"],
                amount=amount,
                balance=Decimal(r["balance"]),
            )
        )

    inv_data = next(
        d for d in truth_s1["documents"] if d["file"] == "inv-purchase-2026-03-01.pdf"
    )
    inv = Invoice(
        invoice_id=inv_data["key"],
        doc_id="doc_inv",
        kind="PURCHASE",
        number=inv_data["number"],
        issuer_name=inv_data["issuer"]["name"],
        buyer_name=inv_data["billTo"]["name"],
        issue_date=date.fromisoformat(inv_data["issueDate"]),
        month="2026-03",
        total=Decimal(inv_data["total"]),
        currency="IDR",
        due_date=date.fromisoformat(inv_data["dueDate"]),
    )

    dp_ctx = MonthContext(
        month="2026-03",
        policy=forensics_policy,
        reconciliation=recon_policy,
        workspace_currency="IDR",
        statements=[
            StatementSpan(
                "doc_statement",
                "Archipelago Commerce Bank ••••4821",
                date(2026, 3, 1),
                date(2026, 3, 31),
                Decimal(0),
                Decimal(0),
            )
        ],
        lines=dp_lines,
        all_lines=dp_lines,
        invoices=[inv],
        receipts=[],
        allocations=[],
        negative_days=0,
    )
    dp_findings = run_month_checks(dp_ctx)
    d07 = [f for f in dp_findings if f.code == "D07_DOUBLE_PAYMENT"]
    assert len(d07) == 1
    assert d07[0].severity == "HIGH"
