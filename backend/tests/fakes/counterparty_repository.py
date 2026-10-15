"""In-memory counterparties for tests."""

from app.domain.counterparties import Counterparty, fold_name
from app.ports.counterparty_repository import CounterpartyRepository


class FakeCounterpartyRepository(CounterpartyRepository):
    def __init__(self) -> None:
        self.parties: dict[tuple[str, str], Counterparty] = {}

    async def replace_all(self, org_id: str, parties: list[Counterparty]) -> None:
        for key in [k for k in self.parties if k[0] == org_id]:
            del self.parties[key]
        for p in parties:
            self.parties[(org_id, p.counterparty_id)] = p

    async def list_counterparties(
        self,
        org_id: str,
        *,
        role: str | None = None,
        q: str | None = None,
        limit: int = 200,
        cursor: str | None = None,
    ) -> tuple[list[Counterparty], str | None]:
        needle = fold_name(q) if q else ""
        found = [
            c
            for (o, _), c in self.parties.items()
            if o == org_id
            and (role is None or role in c.roles)
            and (
                not needle
                or needle in fold_name(c.name)
                or any(needle in fold_name(a) for a in c.aliases)
            )
        ]
        found.sort(key=lambda c: (c.name.casefold(), c.counterparty_id))
        start = 0
        if cursor:
            ids = [c.counterparty_id for c in found]
            start = ids.index(cursor) + 1 if cursor in ids else 0
        page = found[start : start + limit]
        more = page[-1].counterparty_id if len(found) > start + limit and page else None
        return page, more

    async def get(self, org_id: str, counterparty_id: str) -> Counterparty | None:
        return self.parties.get((org_id, counterparty_id))
