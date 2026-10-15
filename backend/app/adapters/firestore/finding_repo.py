"""FindingRepository on Firestore (docs/09 §3.12): one document per finding, by deterministic ID."""

from dataclasses import asdict

from google.cloud.firestore import AsyncClient, FieldFilter

from app.adapters.firestore.models.finding import EvidenceDoc, FindingDoc
from app.adapters.firestore.txn import dump
from app.domain.findings import Evidence, Finding, merge_findings
from app.ports.finding_repository import FindingRepository


def _to_doc(f: Finding) -> FindingDoc:
    return FindingDoc(
        finding_id=f.finding_id,
        code=f.code,
        category=f.category,
        scope=f.scope,
        doc_id=f.doc_id,
        month=f.month,
        severity=f.severity,
        severity_rank=f.severity_rank,
        title=f.title,
        facts=f.facts,
        explanation=f.explanation,
        next_steps=f.next_steps,
        evidence=[EvidenceDoc(**asdict(e)) for e in f.evidence],
        detected_by=f.detected_by,
        status=f.status,
        dismissal=f.dismissal,
        last_seen_run_id=f.last_seen_run_id,
    )


def _evidence_to_domain(e: EvidenceDoc) -> Evidence:
    return Evidence(
        doc_id=e.doc_id,
        page=e.page,
        bbox=e.bbox,
        tx_id=e.tx_id,
        invoice_id=e.invoice_id,
        receipt_id=e.receipt_id,
        ledger_entry_id=e.ledger_entry_id,
        label=e.label,
    )


def _to_domain(d: FindingDoc) -> Finding:
    return Finding(
        finding_id=d.finding_id,
        code=d.code,
        category=d.category,  # type: ignore[arg-type]
        severity=d.severity,  # type: ignore[arg-type]
        title=d.title,
        facts=d.facts,
        evidence=[_evidence_to_domain(e) for e in d.evidence],
        scope=d.scope,  # type: ignore[arg-type]
        doc_id=d.doc_id,
        month=d.month,
        next_steps=d.next_steps,
        explanation=d.explanation,
        detected_by=d.detected_by,  # type: ignore[arg-type]
        status=d.status,  # type: ignore[arg-type]
        dismissal=d.dismissal,
        last_seen_run_id=d.last_seen_run_id,
    )


class FirestoreFindingRepository(FindingRepository):
    def __init__(self, db: AsyncClient) -> None:
        self._db = db

    def _col(self, org_id: str):
        return self._db.collection("orgs").document(org_id).collection("findings")

    async def replace_document_findings(
        self,
        org_id: str,
        doc_id: str,
        fresh: list[Finding],
        *,
        run_id: str | None,
        categories: set[str] | None = None,
    ) -> list[Finding]:
        existing = [
            f
            for f in await self.list_findings(org_id, doc_id=doc_id, limit=1000)
            if categories is None or f.category in categories
        ]
        for f in fresh:
            f.last_seen_run_id = run_id
        merged = merge_findings(existing, fresh)
        batch = self._db.batch()
        for f in merged:
            batch.set(self._col(org_id).document(f.finding_id), dump(_to_doc(f)))
        await batch.commit()
        return merged

    async def replace_month_findings(
        self, org_id: str, month: str, fresh: list[Finding], *, run_id: str | None
    ) -> list[Finding]:
        existing = [
            f
            for f in await self.list_findings(org_id, month=month, limit=1000)
            if f.scope == "MONTH"
        ]
        for f in fresh:
            f.last_seen_run_id = run_id
        merged = merge_findings(existing, fresh)
        batch = self._db.batch()
        for f in merged:
            batch.set(self._col(org_id).document(f.finding_id), dump(_to_doc(f)))
        await batch.commit()
        return merged

    async def list_findings(
        self,
        org_id: str,
        *,
        doc_id: str | None = None,
        month: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[Finding]:
        query = self._col(org_id)
        for field, value in (("docId", doc_id), ("month", month), ("status", status)):
            if value:
                query = query.where(filter=FieldFilter(field, "==", value))
        found = [
            _to_domain(FindingDoc.model_validate(s.to_dict()))
            async for s in query.limit(limit).stream()
        ]
        return sorted(found, key=lambda f: (f.severity_rank, f.code, f.finding_id))

    async def get_finding(self, org_id: str, finding_id: str) -> Finding | None:
        snap = await self._col(org_id).document(finding_id).get()
        if not snap.exists:
            return None
        return _to_domain(FindingDoc.model_validate(snap.to_dict()))

    async def save_finding(self, org_id: str, finding: Finding) -> None:
        await self._col(org_id).document(finding.finding_id).set(dump(_to_doc(finding)))
