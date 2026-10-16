"""The Transactions table (spec 024, AC-024-6). Pure.

Each bank line with what Kredibel knows about it: its category and, from the category policy, its
cash-flow class under IFRS and under US GAAP, its profit-and-loss line and subledger (cash basis);
the model's confidence in the category when a model chose it; the weakest of its amount and date
readings; and the records its confirmed or proposed match points to.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.domain.categorize import CategoryPolicy
from app.domain.models.bank_line import BankLine
from app.domain.models.invoice import Invoice, Receipt
from app.domain.models.match import StoredMatch
from app.domain.profit_loss import LedgerRow, ProfitLossPolicy

# The weakest reading first: a value missing, then disputed, then read once, then agreed.
_READING_ORDER = ("MISSING", "CONFLICT", "SINGLE_SOURCE", "AGREED")


@dataclass(frozen=True)
class LinkedRecord:
    kind: Literal["INVOICE", "RECEIPT", "LEDGER_ENTRY"]
    record_id: str
    doc_id: str
    label: str


@dataclass(frozen=True)
class TransactionRow:
    line: BankLine
    category_label: str
    ifrs: str
    us_gaap: str
    pnl_line: str | None
    subledger: str | None
    confidence: Decimal | None
    reading: str
    match_kind: str | None
    linked: tuple[LinkedRecord, ...]


def _reading(line: BankLine) -> str:
    statuses = [
        "AGREED" if name in line.corrected_fields else str(line.consensus[name].get("status"))
        for name in ("amount", "date")
        if name in line.consensus
    ]
    known = [s for s in statuses if s in _READING_ORDER]
    return min(known, key=_READING_ORDER.index) if known else "SINGLE_SOURCE"


def transaction_rows(
    lines: list[BankLine],
    matches: list[StoredMatch],
    invoices: list[Invoice],
    receipts: list[Receipt],
    ledger: list[LedgerRow],
    categories: CategoryPolicy,
    profit_loss: ProfitLossPolicy,
) -> list[TransactionRow]:
    invoice_of = {i.invoice_id: i for i in invoices}
    receipt_of = {r.receipt_id: r for r in receipts}
    entry_of = {e.entry_id: e for e in ledger}
    live = [m for m in matches if m.status in ("CONFIRMED", "PROPOSED")]
    rows: list[TransactionRow] = []
    for line in sorted(lines, key=lambda ln: (ln.date, ln.doc_id, ln.row_index, ln.tx_id)):
        category = categories.categories.get(line.category)
        mine = sorted(
            (m for m in live if line.tx_id in m.bank_line_ids),
            key=lambda m: (m.status != "CONFIRMED", m.match_id),
        )
        match = mine[0] if mine else None
        linked: list[LinkedRecord] = []
        if match is not None:
            for invoice_id in match.invoice_ids:
                if inv := invoice_of.get(invoice_id):
                    party = inv.buyer_name if inv.kind == "SALES" else inv.issuer_name
                    linked.append(
                        LinkedRecord("INVOICE", invoice_id, inv.doc_id, inv.number or party or "")
                    )
            for receipt_id in match.receipt_ids:
                if rc := receipt_of.get(receipt_id):
                    label = rc.number or rc.merchant_name or ""
                    linked.append(LinkedRecord("RECEIPT", receipt_id, rc.doc_id, label))
            for entry_id in match.ledger_entry_ids:
                if entry := entry_of.get(entry_id):
                    label = entry.journal_id or entry.description or entry.account_name
                    linked.append(LinkedRecord("LEDGER_ENTRY", entry_id, entry.doc_id, label))
        pnl = category.pnl_line if category else None
        sub = category.subledger if category else None
        rows.append(
            TransactionRow(
                line=line,
                category_label=category.label if category else line.category,
                ifrs=category.ifrs if category else line.cashflow_class,
                us_gaap=category.us_gaap if category else line.cashflow_class,
                pnl_line=profit_loss.lines[pnl].label if pnl in profit_loss.lines else None,
                subledger=profit_loss.subledgers.get(sub) if sub else None,
                confidence=line.category_confidence if line.categorized_by == "MODEL" else None,
                reading=_reading(line),
                match_kind=match.kind if match else None,
                linked=tuple(linked),
            )
        )
    return rows
