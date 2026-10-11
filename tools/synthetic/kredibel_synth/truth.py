"""truth.json (docs/18 §6, AC-002-12).

What was generated, what was changed, and what Kredibel should conclude: written from the books
and the tamper log, never re-derived from the files.
"""

import json
from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any

from . import world
from .model import BankRow, InvoiceData, LedgerRow, ReceiptData, StatementData
from .output import LEDGER_FILE
from .render_statement import bank_reference, statement_file
from .scenarios import Scenario

GENERATOR = {"name": "kredibel-synth", "version": "0.1.0"}
CLEAN: dict[str, Any] = {
    "verdict": "CLEAN",
    "riskLevel": "LOW",
    "findingsP0": [],
    "duplicate": None,
}


def _money(value: Decimal | None) -> str | None:
    return None if value is None else f"{value:.2f}"


def workspace_as_onboarded() -> dict[str, Any]:
    """What the user typed at onboarding: no tax ID, no address (docs/18 §2, SD-7)."""
    return {
        "name": world.BUSINESS.name,
        "entityType": "COMPANY",
        "currency": "IDR",
        "timezone": "Asia/Jakarta",
        "profile": {
            "legalName": world.BUSINESS.name,
            "legalForm": world.LEGAL_FORM,
            "industry": world.INDUSTRY,
        },
        "bankAccounts": [
            {
                "bankName": world.BANK_NAME,
                "accountNumber": world.ACCOUNT,
                "holderName": world.HOLDER,
                "ledgerAccountCode": "1110",
            }
        ],
    }


# ---------------------------------------------------------------------------- documents


def _row(row: BankRow, page: int, account: str) -> dict[str, Any]:
    return {
        "key": row.key,
        "rowIndex": row.row_index,
        "page": page,
        "date": row.date.isoformat(),
        "description": row.description,
        "bankRef": bank_reference(row, account),
        "debit": _money(row.debit),
        "credit": _money(row.credit),
        "balance": _money(row.balance),
        "category": row.category,
        "riskTags": row.risk_tags,
    }


def _statement(sc: Scenario, st: StatementData) -> dict[str, Any]:
    pages = sc.row_pages
    file = statement_file(st.month)
    tampering = [t for t in sc.tampering if t.file == file]
    expected = dict(CLEAN)
    if any(t.technique == "T1" for t in tampering):
        expected = {
            "verdict": "TAMPERED",
            "riskLevel": "CRITICAL",
            "findingsP0": [
                "A01_RUNNING_BALANCE_BREAK",
                "A02_OPENING_CLOSING_MISMATCH",
                "M01_EDITING_SOFTWARE_PRODUCER",
                "M02_MODIFIED_AFTER_CREATION",
                "M03_MULTIPLE_REVISIONS",
                "M04_FONT_ANOMALY_IN_VALUES",
            ],
            "duplicate": None,
        }
    if sc.scanned:
        expected = {**expected, "findingsP0": [*expected["findingsP0"], "M06_IMAGE_ONLY"]}
    return {
        "file": file,
        "key": f"statement-{st.month}",
        "docType": "BANK_STATEMENT",
        "bank": st.bank_name,
        "accountNumber": st.account_number,
        "holder": st.holder,
        "holderAddress": st.holder_address,
        "currency": "IDR",
        "period": {"start": st.period_start.isoformat(), "end": st.period_end.isoformat()},
        "opening": _money(st.opening),
        "closing": _money(st.closing),
        "totalDebits": _money(st.total_debits),
        "totalCredits": _money(st.total_credits),
        "rows": [_row(r, pages[r.key], st.account_number) for r in st.rows],
        "tampering": [
            {"technique": t.technique, **_t1_fields(t.details)}
            for t in tampering
            if t.technique == "T1"
        ],
        "expected": expected,
    }


def _t1_fields(details: dict[str, Any]) -> dict[str, Any]:
    return {k: details[k] for k in ("rowIndex", "field", "before", "after") if k in details}


def _invoice(sc: Scenario, inv: InvoiceData, paid: set[str]) -> dict[str, Any]:
    if inv.key in paid:
        payment = "PAID"
    elif inv.due_date > sc.books.statements[world.MONTHS[-1]].period_end:
        payment = "NOT_DUE"
    else:
        payment = "UNPAID"
    expected: dict[str, Any] = {**CLEAN, "payment": payment}
    if sc.scanned:
        expected["findingsP0"] = ["M06_IMAGE_ONLY"]
    return {
        "file": inv.file,
        "key": inv.key,
        "docType": "SALES_INVOICE" if inv.kind == "SALES" else "PURCHASE_INVOICE",
        "number": inv.number,
        "issueDate": inv.issue_date.isoformat(),
        "dueDate": inv.due_date.isoformat(),
        "issuer": {
            "name": inv.issuer.name,
            "address": list(inv.issuer.address),
            "taxId": inv.issuer.tax_id,
        },
        "billTo": {
            "name": inv.bill_to.name,
            "address": list(inv.bill_to.address),
            "taxId": inv.bill_to.tax_id,
        },
        "lines": [
            {
                "description": ln.description,
                "quantity": ln.quantity,
                "unitPrice": _money(ln.unit_price),
                "amount": _money(ln.amount),
            }
            for ln in inv.lines
        ],
        "subtotal": _money(inv.subtotal),
        "vatRate": f"{inv.vat_rate}",
        "vat": _money(inv.vat),
        "total": _money(inv.total),
        "currency": "IDR",
        "payTo": {
            "bankName": inv.pay_to.bank_name,
            "accountNumber": inv.pay_to.account_number,
            "holder": inv.pay_to.holder,
        },
        "expected": expected,
    }


def _receipt(sc: Scenario, rec: ReceiptData) -> dict[str, Any]:
    expected: dict[str, Any] = dict(CLEAN)
    if sc.scanned and rec.form == "pdf":
        expected["findingsP0"] = ["M06_IMAGE_ONLY"]
    return {
        "file": rec.file,
        "key": rec.key,
        "docType": "RECEIPT",
        "merchant": {"name": rec.merchant.name, "address": list(rec.merchant.address)},
        "receiptNo": rec.receipt_no,
        "issuedAt": rec.issued_at.isoformat(),
        "items": [
            {
                "description": i.description,
                "quantity": i.quantity,
                "unitPrice": _money(i.unit_price),
                "amount": _money(i.amount),
            }
            for i in rec.items
        ],
        "subtotal": _money(rec.subtotal),
        "vat": _money(rec.vat),
        "total": _money(rec.total),
        "payment": rec.payment,
        "form": rec.form,
        "expected": expected,
    }


def _entry(e: LedgerRow) -> dict[str, Any]:
    return {
        "key": e.key,
        "date": e.date.isoformat(),
        "journal": e.journal,
        "account": e.account,
        "accountName": e.account_name,
        "description": e.description,
        "reference": e.reference,
        "debit": _money(e.debit),
        "credit": _money(e.credit),
    }


def _ledger(sc: Scenario) -> dict[str, Any]:
    missing = [r.key for r in sc.books.bank_rows if not r.in_ledger]
    return {
        "file": LEDGER_FILE,
        "key": "ledger-2026-H1",
        "docType": "LEDGER_EXPORT",
        "format": "CSV",
        "columns": [
            "Date",
            "Journal",
            "Account",
            "Account Name",
            "Description",
            "Reference",
            "Debit",
            "Credit",
        ],
        "dateFormat": "dd/mm/yyyy",
        "bankAccountCode": "1110",
        "entries": [_entry(e) for e in sc.books.ledger],
        "bankLinesMissingFromLedger": missing,
        "duplicateEntries": sc.ledger_duplicates,
        "expected": {
            "findingsP0": ["D06_LEDGER_ENTRY_DUPLICATE"] if sc.ledger_duplicates else [],
            "heldEntries": sc.ledger_duplicates,
        },
    }


def _duplicates(sc: Scenario) -> list[dict[str, Any]]:
    out = []
    for file, dup in sc.duplicates.items():
        if dup.code == "D01_EXACT_FILE_DUPLICATE":
            expected: dict[str, Any] = {
                "verdict": None,
                "riskLevel": None,
                "findingsP0": [dup.code],
                "duplicate": {"code": dup.code, "of": dup.of, "held": False, "read": False},
            }
        else:
            findings = [dup.code] + (["M06_IMAGE_ONLY"] if file.endswith("-scan.pdf") else [])
            expected = {
                "verdict": "CLEAN",
                "riskLevel": dup.severity,
                "findingsP0": findings,
                "duplicate": {"code": dup.code, "of": dup.of, "held": True, "read": True},
            }
        out.append(
            {"file": file, "key": file.rsplit(".", 1)[0], "copyOf": dup.of, "expected": expected}
        )
    return out


# ---------------------------------------------------------------------------- months


def _months(sc: Scenario) -> dict[str, Any]:
    items: dict[str, Counter[str]] = defaultdict(Counter)
    findings: dict[str, list[str]] = defaultdict(list)
    risk: dict[str, str] = {}
    items["2026-02"]["PROPOSED_MATCH"] += 1
    items["2026-06"]["UNMATCHED_BANK_LINE"] += 1
    findings["2026-06"].append("X09_LEDGER_BANK_MISMATCH")
    risk["2026-06"] = "MEDIUM"
    if sc.name == "S2":
        items["2026-03"]["LEDGER_DIFFERENCE"] += 1
        findings["2026-03"].append("X09_LEDGER_BANK_MISMATCH")
        risk["2026-03"] = "CRITICAL"
    if sc.name == "S3":
        for month in ("2026-02", "2026-03", "2026-05", "2026-06"):
            items[month]["POSSIBLE_DUPLICATE"] += 1
            risk[month] = "MEDIUM"
    if sc.name == "S4":
        items["2026-04"]["UNMATCHED_DOCUMENT"] += 2
        findings["2026-04"] += ["R02_SUPPLIER_INVOICE_UNKNOWN_PARTY"] * 2
        risk["2026-04"] = "MEDIUM"
        findings["2026-05"].append("X08_SUPPLIER_ACCOUNT_CHANGED")
        risk["2026-05"] = "HIGH"
    out: dict[str, Any] = {}
    for month, st in sc.books.statements.items():
        credits, debits = _shown_totals(sc, st)
        count = items[month]
        out[month] = {
            "state": "NEEDS_REVIEW" if sum(count.values()) else "RECONCILED",
            "riskLevel": risk.get(month, "LOW"),
            "autoMatchRateMin": "0.85",
            "monthFindings": findings[month],
            "reviewItems": dict(sorted(count.items())),
            "figures": {
                "moneyIn": _money(credits),
                "moneyOut": _money(debits),
                "net": _money(credits - debits),
                "opening": _money(st.opening),
                "closing": _money(st.closing),
            },
        }
    return out


def _shown_totals(sc: Scenario, st: StatementData) -> tuple[Decimal, Decimal]:
    """Figures from the values the documents show (T1's edited credit counts as printed)."""
    credits, debits = st.total_credits, st.total_debits
    for t in sc.tampering:
        if t.technique == "T1" and t.file == statement_file(st.month):
            credits += Decimal(t.details["after"]) - Decimal(t.details["before"])
    return credits, debits


# ---------------------------------------------------------------------- suggestions, parties, flows


def _counterparties(sc: Scenario) -> list[dict[str, Any]]:
    books = sc.books
    accounts: dict[str, set[str]] = defaultdict(set)
    for inv in books.purchases:
        accounts[inv.issuer.name].add(inv.pay_to.account_number)
    out = [
        {"name": c.upper(), "roles": ["CLIENT"]}
        for c in sorted({inv.bill_to.name for inv in books.sales})
    ]
    out += [
        {"name": s.upper(), "roles": ["SUPPLIER"], "accountsSeen": len(accounts[s])}
        for s in sorted(accounts)
    ]
    out += [
        {"name": m.upper(), "roles": ["SUPPLIER"]}
        for m in sorted({r.merchant.name for r in books.receipts})
    ]
    out += [
        {"name": world.PARTNER.upper(), "roles": ["OWNER"]},
        {"name": "VAT payments", "roles": ["GOVERNMENT"]},
    ]
    return out


_USES = {
    "supplier": "Suppliers",
    "card": "Suppliers",
    "payroll": "Payroll",
    "rent": "Rent and utilities",
    "utility": "Rent and utilities",
    "vat": "Tax",
    "loan": "Loan payments",
    "drawing": "Owner drawings",
    "fee": "Other spending",
}


def _flows(sc: Scenario) -> dict[str, Any]:
    sources: Counter[str] = Counter()
    uses: Counter[str] = Counter()
    for row in sc.books.bank_rows:
        if row.credit is not None and row.party:
            sources[row.party.upper()] += int(row.credit)
        elif row.debit is not None:
            uses[_USES[row.flow]] += int(row.debit)
    return {
        "period": f"{world.MONTHS[0]}..{world.MONTHS[-1]}",
        "topSources": [name for name, _ in sources.most_common(2)],
        "topUses": [name for name, _ in uses.most_common(2)],
    }


def _suggestions() -> list[dict[str, Any]]:
    return [
        {"field": "TAX_ID", "value": {"taxId": world.BUSINESS.tax_id}, "confidence": "HIGH"},
        {
            "field": "ADDRESS",
            "value": {"line1": world.BUSINESS.address[0], "city": "Bandung", "postalCode": "40135"},
            "confidence": "MEDIUM",
        },
    ]


# ---------------------------------------------------------------------------- the file


def truth(sc: Scenario) -> dict[str, Any]:
    books = sc.books
    paid = {
        d
        for m in books.matches
        if m.kind in ("BANK_SALES_INVOICE", "BANK_PURCHASE_INVOICE")
        for d in m.documents
    }
    documents: list[dict[str, Any]] = [_ledger(sc)]
    documents += [_statement(sc, st) for st in books.statements.values()]
    documents += [_invoice(sc, inv, paid) for inv in books.invoices]
    documents += [_receipt(sc, rec) for rec in books.receipts]
    documents += _duplicates(sc)
    return {
        "scenario": sc.name,
        "seed": sc.seed,
        "title": sc.title,
        "variant": "scan" if sc.scanned else "original",
        "generator": GENERATOR,
        "watermark": world.WATERMARK,
        "workspace": workspace_as_onboarded(),
        "uploadOrder": sc.upload_order,
        "documents": documents,
        "tampering": [
            {"technique": t.technique, "file": t.file, **t.details} for t in sc.tampering
        ],
        "matches": [
            {
                "month": m.month,
                "kind": m.kind,
                "bank": m.bank,
                "documents": m.documents,
                "ledger": m.ledger,
                "expect": m.expect,
                "reasons": m.reasons,
                "score": f"{m.score:.3f}",
                **({"note": m.note} if m.note else {}),
            }
            for m in books.matches
        ],
        "months": _months(sc),
        "expectedSuggestions": _suggestions(),
        "expectedCounterparties": _counterparties(sc),
        "expectedFlows": _flows(sc),
    }


def dumps(data: dict[str, Any]) -> bytes:
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def readme(sc: Scenario) -> bytes:
    variant = " (scanned: every PDF is an image-only scan)" if sc.scanned else ""
    text = (
        f"# {sc.name}: {sc.title}{variant}\n\n{sc.summary}\n\n"
        f"Seed {sc.seed}. Upload the files in `upload-order.txt` order; expectations are in "
        f"`truth.json` (docs/18 §6).\n\n"
        f"{world.WATERMARK}. Every business, person, bank and number here is fictional.\n"
    )
    return text.encode("utf-8")
