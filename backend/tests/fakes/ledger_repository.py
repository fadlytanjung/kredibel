from collections import defaultdict

from app.domain.models.events import AuditEvent
from app.domain.profit_loss import Classification, LedgerRow


class FakeLedgerRepository:
    def __init__(self):
        self.rows: dict[str, list[LedgerRow]] = defaultdict(list)
        self.mappings: dict[str, dict[str, Classification]] = defaultdict(dict)
        self.events: list[AuditEvent] = []

    async def list_rows(self, org_id: str) -> list[LedgerRow]:
        return self.rows[org_id]

    async def save_rows(self, org_id: str, rows: list[LedgerRow]) -> None:
        self.rows[org_id].extend(rows)


    async def classifications(self, org_id: str) -> dict[str, Classification]:
        return self.mappings[org_id]

    async def confirm(self, org_id: str, classification: Classification, event: AuditEvent) -> None:
        self.mappings[org_id][classification.account_code] = classification
        self.events.append(event)
