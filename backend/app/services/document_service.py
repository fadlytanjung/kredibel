"""Document intake service (spec 003, AC-003-3, AC-003-4, AC-003-5).

Handles validation, file type sniffing, duplicate checks, plan limits & reservations,
GCS storage, page rendering & triage, task enqueueing, and audit events.
"""

import hashlib

from app.core.auth import Principal
from app.core.clock import Clock
from app.core.ids import new_id
from app.domain.errors import ValidationProblem, WorkspaceRequiredError
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
from app.domain.plans import UploadRequest
from app.ports.document_repository import DocumentRepository
from app.ports.document_storage import DocumentStorage
from app.ports.page_renderer import PageRenderer
from app.ports.spreadsheet_reader import SpreadsheetReader
from app.ports.task_queue import TaskQueue
from app.services.entitlement_service import EntitlementService


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
    ) -> None:
        self._doc_repo = doc_repo
        self._storage = storage
        self._task_queue = task_queue
        self._entitlements = entitlements
        self._renderer = renderer
        self._clock = clock
        self._spreadsheet_reader = spreadsheet_reader

    async def upload(
        self,
        principal: Principal,
        file_bytes: bytes,
        filename: str,
        doc_type_hint: DocType | None = None,
    ) -> Document:
        """Upload and process a document file."""
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

        # 3. Check for exact duplicate in workspace (AC-003-5)
        original = await self._doc_repo.find_original_by_sha256(org_id, file_hash)
        if original is not None:
            doc_id = new_id("doc")
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

        # 4. Preflight check: trial status, document limit, and file size before rendering
        await self._entitlements.check_upload_preflight(org_id, len(file_bytes))

        # 5. New document path: render pages, count rows, check limits
        doc_id = new_id("doc")

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
