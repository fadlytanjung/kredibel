"""Document intake service (spec 003, AC-003-3, AC-003-4, AC-003-5).

Handles validation, file type sniffing, duplicate checks, plan limits & reservations,
GCS storage, page rendering & triage, task enqueueing, and audit events.
"""

import asyncio
import hashlib
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import datetime
from typing import Any

from app.core.auth import Principal
from app.core.clock import Clock
from app.core.ids import new_id
from app.domain.errors import (
    NotFoundError,
    RunsDisabledError,
    UploadInProgressError,
    ValidationProblem,
    WorkspaceRequiredError,
)
from app.domain.file_types import detect_file_type
from app.domain.models.document import (
    DocStatus,
    DocType,
    Document,
    DuplicateDecision,
    DuplicateInfo,
    DuplicateKind,
    PageRecord,
    PageStatus,
)
from app.domain.models.events import AuditEvent
from app.domain.models.invoice import Invoice, Receipt
from app.domain.plans import UploadRequest
from app.ports.bank_line_repository import BankLineRepository
from app.ports.document_repository import DocumentRepository
from app.ports.document_storage import DocumentStorage
from app.ports.page_renderer import PageRenderer
from app.ports.record_repository import DocumentRecords
from app.ports.spreadsheet_reader import SpreadsheetReader
from app.ports.task_queue import TaskQueue
from app.services.entitlement_service import EntitlementService

# A simultaneous upload of the same file renders and stores pages before its document exists;
# its twin waits up to two minutes for it (docs/10 §3 UPLOAD_IN_PROGRESS).
_HOLDER_WAIT_SECONDS = 0.5
_HOLDER_WAIT_STEPS = 240


class DocumentService:
    def __init__(
        self,
        *,
        doc_repo: DocumentRepository,
        storage: DocumentStorage,
        task_queue: TaskQueue,
        entitlements: EntitlementService,
        renderer: PageRenderer,
        clock: Clock,
        spreadsheet_reader: SpreadsheetReader | None = None,
        bank_lines: BankLineRepository | None = None,
        invoices: DocumentRecords[Invoice] | None = None,
        receipts: DocumentRecords[Receipt] | None = None,
        runs_enabled: bool = True,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._doc_repo = doc_repo
        self._storage = storage
        self._task_queue = task_queue
        self._entitlements = entitlements
        self._renderer = renderer
        self._clock = clock
        self._spreadsheet_reader = spreadsheet_reader
        self._bank_lines = bank_lines
        self._records: list[DocumentRecords[Any]] = [r for r in (invoices, receipts) if r]
        self._runs_enabled = runs_enabled
        self._sleep = sleep

    async def upload(
        self,
        principal: Principal,
        file_bytes: bytes,
        filename: str,
        doc_type_hint: DocType | None = None,
    ) -> Document:
        """Upload and process a document file."""
        if not self._runs_enabled:
            raise RunsDisabledError()

        if not file_bytes:
            raise ValidationProblem(field="file", message="The file is empty or damaged.")

        if principal.org_id is None:
            raise WorkspaceRequiredError()
        org_id = principal.org_id
        actor_role = principal.role or "owner"

        # 1. Detect media type by content (raises 415 if unsupported)
        info = detect_file_type(file_bytes)

        # 2. Compute exact SHA-256 hash
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        now = self._clock.now()

        # 3. Claim this exact content, or find the document that holds it (AC-003-5). The claim and
        #    the lookup are one transaction, so simultaneous uploads cannot both become originals.
        doc_id = new_id("doc")
        original = await self._holder_of(org_id, file_hash, doc_id, now)
        if original is not None:
            dup_info = DuplicateInfo(
                kind=DuplicateKind.EXACT,
                code="D01_EXACT_FILE_DUPLICATE",
                of_doc_id=original.doc_id,
                decision=DuplicateDecision.CONFIRMED,
            )
            duplicate_doc = Document(
                doc_id=doc_id,
                file_name=filename,
                content_type=info.media_type,
                size_bytes=len(file_bytes),
                page_count=original.page_count,
                sha256=file_hash,
                gcs_path=original.gcs_path,
                uploaded_by=principal.uid,
                uploaded_at=now,
                doc_type=original.doc_type,
                status=DocStatus.DUPLICATE,
                duplicate=dup_info,
                counts_against_limits=False,
            )
            event = AuditEvent(
                event_id=new_id("evt"),
                type="DUPLICATE_RECORDED",
                actor_uid=principal.uid,
                actor_role=actor_role,
                at=now,
                subject={"docId": doc_id, "ofDocId": original.doc_id},
                details={"code": "D01_EXACT_FILE_DUPLICATE", "fileName": filename},
            )
            await self._doc_repo.save_document(org_id, duplicate_doc, event)
            return duplicate_doc

        try:
            return await self._store_original(
                principal,
                org_id,
                actor_role,
                doc_id,
                file_bytes,
                filename,
                info,
                file_hash,
                now,
                doc_type_hint,
            )
        except BaseException:
            await self._doc_repo.release_original(org_id, file_hash, doc_id)
            raise

    async def _holder_of(
        self, org_id: str, file_hash: str, doc_id: str, now: datetime
    ) -> Document | None:
        """The document already holding this content, or None once `doc_id` holds the claim.

        A simultaneous upload of the same file may still be rendering: wait for its document,
        whose page count and storage path the duplicate record points at."""
        for _ in range(_HOLDER_WAIT_STEPS):
            holder_id = await self._doc_repo.claim_original(org_id, file_hash, doc_id, now)
            if holder_id is None:
                return None
            holder = await self._doc_repo.get_document(org_id, holder_id)
            if holder is not None:
                return holder
            await self._sleep(_HOLDER_WAIT_SECONDS)
        raise UploadInProgressError()

    async def _store_original(
        self,
        principal: Principal,
        org_id: str,
        actor_role: str,
        doc_id: str,
        file_bytes: bytes,
        filename: str,
        info: Any,
        file_hash: str,
        now: datetime,
        doc_type_hint: DocType | None,
    ) -> Document:
        # 4. Preflight check: trial status, document limit, and file size before rendering
        await self._entitlements.check_upload_preflight(org_id, len(file_bytes))

        # 5. New document path: render pages, count rows, check limits

        ledger_rows = (
            self._spreadsheet_reader.count_rows(file_bytes, info.media_type)
            if info.is_spreadsheet and self._spreadsheet_reader
            else None
        )
        page_count, rendered_pages = self._renderer.render_and_triage(file_bytes, info.media_type)

        pages_to_read = sum(1 for rp in rendered_pages if not rp.blank)

        # 5. Entitlement reservation (AC-003-3)
        upload_req = UploadRequest(
            size_bytes=len(file_bytes),
            pages=page_count,
            pages_to_read=pages_to_read,
            ledger_rows=ledger_rows,
            exact_duplicate=False,
        )
        await self._entitlements.reserve_upload(org_id, upload_req)

        # 6. Store original in GCS
        gcs_path = await self._storage.store_original(
            org_id, doc_id, info.extension, file_bytes, info.media_type
        )

        # 7. Store rendered pages in GCS
        page_records: list[PageRecord] = []
        for rp in rendered_pages:
            image_path, thumb_path = await self._storage.store_page(
                org_id, doc_id, rp.page_no, rp.image_png, rp.thumb_png
            )
            page_records.append(
                PageRecord(
                    page_no=rp.page_no,
                    image_path=image_path,
                    thumb_path=thumb_path,
                    sha256=rp.sha256,
                    text_layer=rp.text_layer,
                    blank=rp.blank,
                    witness=rp.witness,
                    status=PageStatus.BLANK if rp.blank else PageStatus.PENDING,
                )
            )

        # 8. Build Document model
        doc_type = doc_type_hint if doc_type_hint else DocType.UNKNOWN
        document = Document(
            doc_id=doc_id,
            file_name=filename,
            content_type=info.media_type,
            size_bytes=len(file_bytes),
            page_count=page_count,
            sha256=file_hash,
            gcs_path=gcs_path,
            uploaded_by=principal.uid,
            uploaded_at=now,
            doc_type=doc_type,
            status=DocStatus.UPLOADED,
            counts_against_limits=True,
            pages=page_records,
        )

        # 9. Audit event and save
        event = AuditEvent(
            event_id=new_id("evt"),
            type="DOCUMENT_UPLOADED",
            actor_uid=principal.uid,
            actor_role=actor_role,
            at=now,
            subject={"docId": doc_id},
            details={
                "fileName": filename,
                "sizeBytes": len(file_bytes),
                "pageCount": page_count,
                "contentType": info.media_type,
            },
        )
        await self._doc_repo.save_document(org_id, document, event)

        # 10. Enqueue document workflow task
        run_id = new_id("run")
        await self._task_queue.enqueue_document_task(org_id, doc_id, run_id)

        return document

    async def mark_failed(self, org_id: str, doc_id: str, detail: str) -> None:
        """A document whose last processing attempt failed is FAILED, never left as UPLOADED."""
        doc = await self._doc_repo.get_document(org_id, doc_id)
        if doc is not None and doc.status not in (DocStatus.DONE, DocStatus.FAILED):
            await self._doc_repo.save_document(
                org_id, replace(doc, status=DocStatus.FAILED, status_detail=detail)
            )

    async def get_document(self, principal: Principal, doc_id: str) -> Document:
        """Fetch a document. Raises NotFoundError (404) if foreign or not found."""
        if principal.org_id is None:
            raise WorkspaceRequiredError()
        doc = await self._doc_repo.get_document(principal.org_id, doc_id)
        if doc is None:
            raise NotFoundError(detail=f"Document {doc_id} not found")
        return doc

    async def list_documents(
        self,
        principal: Principal,
        *,
        doc_type: str | None = None,
        month: str | None = None,
        status: str | None = None,
        duplicate: bool | None = None,
        risk: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[Document], str | None]:
        """List documents in the workspace, newest first."""
        if principal.org_id is None:
            raise WorkspaceRequiredError()
        return await self._doc_repo.list_documents(
            principal.org_id,
            doc_type=doc_type,
            month=month,
            status=status,
            duplicate=duplicate,
            risk=risk,
            limit=limit,
            cursor=cursor,
        )

    async def get_file(self, principal: Principal, doc_id: str) -> tuple[bytes, str]:
        """Fetch original document bytes. An exact duplicate serves the original's file."""
        if principal.org_id is None:
            raise WorkspaceRequiredError()
        doc = await self.get_document(principal, doc_id)
        target_id = (
            doc.duplicate.of_doc_id
            if doc.duplicate and doc.duplicate.kind == DuplicateKind.EXACT
            else doc.doc_id
        )
        ext = _extension_for(doc.file_name, doc.content_type)
        data = await self._storage.get_original(principal.org_id, target_id, ext)
        if data is None:
            raise NotFoundError(detail=f"File for document {doc_id} not found")
        return data, doc.content_type

    async def get_page_image(
        self,
        principal: Principal,
        doc_id: str,
        page_no: int,
        *,
        thumb: bool = False,
    ) -> bytes:
        """Fetch rendered page PNG or thumbnail."""
        if principal.org_id is None:
            raise WorkspaceRequiredError()
        doc = await self.get_document(principal, doc_id)
        if page_no < 1 or (doc.page_count > 0 and page_no > doc.page_count):
            raise NotFoundError(detail=f"Page {page_no} not found")
        target_id = (
            doc.duplicate.of_doc_id
            if doc.duplicate and doc.duplicate.kind == DuplicateKind.EXACT
            else doc.doc_id
        )
        data = await self._storage.get_page_image(principal.org_id, target_id, page_no, thumb=thumb)
        if data is None:
            raise NotFoundError(detail=f"Page {page_no} image not found")
        return data

    async def delete_document(self, principal: Principal, doc_id: str) -> None:
        """Remove a document, its GCS prefix and records. Records DOCUMENT_REMOVED event."""
        if principal.org_id is None:
            raise WorkspaceRequiredError()
        doc = await self.get_document(principal, doc_id)
        org_id = principal.org_id
        actor_role = principal.role or "owner"
        now = self._clock.now()

        # Delete original storage if not an exact duplicate
        if not (doc.duplicate and doc.duplicate.kind == DuplicateKind.EXACT):
            await self._storage.delete_prefix(org_id, doc_id)

        event = AuditEvent(
            event_id=new_id("evt"),
            type="DOCUMENT_REMOVED",
            actor_uid=principal.uid,
            actor_role=actor_role,
            at=now,
            subject={"docId": doc_id},
            details={"fileName": doc.file_name, "months": ",".join(doc.months)},
        )
        # Everything read from it goes too (AC-003-10).
        if self._bank_lines is not None:
            await self._bank_lines.replace_document_lines(org_id, doc_id, [])
        for records in self._records:
            await records.replace_for_document(org_id, doc_id, [])
        await self._doc_repo.delete_document(org_id, doc_id, months=doc.months, event=event)

        # Documents held as content duplicates of this one are read again, which releases them
        # now that the earlier copy is gone (AC-006-5).
        others, _ = await self._doc_repo.list_documents(org_id, limit=500)
        for other in others:
            dup = other.duplicate
            if dup and dup.kind == DuplicateKind.CONTENT and dup.of_doc_id == doc_id:
                await self._task_queue.enqueue_document_task(org_id, other.doc_id, new_id("run"))


def _extension_for(filename: str, content_type: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf") or content_type == "application/pdf":
        return ".pdf"
    if lower.endswith(".png") or content_type == "image/png":
        return ".png"
    if lower.endswith((".jpg", ".jpeg")) or content_type == "image/jpeg":
        return ".jpg"
    if lower.endswith(".xlsx"):
        return ".xlsx"
    if lower.endswith(".csv"):
        return ".csv"
    return ""
