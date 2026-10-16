"""A synthetic scenario's books in the in-memory stores, as the document workflow leaves them.

`tools/synthetic/out/<S>/seed-1/truth.json` (docs/18) says what every synthetic file holds. The
seeding writes documents as `DONE`, their bank lines, invoices, receipts and ledger rows, and the
workspace's declared account with its ledger code; the readers are not under test here (spec 012
evaluates them). The month runs, the review queue, the figures and the money flow are, through the
same API the app uses. Tests skip when the scenarios were not generated (`make synth`).
"""

import hashlib
import json
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from app.adapters.cloud_tasks import InlineTaskQueue
from app.domain.accounts import mask_tax_id
from app.domain.categorize import by_rules
from app.domain.duplicates import ledger_entry_duplicates
from app.domain.models.bank_line import BankLine
from app.domain.models.document import (
    DocStatus,
    DocType,
    Document,
    DuplicateDecision,
    DuplicateInfo,
    DuplicateKind,
)
from app.domain.models.invoice import Invoice, InvoiceLine, Receipt, ReceiptItem
from app.domain.models.workspace import BankAccount
from app.domain.normalize import extract_counterparty, payment_method
from app.domain.profit_loss import LedgerRow

SYNTH_DIR = Path(__file__).resolve().parents[3] / "tools" / "synthetic" / "out"
ORG = "org_1"
UPLOADED_AT = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
MONTHS = [f"2026-0{m}" for m in range(1, 7)]
ACCOUNT_MASKED = "••••4821"
BANK = "Archipelago Commerce Bank"


def load_truth(scenario: str) -> dict[str, Any]:
    path = SYNTH_DIR / scenario / "seed-1" / "truth.json"
    if not path.exists():
        pytest.skip(f"Synthetic scenario {scenario} not generated (make synth): {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def scenario_file(scenario: str, name: str) -> Path:
    return SYNTH_DIR / scenario / "seed-1" / name


def doc_id_of(key: str) -> str:
    return f"doc_{key}"


def _masked_tax(raw: str | None) -> str | None:
    return mask_tax_id(raw) if raw else None


def _money(text: str | None) -> Decimal | None:
    return None if text is None else Decimal(text)


def _sha(scenario: str, file_name: str) -> str:
    path = scenario_file(scenario, file_name)
    data = path.read_bytes() if path.exists() else file_name.encode()
    return hashlib.sha256(data).hexdigest()


def _document(
    scenario: str,
    entry: dict[str, Any],
    doc_type: DocType,
    months: list[str],
    *,
    meta: dict[str, Any] | None = None,
    pages: int = 1,
) -> Document:
    file_name = entry["file"]
    path = scenario_file(scenario, file_name)
    suffix = file_name.rsplit(".", 1)[-1].lower()
    content_type = {"pdf": "application/pdf", "csv": "text/csv", "jpg": "image/jpeg"}.get(
        suffix, "application/octet-stream"
    )
    return Document(
        doc_id=doc_id_of(entry["key"]),
        file_name=file_name,
        content_type=content_type,
        size_bytes=path.stat().st_size if path.exists() else 1000,
        page_count=pages,
        sha256=_sha(scenario, file_name),
        gcs_path=f"orgs/{ORG}/docs/{doc_id_of(entry['key'])}/original.{suffix}",
        uploaded_by="u-1",
        uploaded_at=UPLOADED_AT,
        doc_type=doc_type,
        type_confidence=Decimal("0.97"),
        status=DocStatus.DONE,
        months=months,
        statement_meta=meta if doc_type == DocType.BANK_STATEMENT else None,
        ledger_meta=meta if doc_type == DocType.LEDGER_EXPORT else None,
    )


def bank_lines(entry: dict[str, Any], doc_id: str, policy, framework: str) -> list[BankLine]:
    """The statement's rows as read lines: code's rules categorize what they can, the truth's
    category stands in for the model's answer on the rest (its own eval is spec 012)."""
    out: list[BankLine] = []
    for row in entry["rows"]:
        amount = Decimal(row["credit"]) if row["credit"] else -Decimal(row["debit"])
        counterparty = extract_counterparty(row["description"])
        decided, tags = by_rules(row["description"], counterparty, amount, policy)
        category = decided.category if decided else row["category"]
        if category not in policy.categories:
            category = "UNKNOWN"
        out.append(
            BankLine(
                tx_id=row["key"],
                doc_id=doc_id,
                page=row["page"],
                row_index=row["rowIndex"],
                date=date.fromisoformat(row["date"]),
                month=row["date"][:7],
                description=row["description"],
                amount=amount,
                balance=_money(row.get("balance")),
                counterparty_name=counterparty,
                # The synthetic PDFs print every value in their text layer: the reading is grounded.
                consensus={
                    f: {"status": "AGREED", "page": row["page"]}
                    for f in ("date", "description", "amount", "balance")
                },
                category=category,
                cashflow_class=policy.categories[category].cashflow_class(framework),
                risk_tags=sorted({*tags, *row.get("riskTags", [])}),
                categorized_by="RULE" if decided else "MODEL",
            )
        )
    return out


def statement_meta(entry: dict[str, Any]) -> dict[str, Any]:
    address = entry.get("holderAddress")
    return {
        "bankName": entry["bank"],
        "accountHolder": entry.get("holder"),
        "holderAddress": "\n".join(address) if isinstance(address, list) else address,
        "accountMasked": f"••••{entry['accountNumber'][-4:]}",
        "currency": entry["currency"],
        "periodStart": entry["period"]["start"],
        "periodEnd": entry["period"]["end"],
        "openingMinor": int(Decimal(entry["opening"]) * 100),
        "closingMinor": int(Decimal(entry["closing"]) * 100),
    }


def invoice(entry: dict[str, Any], doc_id: str, own_name: str) -> Invoice:
    kind = "SALES" if entry["issuer"]["name"].casefold() == own_name.casefold() else "PURCHASE"
    pay_to = (entry.get("payTo") or {}).get("accountNumber")
    return Invoice(
        invoice_id=entry["key"],
        doc_id=doc_id,
        kind=kind,
        number=entry["number"],
        issuer_name=entry["issuer"]["name"],
        buyer_name=entry["billTo"]["name"],
        issue_date=date.fromisoformat(entry["issueDate"]),
        month=entry["issueDate"][:7],
        total=Decimal(entry["total"]),
        currency=entry["currency"],
        issuer_tax_id=_masked_tax(entry["issuer"].get("taxId")),  # stored masked (docs/14 §6)
        buyer_tax_id=_masked_tax(entry["billTo"].get("taxId")),
        due_date=date.fromisoformat(entry["dueDate"]),
        subtotal=_money(entry.get("subtotal")),
        tax=_money(entry.get("vat")),
        pay_to_bank=(entry.get("payTo") or {}).get("bankName"),
        pay_to_masked=f"••••{pay_to[-4:]}" if pay_to else None,
        supply_kind="GOODS",
        consensus={
            f: {"status": "AGREED", "page": 1} for f in ("issuerTaxId", "total", "issueDate")
        },
        lines=[
            InvoiceLine(
                ln["description"],
                Decimal(str(ln["quantity"])),
                _money(ln.get("unitPrice")),
                _money(ln.get("amount")),
            )
            for ln in entry["lines"]
        ],
        pages=[1],
    )


def receipt(entry: dict[str, Any], doc_id: str) -> Receipt:
    method = payment_method(entry.get("payment"))  # as the reader's text is normalized
    return Receipt(
        receipt_id=entry["key"],
        doc_id=doc_id,
        merchant_name=entry["merchant"]["name"],
        date=date.fromisoformat(entry["issuedAt"][:10]),
        month=entry["issuedAt"][:7],
        total=Decimal(entry["total"]),
        currency="IDR",
        number=entry.get("receiptNo"),
        time=entry["issuedAt"][11:16],
        tax=_money(entry.get("vat")),
        payment_method=method,
        items=[ReceiptItem(i["description"], _money(i.get("amount"))) for i in entry["items"]],
        pages=[1],
    )


def ledger_rows(entry: dict[str, Any], doc_id: str) -> list[LedgerRow]:
    return [
        LedgerRow(
            entry_id=row["key"],
            doc_id=doc_id,
            row_number=number,
            date=date.fromisoformat(row["date"]),
            account_code=row["account"],
            account_name=row["accountName"],
            debit=Decimal(row["debit"] or "0"),
            credit=Decimal(row["credit"] or "0"),
            currency="IDR",
            posting_status="POSTED",
            journal_id=row.get("reference")
            or None,  # the reference column, as parse_ledger keeps it
            description=row.get("description") or "",
            reference=row.get("reference") or None,
        )
        for number, row in enumerate(entry["entries"], start=1)
    ]


async def seed(deps, scenario: str, truth: dict[str, Any], *, copies: bool = False) -> None:
    """The scenario's books in the stores. With `copies`, the scenario's content duplicates are held
    as the duplicate node leaves them (docs/08 §2.1): read, pending a person's decision."""
    workspace = await deps.workspace_repo.get_workspace(ORG)
    own_name = workspace.name
    framework = workspace.profile.accounting_framework
    deps.workspace_repo.bank_accounts.setdefault(ORG, {})["acc_1"] = BankAccount(
        account_id="acc_1",
        bank_name=BANK,
        account_masked=ACCOUNT_MASKED,
        holder_name=own_name.upper(),
        ledger_account_code=truth["workspace"]["bankAccounts"][0]["ledgerAccountCode"],
    )
    originals: dict[str, dict[str, Any]] = {}
    for entry in truth["documents"]:
        if "copyOf" in entry:
            continue
        originals[entry["file"]] = entry
        doc_id = doc_id_of(entry["key"])
        match entry["docType"]:
            case "BANK_STATEMENT":
                months = [entry["period"]["start"][:7]]
                doc = _document(
                    scenario,
                    entry,
                    DocType.BANK_STATEMENT,
                    months,
                    meta=statement_meta(entry),
                    pages=2,
                )
                await deps.doc_repo.save_document(ORG, doc)
                await deps.bank_lines.replace_document_lines(
                    ORG, doc_id, bank_lines(entry, doc_id, deps.categories, framework)
                )
            case "SALES_INVOICE" | "PURCHASE_INVOICE":
                record = invoice(entry, doc_id, own_name)
                doc_type = (
                    DocType.SALES_INVOICE if record.kind == "SALES" else DocType.PURCHASE_INVOICE
                )
                await deps.doc_repo.save_document(
                    ORG, _document(scenario, entry, doc_type, [record.month or ""])
                )
                await deps.invoices.replace_for_document(ORG, doc_id, [record])
            case "RECEIPT":
                record = receipt(entry, doc_id)
                await deps.doc_repo.save_document(
                    ORG, _document(scenario, entry, DocType.RECEIPT, [record.month or ""])
                )
                await deps.receipts.replace_for_document(ORG, doc_id, [record])
            case "LEDGER_EXPORT":
                meta = {"mappingStatus": "CONFIRMED", "rowsImported": len(entry["entries"])}
                await deps.doc_repo.save_document(
                    ORG, _document(scenario, entry, DocType.LEDGER_EXPORT, MONTHS, meta=meta)
                )
                rows = ledger_rows(entry, doc_id)
                ledger_copies = {c.entry_id: c for c in ledger_entry_duplicates(rows)}
                rows = [
                    r.model_copy(
                        update={
                            "held_as_duplicate": True,
                            "duplicate": {
                                "code": "D06_LEDGER_ENTRY_DUPLICATE",
                                "ofEntryId": ledger_copies[r.entry_id].of_entry_id,
                                "ofDocId": doc_id,
                                "decision": "PENDING",
                            },
                        }
                    )
                    if r.entry_id in ledger_copies
                    else r
                    for r in rows
                ]
                await deps.ledger_repo.save_rows(ORG, rows)
    if not copies:
        return
    for entry in truth["documents"]:
        dup = (entry.get("expected") or {}).get("duplicate")
        if "copyOf" not in entry or not dup or not dup["held"]:
            continue  # an exact copy (D01) is refused at upload and never read
        original = originals[entry["copyOf"]]
        of_doc = await deps.doc_repo.get_document(ORG, doc_id_of(original["key"]))
        assert of_doc is not None
        copy_id = doc_id_of(entry["key"])
        copy = replace(
            _document(
                scenario,
                {**original, **entry},
                of_doc.doc_type,
                of_doc.months,
                meta=of_doc.statement_meta,
                pages=of_doc.page_count,
            ),
            duplicate=DuplicateInfo(
                kind=DuplicateKind.CONTENT,
                code=dup["code"],
                of_doc_id=of_doc.doc_id,
                decision=DuplicateDecision.PENDING,
            ),
            held_as_duplicate=True,
        )
        await deps.doc_repo.save_document(ORG, copy)
        if of_doc.doc_type == DocType.BANK_STATEMENT:
            lines = bank_lines(original, copy_id, deps.categories, framework)
            lines = [replace(ln, tx_id=f"{ln.tx_id}~copy") for ln in lines]
            await deps.bank_lines.replace_document_lines(ORG, copy_id, lines)
        elif of_doc.doc_type == DocType.RECEIPT:
            rec = replace(receipt(original, copy_id), receipt_id=f"{entry['key']}")
            await deps.receipts.replace_for_document(ORG, copy_id, [rec])
        else:
            inv = replace(invoice(original, copy_id, own_name), invoice_id=f"{entry['key']}")
            await deps.invoices.replace_for_document(ORG, copy_id, [inv])


async def run_months(deps, months: list[str] = MONTHS) -> None:
    """Every month once, in order, then the re-runs a run asked for (a payment found in one month
    settles a document of another), as the queue would on Cloud Run."""
    for month in months:
        generation, _ = await deps.month_repo.bump_generation(ORG, month)
        result = await deps.month_workflow_runner(ORG, month, generation, f"run_{month}")
        assert result.get("status") != "FAILED", result
    await drain(deps)


async def drain(deps) -> None:
    queue = deps.task_queue
    assert isinstance(queue, InlineTaskQueue)
    await queue.drain()


def expected_items(truth: dict[str, Any]) -> dict[str, dict[str, int]]:
    return {m: dict(v["reviewItems"]) for m, v in truth["months"].items() if v["reviewItems"]}


def count_items(items: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for item in items:
        by_kind = out.setdefault(item["month"], {})
        by_kind[item["kind"]] = by_kind.get(item["kind"], 0) + 1
    return {m: dict(sorted(v.items())) for m, v in sorted(out.items())}


def ledger_paid_receipts(truth: dict[str, Any]) -> set[str]:
    """Receipts the truth settles through a ledger entry alone (paid from a wallet or petty cash,
    booked, never on the statement). Document-to-ledger pairs are not built yet (spec 007), so
    the queue still asks about them."""
    bank_paid = {d for m in truth["matches"] if m["kind"] == "BANK_RECEIPT" for d in m["documents"]}
    ledger = {d for m in truth["matches"] if m["kind"] == "DOCUMENT_LEDGER" for d in m["documents"]}
    return {d for d in ledger - bank_paid if d.startswith("receipt-")}


def books_deps():
    """The API test deps with the clock after the half-year: nothing is "not yet due"."""
    from tests.fakes.clock import FixedClock
    from tests.integration.test_invoice_workflow import _deps

    deps, _ = _deps()
    deps._clock = FixedClock(UPLOADED_AT)
    return deps
