"""Firestore month repository implementation (docs/09 §3.9)."""

from datetime import UTC, datetime
from typing import Any

from google.cloud.firestore import AsyncClient

from app.domain.models.month import Month, MonthState
from app.ports.month_repository import MonthRepository


def _to_domain(data: dict[str, Any]) -> Month:
    return Month(
        month=data.get("month", ""),
        state=MonthState(data.get("state", "COLLECTING")),
        dirty=data.get("dirty", False),
        generation=data.get("generation", 0),
        statements=data.get("statements", []),
        figures=data.get("figures", {}),
        risk=data.get("risk", {}),
        flows=data.get("flows", {}),
        note=data.get("note"),
        last_run_id=data.get("lastRunId"),
        updated_at=data.get("updatedAt"),
    )


def _to_firestore(month: Month) -> dict[str, Any]:
    return {
        "month": month.month,
        "state": month.state.value if hasattr(month.state, "value") else str(month.state),
        "dirty": month.dirty,
        "generation": month.generation,
        "statements": month.statements,
        "figures": month.figures,
        "risk": month.risk,
        "flows": month.flows,
        "note": month.note,
        "lastRunId": month.last_run_id,
        "updatedAt": month.updated_at or datetime.now(UTC),
    }


class FirestoreMonthRepository(MonthRepository):
    def __init__(self, db: AsyncClient) -> None:
        self._db = db

    def _col(self, org_id: str):
        return self._db.collection("orgs").document(org_id).collection("months")

    async def get(self, org_id: str, month: str) -> Month | None:
        doc = await self._col(org_id).document(month).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        data["month"] = month
        return _to_domain(data)

    async def save(self, org_id: str, month: Month) -> None:
        await self._col(org_id).document(month.month).set(_to_firestore(month), merge=True)

    async def bump_generation(
        self, org_id: str, month: str, dirty: bool = True
    ) -> tuple[int, Month]:
        doc_ref = self._col(org_id).document(month)
        snap = await doc_ref.get()
        now = datetime.now(UTC)
        if not snap.exists:
            m = Month(
                month=month,
                state=MonthState.COLLECTING,
                dirty=dirty,
                generation=1,
                updated_at=now,
            )
            await doc_ref.set(_to_firestore(m))
            return 1, m
        data = snap.to_dict() or {}
        data["month"] = month
        m = _to_domain(data)
        m.generation += 1
        m.dirty = dirty
        m.updated_at = now
        await doc_ref.set(_to_firestore(m), merge=True)
        return m.generation, m

    async def list(self, org_id: str) -> list[Month]:
        snaps = await self._col(org_id).get()
        result: list[Month] = []
        for snap in snaps:
            data = snap.to_dict() or {}
            data["month"] = snap.id
            result.append(_to_domain(data))
        return result
