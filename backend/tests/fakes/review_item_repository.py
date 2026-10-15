"""In-memory review items repository for tests."""

from __future__ import annotations

from datetime import datetime

from app.domain.models.events import AuditEvent
from app.domain.review_items import ReviewItem, queue_page, sync_items
from app.ports.review_item_repository import ReviewItemRepository


class FakeReviewItemRepository(ReviewItemRepository):
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], ReviewItem] = {}
        self.events: list[AuditEvent] = []

    async def list_review_items(
        self,
        org_id: str,
        *,
        status: str | None = None,
        kind: str | None = None,
        month: str | None = None,
        limit: int = 200,
        cursor: str | None = None,
    ) -> tuple[list[ReviewItem], str | None, dict[str, int]]:
        mine = [
            i
            for (o, _), i in self.items.items()
            if o == org_id and (status is None or i.status == status)
        ]
        return queue_page(mine, kind=kind, month=month, limit=limit, cursor=cursor)

    async def get_review_item(self, org_id: str, item_id: str) -> ReviewItem | None:
        return self.items.get((org_id, item_id))

    async def resolve(self, org_id: str, item: ReviewItem, event: AuditEvent) -> None:
        self.items[(org_id, item.item_id)] = item
        self.events.append(event)

    async def upsert_review_item(self, org_id: str, item: ReviewItem) -> None:
        self.items[(org_id, item.item_id)] = item

    async def replace_month_review_items(
        self, org_id: str, month: str, fresh: list[ReviewItem], *, now: datetime
    ) -> list[ReviewItem]:
        existing = [i for (o, _), i in self.items.items() if o == org_id and i.month == month]
        written = sync_items(existing, fresh, now=now)
        for item in written:
            self.items[(org_id, item.item_id)] = item
        return written
