"""A month's checks see payments made in other months (spec 007, AC-007-10): R01 must not call an
invoice overdue that an earlier month's statement shows paid; D07 must see an earlier payment."""

from decimal import Decimal as D

from app.agents.month_data import allocations_for_checks
from app.domain.models.match import StoredMatch
from app.domain.reconcile import Allocation


def stored(match_id: str, month: str, status: str, method: str | None = "AUTO") -> StoredMatch:
    return StoredMatch(
        match_id=match_id,
        month=month,
        kind="BANK_SALES_INVOICE",
        status=status,  # type: ignore[arg-type]
        method=method,  # type: ignore[arg-type]
        bank_line_ids=[f"tx_{match_id}"],
        invoice_ids=[f"inv_{match_id}"],
        score=D("0.95"),
    )


def test_this_months_allocations_plus_other_months_confirmed_matches():
    fresh = [
        Allocation(
            "mat_feb", ("tx_feb",), ("inv_feb",), "CONFIRMED", "AUTO", D("0.9"), (), D(0), False
        )
    ]
    matches = [
        stored("mat_jan", "2026-01", "CONFIRMED"),
        stored("mat_jan_manual", "2026-01", "CONFIRMED", "MANUAL"),
        stored("mat_jan_proposed", "2026-01", "PROPOSED", None),
        stored("mat_jan_rejected", "2026-01", "REJECTED"),
        stored("mat_feb_old", "2026-02", "CONFIRMED"),  # this month's stored: replaced by the run
    ]
    ids = [a.match_id for a in allocations_for_checks(fresh, matches, "2026-02")]
    assert ids == ["mat_feb", "mat_jan", "mat_jan_manual", "mat_jan_proposed"]
