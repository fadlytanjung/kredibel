"""In-memory fake month repository for tests."""

from datetime import UTC, datetime

from app.domain.models.month import Month, MonthState
from app.ports.month_repository import MonthRepository


class FakeMonthRepository(MonthRepository):
    def __init__(self) -> None:
        self.months: dict[tuple[str, str], Month] = {}

    async def get(self, org_id: str, month: str) -> Month | None:
        return self.months.get((org_id, month))

    async def save(self, org_id: str, month: Month) -> None:
        self.months[(org_id, month.month)] = month

    async def bump_generation(
        self, org_id: str, month: str, dirty: bool = True
    ) -> tuple[int, Month]:
        existing = self.months.get((org_id, month))
        if existing is None:
            existing = Month(
                month=month,
                state=MonthState.COLLECTING,
                dirty=dirty,
                generation=1,
                updated_at=datetime.now(UTC),
            )
        else:
            existing.generation += 1
            existing.dirty = dirty
            existing.updated_at = datetime.now(UTC)
        self.months[(org_id, month)] = existing
        return existing.generation, existing

    async def list(self, org_id: str) -> list[Month]:
        return [m for (o, _), m in self.months.items() if o == org_id]
