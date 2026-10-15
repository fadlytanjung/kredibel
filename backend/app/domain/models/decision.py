"""A person's audited decisions about documents and bank lines (ADR-025, docs/09 §3.21).

None of them creates bank cash or a match; they are inputs to the month's reconciliation.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

DecisionKind = Literal[
    "DOCUMENT_APPROVAL", "PAYMENT_CONFIRMATION", "CURRENCY_AGREEMENT", "SUPPORT_NOT_REQUIRED"
]
PaymentMethodPaid = Literal["CASH", "CARD", "TRANSFER", "CHEQUE", "OTHER"]


@dataclass
class Decision:
    decision_id: str
    kind: DecisionKind
    decided_by: str
    decided_at: datetime
    status: Literal["ACTIVE", "WITHDRAWN"] = "ACTIVE"
    doc_id: str | None = None
    invoice_id: str | None = None
    receipt_id: str | None = None
    tx_id: str | None = None
    amount: Decimal | None = None  # in the workspace currency; never converted
    currency: str | None = None
    paid_on: date | None = None
    method: PaymentMethodPaid | None = None
    reason: str | None = None
    printed_currency: str | None = None  # CURRENCY_AGREEMENT: what the document prints
    months: list[str] = field(default_factory=list)
    withdrawn_by: str | None = None
    withdrawn_at: datetime | None = None

    @property
    def record_id(self) -> str | None:
        return self.invoice_id or self.receipt_id or self.tx_id
