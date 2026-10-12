"""MatchRepository on Firestore (docs/09 §3.10)."""

from decimal import Decimal

from google.cloud.firestore import AsyncClient, FieldFilter

from app.adapters.firestore.models.match import MatchDoc
from app.adapters.firestore.txn import dump
from app.domain.models.match import StoredMatch
from app.ports.match_repository import MatchRepository

_BATCH = 400


def _to_doc(m: StoredMatch) -> MatchDoc:
    return MatchDoc(
        match_id=m.match_id,
        month=m.month,
        kind=m.kind,
        status=m.status,
        method=m.method,
        bank_line_ids=m.bank_line_ids,
        invoice_ids=m.invoice_ids,
        receipt_ids=m.receipt_ids,
        amount_minor=int(m.amount * 100),
        amount_difference_minor=int(m.amount_difference * 100),
        score=str(m.score),
        reasons=m.reasons,
        alternatives=m.alternatives,
        requires_review=m.requires_review,
        created_by=m.created_by,
        created_at=m.created_at,
        run_id=m.run_id,
    )


def _to_domain(d: MatchDoc) -> StoredMatch:
    return StoredMatch(
        match_id=d.match_id,
        month=d.month,
        kind=d.kind,  # type: ignore[arg-type]
        status=d.status,  # type: ignore[arg-type]
        method=d.method,  # type: ignore[arg-type]
        bank_line_ids=d.bank_line_ids,
        invoice_ids=d.invoice_ids,
        receipt_ids=d.receipt_ids,
        amount=Decimal(d.amount_minor) / 100,
        amount_difference=Decimal(d.amount_difference_minor) / 100,
        score=Decimal(d.score),
        reasons=d.reasons,
        alternatives=d.alternatives,
        requires_review=d.requires_review,
        created_by=d.created_by,
        created_at=d.created_at,
        run_id=d.run_id,
    )


class FirestoreMatchRepository(MatchRepository):
    def __init__(self, db: AsyncClient) -> None:
        self._db = db

    def _col(self, org_id: str):
        return self._db.collection("orgs").document(org_id).collection("matches")

    async def replace_month_matches(
        self, org_id: str, month: str, matches: list[StoredMatch]
    ) -> None:
        current = await self.list_matches(org_id, month=month)
        keep = {m.match_id for m in matches}
        stale = [m for m in current if not m.by_person and m.match_id not in keep]
        people = {m.match_id for m in current if m.by_person}
        writes = [("set", m) for m in matches if m.match_id not in people]
        writes += [("delete", m) for m in stale]
        for start in range(0, len(writes), _BATCH):
            batch = self._db.batch()
            for kind, m in writes[start : start + _BATCH]:
                ref = self._col(org_id).document(m.match_id)
                if kind == "set":
                    batch.set(ref, dump(_to_doc(m)))
                else:
                    batch.delete(ref)
            await batch.commit()

    async def list_matches(
        self, org_id: str, *, month: str | None = None, status: str | None = None, limit: int = 1000
    ) -> list[StoredMatch]:
        query = self._col(org_id)
        if month:
            query = query.where(filter=FieldFilter("month", "==", month))
        if status:
            query = query.where(filter=FieldFilter("status", "==", status))
        found = [
            _to_domain(MatchDoc.model_validate(s.to_dict()))
            async for s in query.limit(limit).stream()
        ]
        return sorted(found, key=lambda m: m.match_id)

    async def save(self, org_id: str, match: StoredMatch) -> None:
        await self._col(org_id).document(match.match_id).set(dump(_to_doc(match)))
