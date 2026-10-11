"""Month service for managing month states and triggering debounced runs (spec 004).

Normative references:
- spec 004 US-004-2 (AC-004-4)
- docs/06 §3 (Month workflow)
"""

from app.domain.models.month import Month
from app.ports.month_repository import MonthRepository
from app.services.runs import RunService


class MonthService:
    def __init__(
        self,
        *,
        month_repo: MonthRepository,
        run_service: RunService,
    ) -> None:
        self._month_repo = month_repo
        self._run_service = run_service

    async def get_month(self, org_id: str, month: str) -> Month | None:
        """Get month record by org_id and yyyy-mm."""
        return await self._month_repo.get(org_id, month)

    async def list_months(self, org_id: str) -> list[Month]:
        """List all months for a workspace."""
        return await self._month_repo.list(org_id)

    async def mark_dirty(
        self, org_id: str, months: list[str], reason: str = "data_changed"
    ) -> list[str]:
        """Mark dirty and trigger a debounced month run for each month (AC-004-4)."""
        run_ids: list[str] = []
        for m in months:
            run = await self._run_service.start_month_run(org_id, m, is_user_request=False)
            run_ids.append(run.run_id)
        return run_ids
