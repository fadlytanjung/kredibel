"""A stored match (docs/09 §3.10): a month run's AUTO and PROPOSED matches, a person's MANUAL ones,
and REJECTED proposals, which are kept so they are never proposed again."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal

MatchKind = Literal[
    "BANK_SALES_INVOICE", "BANK_PURCHASE_INVOICE", "BANK_RECEIPT", "BANK_LEDGER", "DOCUMENT_LEDGER"
]


@dataclass
class StoredMatch:
    match_id: str
    month: str  # of the bank line
    kind: MatchKind
    status: Literal["CONFIRMED", "PROPOSED", "REJECTED"]
    method: Literal["AUTO", "MANUAL"] | None
    bank_line_ids: list[str]
    invoice_ids: list[str] = field(default_factory=list)
    receipt_ids: list[str] = field(default_factory=list)
    amount: Decimal = Decimal("0")  # the bank side, unsigned
    amount_difference: Decimal = Decimal("0")
    score: Decimal = Decimal("0")
    reasons: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    requires_review: bool = False
    created_by: str = "system"
    created_at: datetime | None = None
    run_id: str | None = None

    @property
    def document_ids(self) -> list[str]:
        return [*self.invoice_ids, *self.receipt_ids]

    @property
    def by_person(self) -> bool:
        return self.method == "MANUAL" or self.status == "REJECTED"
