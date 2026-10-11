"""In-memory UsageRepository; a lock stands in for the Firestore transaction."""

import asyncio
from collections.abc import Sequence

from app.domain.models.workspace import Subscription, UsageDay, UsageMonth
from app.domain.plans import Allowed, Decision
from app.ports.workspace_repository import (
    Decide,
    PendingWrite,
    UsageIncrement,
    UsageRepository,
    UsageSettlement,
)


class FakeUsageRepository(UsageRepository):
    def __init__(self, subscriptions: dict[str, Subscription]) -> None:
        self.subscriptions = subscriptions
        self.months: dict[tuple[str, str], UsageMonth] = {}
        self.days: dict[tuple[str, str], UsageDay] = {}
        self.writes: list[PendingWrite] = []
        self._txn = asyncio.Lock()

    @staticmethod
    def days_factory(day: str, **fields: int) -> UsageDay:
        return UsageDay.model_validate({"day": day, **fields})

    async def meter(
        self,
        org_id: str,
        *,
        month: str,
        day: str,
        decide: Decide,
        increment: UsageIncrement,
        writes: Sequence[PendingWrite] = (),
    ) -> tuple[Decision, Subscription]:
        async with self._txn:
            sub = self.subscriptions[org_id]
            m = self.months.get((org_id, month), UsageMonth(month=month))
            d = self.days.get((org_id, day), UsageDay(day=day))
            decision = decide(sub, m, d)
            await asyncio.sleep(0)
            if isinstance(decision, Allowed) and increment != UsageIncrement():
                self.months[(org_id, month)] = m.model_copy(
                    update={
                        "documents_uploaded": m.documents_uploaded + increment.documents_uploaded,
                        "pages_reserved": m.pages_reserved + increment.pages_reserved,
                    }
                )
                self.days[(org_id, day)] = d.model_copy(
                    update={
                        "month_runs": d.month_runs + increment.month_runs,
                        "assistant_questions": d.assistant_questions
                        + increment.assistant_questions,
                    }
                )
            if isinstance(decision, Allowed):
                self.writes.extend(writes)
            return decision, sub

    async def settle(self, org_id: str, settlement: UsageSettlement) -> None:
        async with self._txn:
            key = (org_id, settlement.month)
            m = self.months.get(key, UsageMonth(month=settlement.month))
            self.months[key] = m.model_copy(
                update={
                    "pages_reserved": m.pages_reserved
                    + settlement.pages_read
                    - settlement.pages_reserved,
                    "pages_read": m.pages_read + settlement.pages_read,
                    "pages_cached": m.pages_cached + settlement.pages_cached,
                    "ocr_pages": m.ocr_pages + settlement.ocr_pages,
                    "parser_pages": m.parser_pages + settlement.parser_pages,
                    "ai_spend_usd": m.ai_spend_usd + settlement.ai_spend_usd,
                }
            )

    async def get_usage(self, org_id: str, *, month: str, day: str) -> tuple[UsageMonth, UsageDay]:
        return (
            self.months.get((org_id, month), UsageMonth(month=month)),
            self.days.get((org_id, day), UsageDay(day=day)),
        )
