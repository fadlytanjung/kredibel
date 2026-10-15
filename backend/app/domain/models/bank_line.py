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
    # Categorization (docs/08 §4.1): the category, its cash-flow class under the workspace's
    # framework, risk tags, and who decided it.
    category: str = "UNKNOWN"
    cashflow_class: str = "UNCLASSIFIED"
    risk_tags: list[str] = field(default_factory=list)
    categorized_by: str = "NONE"
    category_confidence: Decimal | None = None
    # Written by the month run (ADR-025): match state and support are not the same as cash.
    match_state: str = "UNMATCHED"
    match_ids: list[str] = field(default_factory=list)
    support: str | None = None
    # Corrections (T009-03b)
    corrected_fields: list[str] = field(default_factory=list)
    corrected_by: str | None = None
    corrected_at: Any = None

    @property
    def amount_minor(self) -> int:
        return int(self.amount * 100)

    @property
    def balance_minor(self) -> int | None:
        return None if self.balance is None else int(self.balance * 100)
