"""Review items repository port (docs/09 §3.11, §5)."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.domain.models.events import AuditEvent
from app.domain.review_items import ReviewItem


class ReviewItemRepository(Protocol):
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
        """Items, highest priority first, with the next cursor and the counts per kind."""
        ...

    async def get_review_item(self, org_id: str, item_id: str) -> ReviewItem | None: ...

    async def resolve(self, org_id: str, item: ReviewItem, event: AuditEvent) -> None:
        """A person's resolution and its audit event, in one write."""
        ...

    async def replace_month_review_items(
        self, org_id: str, month: str, fresh: list[ReviewItem], *, now: datetime
    ) -> list[ReviewItem]:
        """Store a month run's items (domain `sync_items`); returns the items written."""
        ...
