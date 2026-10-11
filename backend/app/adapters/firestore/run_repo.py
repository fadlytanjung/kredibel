"""Firestore run repository implementation (docs/09 §3.15)."""

from datetime import UTC, datetime
from typing import Any

from google.cloud.firestore import ArrayUnion, AsyncClient, FieldFilter

from app.domain.models.run import Run, RunKind, RunStage, RunStatus, StageStatus
from app.ports.run_repository import RunRepository


def _parse_datetime(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        return datetime.fromisoformat(val)
    return None


def _stage_to_firestore(stage: RunStage) -> dict[str, Any]:
    return {
        "node": stage.node,
        "parent": stage.parent,
        "status": stage.status.value if hasattr(stage.status, "value") else str(stage.status),
        "startedAt": stage.started_at,
        "endedAt": stage.ended_at,
        "model": stage.model,
        "tokensIn": stage.tokens_in,
        "tokensOut": stage.tokens_out,
        "summary": stage.summary,
        "traceSpanId": stage.trace_span_id,
    }


def _stage_to_domain(data: dict[str, Any]) -> RunStage:
    return RunStage(
        node=data.get("node", ""),
        parent=data.get("parent"),
        status=StageStatus(data.get("status", "QUEUED")),
        started_at=_parse_datetime(data.get("startedAt")),
        ended_at=_parse_datetime(data.get("endedAt")),
        model=data.get("model"),
        tokens_in=data.get("tokensIn"),
        tokens_out=data.get("tokensOut"),
        summary=data.get("summary"),
        trace_span_id=data.get("traceSpanId"),
    )


def _run_to_firestore(run: Run) -> dict[str, Any]:
    return {
        "runId": run.run_id,
        "kind": run.kind.value if hasattr(run.kind, "value") else str(run.kind),
        "target": run.target,
        "status": run.status.value if hasattr(run.status, "value") else str(run.status),
        "stages": [_stage_to_firestore(s) for s in run.stages],
        "traceId": run.trace_id,
        "models": run.models,
        "promptVersions": run.prompt_versions,
        "labels": run.labels,
        "usage": run.usage,
        "policyHashes": run.policy_hashes,
        "generation": run.generation,
        "createdAt": run.created_at or datetime.now(UTC),
        "endedAt": run.ended_at,
    }


def _run_to_domain(data: dict[str, Any]) -> Run:
    return Run(
        run_id=data.get("runId", ""),
        kind=RunKind(data.get("kind", "DOCUMENT")),
        target=data.get("target", ""),
        status=RunStatus(data.get("status", "QUEUED")),
        stages=[_stage_to_domain(s) for s in data.get("stages", [])],
        trace_id=data.get("traceId"),
        models=data.get("models", []),
        prompt_versions=data.get("promptVersions", {}),
        labels=data.get("labels", {}),
        usage=data.get("usage", {}),
        policy_hashes=data.get("policyHashes", {}),
        generation=data.get("generation"),
        created_at=_parse_datetime(data.get("createdAt")),
        ended_at=_parse_datetime(data.get("endedAt")),
    )


class FirestoreRunRepository(RunRepository):
    def __init__(self, db: AsyncClient) -> None:
        self._db = db

    def _col(self, org_id: str):
        return self._db.collection("orgs").document(org_id).collection("runs")

    async def create(self, org_id: str, run: Run) -> None:
        await self._col(org_id).document(run.run_id).set(_run_to_firestore(run))

    async def get(self, org_id: str, run_id: str) -> Run | None:
        doc = await self._col(org_id).document(run_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        data["runId"] = run_id
        return _run_to_domain(data)

    async def update_status(
        self, org_id: str, run_id: str, status: RunStatus, ended: bool = False
    ) -> None:
        doc_ref = self._col(org_id).document(run_id)
        updates: dict[str, Any] = {
            "status": status.value if hasattr(status, "value") else str(status)
        }
        if ended:
            updates["endedAt"] = datetime.now(UTC)
        await doc_ref.set(updates, merge=True)

    async def append_stage(self, org_id: str, run_id: str, stage: RunStage) -> None:
        doc_ref = self._col(org_id).document(run_id)
        await doc_ref.set({"stages": ArrayUnion([_stage_to_firestore(stage)])}, merge=True)

    async def list_by_target(self, org_id: str, target: str) -> list[Run]:
        return await self.list_runs(org_id, target=target)

    async def list_runs(
        self,
        org_id: str,
        *,
        kind: RunKind | None = None,
        target: str | None = None,
        status: RunStatus | None = None,
        limit: int = 50,
    ) -> list[Run]:
        query = self._col(org_id)
        if target is not None:
            query = query.where(filter=FieldFilter("target", "==", target))
        if kind is not None:
            k_val = kind.value if hasattr(kind, "value") else str(kind)
            query = query.where(filter=FieldFilter("kind", "==", k_val))
        if status is not None:
            s_val = status.value if hasattr(status, "value") else str(status)
            query = query.where(filter=FieldFilter("status", "==", s_val))
        query = query.limit(limit)
        snaps = await query.get()
        runs: list[Run] = []
        for snap in snaps:
            data = snap.to_dict() or {}
            data["runId"] = snap.id
            runs.append(_run_to_domain(data))
        runs.sort(
            key=lambda r: r.created_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        return runs
