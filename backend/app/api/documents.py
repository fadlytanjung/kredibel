"""Document intake routes: upload, list, get, file stream, page render, and delete (spec 003).

Normative references:
- docs/10-api-contract.md §2.2
- contracts/openapi.yaml /api/documents endpoints
- AC-003-1, AC-003-2, AC-003-5, AC-003-7, AC-003-10, AC-003-11
"""

from typing import Any

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status

from app.api.deps import ServiceProvider
from app.core.auth import Principal, PrincipalDependency
from app.domain.models.document import DocStatus, DocType, Document, TextLayerStatus


def _document_body(doc: Document) -> dict[str, Any]:
    pages = [
        {
            "pageNo": p.page_no,
            "status": p.status.value if hasattr(p.status, "value") else str(p.status),
            "textLayer": p.text_layer == TextLayerStatus.USABLE,
            "witness": p.witness.value if hasattr(p.witness, "value") else str(p.witness),
            "agreement": str(p.agreement) if p.agreement is not None else None,
        }
        for p in doc.pages
    ]
    duplicate_info = None
    if doc.duplicate:
        duplicate_info = {
            "kind": (
                doc.duplicate.kind.value
                if hasattr(doc.duplicate.kind, "value")
                else str(doc.duplicate.kind)
            ),
            "code": doc.duplicate.code,
            "ofDocId": doc.duplicate.of_doc_id,
            "decision": (
                doc.duplicate.decision.value
                if hasattr(doc.duplicate.decision, "value")
                else str(doc.duplicate.decision)
            ),
            "reviewItemId": doc.duplicate.review_item_id,
        }

    body: dict[str, Any] = {
        "docId": doc.doc_id,
        "fileName": doc.file_name,
        "contentType": doc.content_type,
        "sizeBytes": doc.size_bytes,
        "pageCount": doc.page_count,
        "docType": doc.doc_type.value if hasattr(doc.doc_type, "value") else str(doc.doc_type),
        "typeConfidence": str(doc.type_confidence) if doc.type_confidence is not None else None,
        "status": doc.status.value if hasattr(doc.status, "value") else str(doc.status),
        "statusDetail": doc.status_detail,
        "months": doc.months,
        "duplicate": duplicate_info,
        "heldAsDuplicate": doc.held_as_duplicate,
        "countsAgainstLimits": doc.counts_against_limits,
        "pages": pages,
        "reading": doc.reading,
        "statementMeta": doc.statement_meta,
        "ledgerMeta": doc.ledger_meta,
        "pdf": doc.pdf,
        "integrity": doc.integrity,
        "risk": doc.risk,
        "uploadedBy": doc.uploaded_by,
        "uploadedAt": doc.uploaded_at.isoformat(),
        "lastRunId": doc.last_run_id,
    }
    return {k: v for k, v in body.items() if v is not None or k in ("duplicate",)}


def create_documents_router(
    provider: ServiceProvider, workspace_dep: PrincipalDependency
) -> APIRouter:
    router = APIRouter(prefix="/api/documents", tags=["documents"])

    @router.post("", status_code=status.HTTP_201_CREATED)
    async def upload_document(
        file: UploadFile = File(...),
        doc_type_hint: DocType | None = Form(None, alias="docTypeHint"),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        file_bytes = await file.read()
        filename = file.filename or "uploaded"
        doc = await provider.document_service.upload(
            principal=principal,
            file_bytes=file_bytes,
            filename=filename,
            doc_type_hint=doc_type_hint,
        )
        return _document_body(doc)

    @router.get("")
    async def list_documents(
        doc_type: DocType | None = Query(None, alias="type"),
        month: str | None = Query(None),
        doc_status: DocStatus | None = Query(None, alias="status"),
        duplicate: bool | None = Query(None),
        risk: str | None = Query(None),
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = Query(None),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        docs, next_cursor = await provider.document_service.list_documents(
            principal=principal,
            doc_type=doc_type.value if doc_type else None,
            month=month,
            status=doc_status.value if doc_status else None,
            duplicate=duplicate,
            risk=risk,
            limit=limit,
            cursor=cursor,
        )
        return {
            "items": [_document_body(d) for d in docs],
            "nextCursor": next_cursor,
        }

    @router.get("/{doc_id}")
    async def get_document(
        doc_id: str,
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        doc = await provider.document_service.get_document(principal, doc_id)
        return _document_body(doc)

    @router.get("/{doc_id}/file")
    async def get_document_file(
        doc_id: str,
        principal: Principal = Depends(workspace_dep),
    ) -> Response:
        data, content_type = await provider.document_service.get_file(principal, doc_id)
        return Response(
            content=data,
            media_type=content_type or "application/octet-stream",
            headers={"Content-Disposition": f'inline; filename="{doc_id}"'},
        )

    @router.get("/{doc_id}/pages/{page_no}")
    async def get_document_page(
        doc_id: str,
        page_no: int,
        variant: str = Query("full", pattern="^(full|thumb)$"),
        principal: Principal = Depends(workspace_dep),
    ) -> Response:
        thumb = variant == "thumb"
        png_bytes = await provider.document_service.get_page_image(
            principal=principal,
            doc_id=doc_id,
            page_no=page_no,
            thumb=thumb,
        )
        return Response(content=png_bytes, media_type="image/png")

    @router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_document(
        doc_id: str,
        principal: Principal = Depends(workspace_dep),
    ) -> Response:
        await provider.document_service.delete_document(principal, doc_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
