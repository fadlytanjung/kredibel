"""orgs/{orgId}/counterparties/{counterpartyId} as stored (docs/09 §3.13)."""

from typing import Any

from pydantic import Field

from app.adapters.firestore.models.base import FirestoreModel


class CounterpartyDoc(FirestoreModel):
    counterparty_id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    kind: str = "UNKNOWN"
    roles: list[str] = Field(default_factory=list)
    # month → {inMinor, outMinor, count}
    totals_by_month: dict[str, dict[str, int]] = Field(default_factory=dict)
    # {accountMasked, firstSeen, lastSeen}; the hashes live in orgPrivate/…/counterpartyAccounts
    accounts_seen: list[dict[str, Any]] = Field(default_factory=list)
    open_invoices: int = 0
    first_date: str | None = None
    last_date: str | None = None
    sample_evidence: list[dict[str, Any]] = Field(default_factory=list)
    bank_line_ids: list[str] = Field(default_factory=list)
    invoice_ids: list[str] = Field(default_factory=list)
    receipt_ids: list[str] = Field(default_factory=list)
    bucket: bool = False
    name_fold: str = ""  # for the `q` filter
