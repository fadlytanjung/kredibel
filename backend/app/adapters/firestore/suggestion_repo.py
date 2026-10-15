"""SuggestionRepository on Firestore (docs/09 §3.14); account hashes under orgPrivate only."""

from google.cloud.firestore import AsyncClient, FieldFilter

from app.adapters.firestore.models.suggestion import SuggestionDoc
from app.adapters.firestore.models.workspace import EventDoc
from app.adapters.firestore.txn import dump
from app.domain.models.events import AuditEvent
from app.domain.profile_suggestions import Suggestion
from app.ports.suggestion_repository import SuggestionRepository

_DECIDED = ("ACCEPTED", "REJECTED")


def _to_doc(s: Suggestion) -> SuggestionDoc:
    return SuggestionDoc(
        suggestion_id=s.suggestion_id,
        field=s.field,
        value=dict(s.value),
        display=s.display,
        confidence=s.confidence,
        basis=s.basis,
        evidence=list(s.evidence),
        status=s.status,
        conflict_with=s.conflict_with,
        decided_by=s.decided_by,
        decided_at=s.decided_at,
    )


def _to_domain(d: SuggestionDoc, secret: dict[str, str]) -> Suggestion:
    return Suggestion(
        suggestion_id=d.suggestion_id,
        field=d.field,  # type: ignore[arg-type]
        value=dict(d.value),
        display=d.display,
        confidence=d.confidence,  # type: ignore[arg-type]
        basis=d.basis,
        evidence=list(d.evidence),
        status=d.status,  # type: ignore[arg-type]
        conflict_with=d.conflict_with,
        secret=secret,
        decided_by=d.decided_by,
        decided_at=d.decided_at,
    )


class FirestoreSuggestionRepository(SuggestionRepository):
    def __init__(self, db: AsyncClient) -> None:
        self._db = db

    def _col(self, org_id: str):
        return self._db.collection("orgs").document(org_id).collection("suggestions")

    def _secret(self, org_id: str, suggestion_id: str):
        return (
            self._db.collection("orgPrivate")
            .document(org_id)
            .collection("suggestionSecrets")
            .document(suggestion_id)
        )

    async def upsert_open(self, org_id: str, suggestions: list[Suggestion]) -> None:
        for s in suggestions:
            existing = await self._col(org_id).document(s.suggestion_id).get()
            if existing.exists and (existing.to_dict() or {}).get("status") in _DECIDED:
                continue
            batch = self._db.batch()
            batch.set(self._col(org_id).document(s.suggestion_id), dump(_to_doc(s)))
            if s.secret:
                batch.set(self._secret(org_id, s.suggestion_id), dict(s.secret))
            await batch.commit()

    async def list_suggestions(self, org_id: str, *, status: str | None = None) -> list[Suggestion]:
        query = self._col(org_id)
        if status:
            query = query.where(filter=FieldFilter("status", "==", status))
        found = [
            _to_domain(SuggestionDoc.model_validate(s.to_dict()), {}) async for s in query.stream()
        ]
        return sorted(found, key=lambda s: (s.field, s.suggestion_id))

    async def get(self, org_id: str, suggestion_id: str) -> Suggestion | None:
        snap = await self._col(org_id).document(suggestion_id).get()
        if not snap.exists:
            return None
        secret = await self._secret(org_id, suggestion_id).get()
        return _to_domain(
            SuggestionDoc.model_validate(snap.to_dict()),
            {k: str(v) for k, v in (secret.to_dict() or {}).items()} if secret.exists else {},
        )

    async def decide(self, org_id: str, suggestion: Suggestion, event: AuditEvent) -> None:
        batch = self._db.batch()
        batch.set(self._col(org_id).document(suggestion.suggestion_id), dump(_to_doc(suggestion)))
        batch.set(
            self._db.collection("orgs")
            .document(org_id)
            .collection("events")
            .document(event.event_id),
            dump(EventDoc(org_id=org_id, **event.model_dump())),
        )
        await batch.commit()
