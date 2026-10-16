"""What a person expects against the reconciled months (spec 024, AC-024-5)."""

from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain.expectations import Actual, Expectation, MonthComparison, compare_expectations
from app.domain.models.month import MonthState
from app.ports.month_repository import MonthRepository
from app.ports.workspace_repository import WorkspaceRepository

READY = {MonthState.RECONCILED, MonthState.NEEDS_REVIEW}


def _figure(figures: dict[str, Any], key: str) -> Decimal | None:
    raw = figures.get(key)
    value = raw.get("value") if isinstance(raw, dict) else raw
    try:
        return None if value is None else Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


class ExpectationService:
    def __init__(
        self, workspaces: WorkspaceRepository, months: MonthRepository, tolerance: Decimal
    ) -> None:
        self._workspaces = workspaces
        self._months = months
        self._tolerance = tolerance

    async def compare(self, org_id: str) -> tuple[Decimal, list[MonthComparison]]:
        workspace = await self._workspaces.get_workspace(org_id)
        if workspace is None or not workspace.expectations:
            return self._tolerance, []
        actuals: dict[str, Actual] = {}
        for month in await self._months.list(org_id):
            figures = month.figures or {}
            money_in, money_out = _figure(figures, "moneyIn"), _figure(figures, "moneyOut")
            if money_in is None or money_out is None:
                continue
            ready = month.state in READY and not month.dirty
            actuals[month.month] = Actual(month.month, money_in, abs(money_out), ready)
        expected = [Expectation(e.month, e.money_in, e.money_out) for e in workspace.expectations]
        return self._tolerance, compare_expectations(expected, actuals, self._tolerance)
