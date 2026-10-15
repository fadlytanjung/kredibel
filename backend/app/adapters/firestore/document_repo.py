"""FirestoreDocumentRepository implementation for storing and querying documents (spec 003).

Normative references: docs/09 §3.5, docs/10 §2.2, ADR-011, ADR-013.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from google.cloud.firestore import AsyncClient, AsyncTransaction, FieldFilter, async_transactional

from app.adapters.firestore.models.document import FileHashDoc
from app.adapters.firestore.txn import dump, with_backoff
from app.adapters.firestore.upcast import upcast
from app.domain.models.document import (
    DocStatus,
    DocType,
    Document,
    DuplicateDecision,
    DuplicateInfo,
    DuplicateKind,
    PageRecord,
    PageStatus,
    TextLayerStatus,
    WitnessType,
)
from app.domain.models.events import AuditEvent
from app.ports.document_repository import DocumentRepository

# An upload holds its claim while it renders and stores pages; one that never saved its document
# (a crashed process) stops blocking the content after this long (docs/09 §3.18).
CLAIM_STALE_AFTER = timedelta(minutes=10)


def _parse_datetime(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        return datetime.fromisoformat(val)
    return datetime.now()


def _to_domain(data: dict[str, Any]) -> Document:
    upcasted = upcast("documents", data)
    doc_id = upcasted.get("id") or upcasted.get("docId", "")
    dup_raw = upcasted.get("duplicate")
    duplicate: DuplicateInfo | None = None
    if dup_raw and isinstance(dup_raw, dict):
        duplicate = DuplicateInfo(
            kind=DuplicateKind(dup_raw.get("kind", "EXACT")),
            code=dup_raw.get("code", "D01_EXACT_FILE_DUPLICATE"),
            of_doc_id=dup_raw.get("ofDocId", ""),
            decision=DuplicateDecision(dup_raw.get("decision", "CONFIRMED")),
            review_item_id=dup_raw.get("reviewItemId"),
            decided_by=dup_raw.get("decidedBy"),
            decided_at=_parse_datetime(dup_raw["decidedAt"]) if dup_raw.get("decidedAt") else None,
        )

    pages: list[PageRecord] = []
    for p in upcasted.get("pages", []):
        pages.append(
            PageRecord(
                page_no=p.get("pageNo", 1),
                image_path=p.get("imagePath", ""),
                thumb_path=p.get("thumbPath", ""),
                sha256=p.get("sha256", ""),
                text_layer=TextLayerStatus(p.get("textLayer", "NONE")),
                blank=bool(p.get("blank", False)),
                witness=WitnessType(p.get("witness", "NONE")),
                status=PageStatus(p.get("status", "PENDING")),
                agreement=Decimal(str(p["agreement"])) if p.get("agreement") is not None else None,
            )
        )

    return Document(
        doc_id=doc_id,
        file_name=upcasted.get("fileName") or upcasted.get("file_name", ""),
        content_type=upcasted.get("contentType") or upcasted.get("content_type", ""),
        size_bytes=int(upcasted.get("sizeBytes", 0)),
        page_count=int(upcasted.get("pageCount", 0)),
        sha256=upcasted.get("sha256", ""),
        gcs_path=upcasted.get("gcsPath") or upcasted.get("gcs_path", ""),
        uploaded_by=upcasted.get("uploadedBy") or upcasted.get("uploaded_by", ""),
        uploaded_at=_parse_datetime(upcasted.get("uploadedAt") or upcasted.get("uploaded_at")),
        doc_type=DocType(upcasted.get("docType", "UNKNOWN")),
        type_confidence=(
            Decimal(str(upcasted["typeConfidence"]))
            if upcasted.get("typeConfidence") is not None
            else None
        ),
        type_set_by=upcasted.get("typeSetBy"),
        status=DocStatus(upcasted.get("status", "UPLOADED")),
        status_detail=upcasted.get("statusDetail"),
        p_hash=upcasted.get("pHash"),
        months=list(upcasted.get("months", [])),
        duplicate=duplicate,
        held_as_duplicate=bool(upcasted.get("heldAsDuplicate", False)),
        counts_against_limits=bool(upcasted.get("countsAgainstLimits", True)),
        pages=pages,
        reading=upcasted.get("reading"),
        statement_meta=upcasted.get("statementMeta"),
        ledger_meta=upcasted.get("ledgerMeta"),
        pdf=upcasted.get("pdf"),
        integrity=upcasted.get("integrity"),
        risk=upcasted.get("risk"),
        screening=upcasted.get("screening"),
        last_run_id=upcasted.get("lastRunId"),
    )


def _to_firestore_dict(org_id: str, doc: Document) -> dict[str, Any]:
    dup_dict = None
    if doc.duplicate:
        dup_dict = {
            "kind": doc.duplicate.kind.value,
            "code": doc.duplicate.code,
            "ofDocId": doc.duplicate.of_doc_id,
            "decision": doc.duplicate.decision.value,
            "reviewItemId": doc.duplicate.review_item_id,
            "decidedBy": doc.duplicate.decided_by,
            "decidedAt": doc.duplicate.decided_at.isoformat() if doc.duplicate.decided_at else None,
        }

    pages_list = [
        {
            "pageNo": p.page_no,
            "imagePath": p.image_path,
            "thumbPath": p.thumb_path,
            "sha256": p.sha256,
            "textLayer": p.text_layer.value,
            "blank": p.blank,
            "witness": p.witness.value,
            "status": p.status.value,
            "agreement": str(p.agreement) if p.agreement is not None else None,
        }
        for p in doc.pages
    ]

    data: dict[str, Any] = {
        "schemaVersion": 2,
        "id": doc.doc_id,
        "docId": doc.doc_id,
        "orgId": org_id,
        "fileName": doc.file_name,
        "contentType": doc.content_type,
        "sizeBytes": doc.size_bytes,
        "pageCount": doc.page_count,
        "sha256": doc.sha256,
        "gcsPath": doc.gcs_path,
        "uploadedBy": doc.uploaded_by,
        "uploadedAt": doc.uploaded_at.isoformat(),
        "docType": doc.doc_type.value,
        "typeConfidence": str(doc.type_confidence) if doc.type_confidence is not None else None,
        "typeSetBy": doc.type_set_by,
        "status": doc.status.value,
        "statusDetail": doc.status_detail,
        "pHash": doc.p_hash,
        "months": doc.months,
        "duplicate": dup_dict,
        "heldAsDuplicate": doc.held_as_duplicate,
        "countsAgainstLimits": doc.counts_against_limits,
        "pages": pages_list,
        "reading": doc.reading,
        "statementMeta": doc.statement_meta,
        "ledgerMeta": doc.ledger_meta,
        "pdf": doc.pdf,
        "integrity": doc.integrity,
        "risk": doc.risk,
        "screening": doc.screening,
        "lastRunId": doc.last_run_id,
    }
    return {k: v for k, v in data.items() if v is not None or k in ("duplicate",)}


class FirestoreDocumentRepository(DocumentRepository):
    def __init__(self, client: AsyncClient) -> None:
        self._db = client

    async def find_original_by_sha256(self, org_id: str, sha256: str) -> Document | None:
        docs_ref = self._db.collection("orgs").document(org_id).collection("documents")
        query = docs_ref.where(filter=FieldFilter("sha256", "==", sha256))
        async for snap in query.stream():
            data = snap.to_dict() or {}
            # An exact duplicate is not an original
            if not data.get("duplicate"):
                return _to_domain(data)
        return None

    async def claim_original(
        self, org_id: str, sha256: str, doc_id: str, now: datetime
    ) -> str | None:
        org_ref = self._db.collection("orgs").document(org_id)
        claim_ref = org_ref.collection("fileHashes").document(sha256)
        documents = org_ref.collection("documents")

        @async_transactional
        async def run(txn: AsyncTransaction) -> str | None:
            snap = await claim_ref.get(transaction=txn)
            if snap.exists:
                claim = FileHashDoc.model_validate(snap.to_dict())
                if claim.doc_id == doc_id:
                    return None
                holder = await documents.document(claim.doc_id).get(transaction=txn)
                fresh = now - claim.claimed_at < CLAIM_STALE_AFTER
                if holder.exists or fresh:
                    return claim.doc_id
            else:
                # Documents uploaded before the registry existed are registered on first sight.
                legacy = documents.where(filter=FieldFilter("sha256", "==", sha256))
                for found in await legacy.get(transaction=txn):
                    data = found.to_dict() or {}
                    if not data.get("duplicate"):
                        txn.set(claim_ref, dump(FileHashDoc(doc_id=found.id, claimed_at=now)))
                        return found.id
            txn.set(claim_ref, dump(FileHashDoc(doc_id=doc_id, claimed_at=now)))
            return None

        return await with_backoff(lambda: run(self._db.transaction()))

    async def release_original(self, org_id: str, sha256: str, doc_id: str) -> None:
        claim_ref = (
            self._db.collection("orgs").document(org_id).collection("fileHashes").document(sha256)
        )

        @async_transactional
        async def run(txn: AsyncTransaction) -> None:
            snap = await claim_ref.get(transaction=txn)
            if snap.exists and (snap.to_dict() or {}).get("docId") == doc_id:
                txn.delete(claim_ref)

        await with_backoff(lambda: run(self._db.transaction()))

    async def get_document(self, org_id: str, doc_id: str) -> Document | None:
        doc_ref = (
            self._db.collection("orgs").document(org_id).collection("documents").document(doc_id)
        )
        snap = await doc_ref.get()
        if not snap.exists:
            return None
        return _to_domain(snap.to_dict() or {})

    async def list_documents(
        self,
        org_id: str,
        *,
        doc_type: str | None = None,
        month: str | None = None,
        status: str | None = None,
        duplicate: bool | None = None,
        risk: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[Document], str | None]:
        docs_ref = self._db.collection("orgs").document(org_id).collection("documents")
        query = docs_ref.order_by("uploadedAt", direction="DESCENDING")

        if doc_type:
            query = query.where(filter=FieldFilter("docType", "==", doc_type))
        if status:
            query = query.where(filter=FieldFilter("status", "==", status))
        if month:
            query = query.where(filter=FieldFilter("months", "array_contains", month))

        results: list[Document] = []
        async for snap in query.limit(limit * 2).stream():
            doc = _to_domain(snap.to_dict() or {})
            if duplicate is not None:
                is_dup = doc.duplicate is not None
                if is_dup != duplicate:
                    continue
            if risk and (not doc.risk or doc.risk.get("level") != risk):
                continue
            results.append(doc)
            if len(results) >= limit:
                break

        return results[:limit], None

    async def save_document(
        self,
        org_id: str,
        document: Document,
        event: AuditEvent | None = None,
    ) -> None:
        org_ref = self._db.collection("orgs").document(org_id)
        doc_ref = org_ref.collection("documents").document(document.doc_id)
        batch = self._db.batch()
        batch.set(doc_ref, _to_firestore_dict(org_id, document))

        if event:
            event_ref = org_ref.collection("events").document(event.event_id)
            event_data = {
                "eventId": event.event_id,
                "type": event.type,
                "actorUid": event.actor_uid,
                "actorRole": event.actor_role,
                "at": event.at.isoformat(),
                "subject": event.subject,
                "details": event.details,
            }
            batch.set(event_ref, event_data)

        await batch.commit()

    async def delete_document(
        self,
        org_id: str,
        doc_id: str,
        *,
        months: list[str] | None = None,
        event: AuditEvent | None = None,
    ) -> bool:
        org_ref = self._db.collection("orgs").document(org_id)
        doc_ref = org_ref.collection("documents").document(doc_id)
        snap = await doc_ref.get()
        if not snap.exists:
            return False

        doc_data = snap.to_dict() or {}
        batch = self._db.batch()
        batch.delete(doc_ref)
        if doc_data.get("sha256") and not doc_data.get("duplicate"):
            claim_ref = org_ref.collection("fileHashes").document(str(doc_data["sha256"]))
            claim = await claim_ref.get()
            if claim.exists and (claim.to_dict() or {}).get("docId") == doc_id:
                batch.delete(claim_ref)

        # Cascade: exact copies of this file go with it (AC-003-10); a content duplicate is a file
        # of its own and stays (its next run releases it).
        dups_query = org_ref.collection("documents").where(
            filter=FieldFilter("duplicate.ofDocId", "==", doc_id)
        )
        async for dup_snap in dups_query.stream():
            if ((dup_snap.to_dict() or {}).get("duplicate") or {}).get("kind") == "EXACT":
                batch.delete(dup_snap.reference)

        # Mark months dirty
        affected_months = set(months or [])
        if doc_data.get("months"):
            affected_months.update(doc_data["months"])

        for m in affected_months:
            month_ref = org_ref.collection("months").document(m)
            batch.set(month_ref, {"dirty": True, "month": m}, merge=True)

        if event:
            event_ref = org_ref.collection("events").document(event.event_id)
            batch.set(
                event_ref,
                {
                    "eventId": event.event_id,
                    "type": event.type,
                    "actorUid": event.actor_uid,
                    "actorRole": event.actor_role,
                    "at": event.at.isoformat(),
                    "subject": event.subject,
                    "details": event.details,
                },
            )

        await batch.commit()
        return True
