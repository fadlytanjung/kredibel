"""A bank line: one transaction row of a statement, with its grounding (docs/09 §3.6)."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Literal


@dataclass
class BankLine:
    tx_id: str
    doc_id: str
    page: int
    row_index: int  # printed order across the statement, balance lines included
    date: date
    month: str  # yyyy-mm
    description: str
    amount: Decimal  # signed: + credit, − debit
    balance: Decimal | None
    counterparty_name: str | None = None
    source: Literal["AI", "WITNESS"] = "AI"
    consensus: dict[str, dict[str, Any]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    chunk_ids: tuple[str, ...] = ()

    @property
    def amount_minor(self) -> int:
        return int(self.amount * 100)

    @property
    def balance_minor(self) -> int | None:
        return None if self.balance is None else int(self.balance * 100)
