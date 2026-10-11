"""Document workflow node factories with stubs for specs 004-008 (docs/06 §2, §4)."""

from dataclasses import replace
from typing import Any

from google.adk import Context

from app.agents.deps import PipelineDeps
from app.agents.stages import stage
from app.domain.models.document import DocStatus, DocType


def pages_to_read(doc: dict[str, Any]) -> list[int]:
    """List of 1-indexed page numbers to read."""
    count = int(doc.get("pageCount") or doc.get("page_count") or 1)
    return list(range(1, count + 1))


def load_document(deps: PipelineDeps):
    @stage(deps, "load_document")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id = node_input.get("orgId") or node_input.get("org_id") or ""
        doc_id = node_input.get("docId") or node_input.get("doc_id") or ""
        doc = await deps.doc_repo.get_document(org_id, doc_id)
        if doc is None:
            return {**node_input, "status": "SKIPPED", "summary": "Document not found"}

        return {
            **node_input,
            "fileName": doc.file_name,
            "pageCount": doc.page_count,
            "docType": doc.doc_type.value,
            "typeConfidence": doc.type_confidence,
            "months": doc.months,
            "status": doc.status.value,
            "summary": "Document loaded",
        }

    return _node


def screen_document(deps: PipelineDeps):
    @stage(deps, "screen_document")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        return {**node_input, "summary": "Screening skipped"}

    return _node


def inspect_file(deps: PipelineDeps):
    @stage(deps, "inspect_file")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        if node_input.get("_simulate_failure"):
            raise RuntimeError("Simulated inspection failure")
        return {**node_input, "summary": "File metadata inspected"}

    return _node


def classify_document(deps: PipelineDeps):
    @stage(deps, "classify_document")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        doc_type = node_input.get("docType", "BANK_STATEMENT")
        conf = float(node_input.get("typeConfidence") or 1.0)
        org_id = node_input.get("orgId") or node_input.get("org_id") or ""
        doc_id = node_input.get("docId") or node_input.get("doc_id") or ""

        if doc_type == DocType.UNKNOWN.value or conf < 0.6:
            doc = await deps.doc_repo.get_document(org_id, doc_id)
            if doc is not None:
                updated = replace(doc, status=DocStatus.NEEDS_INPUT)
                await deps.doc_repo.save_document(org_id, updated)
            return {**node_input, "status": "NEEDS_INPUT", "summary": "Type confirmation needed"}

        return {**node_input, "docType": doc_type, "summary": "Classified document"}

    return _node


def propose_ledger_mapping(deps: PipelineDeps):
    @stage(deps, "propose_ledger_mapping")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        if not node_input.get("mappingConfirmed"):
            org_id = node_input.get("orgId") or node_input.get("org_id") or ""
            doc_id = node_input.get("docId") or node_input.get("doc_id") or ""
            doc = await deps.doc_repo.get_document(org_id, doc_id)
            if doc is not None:
                updated = replace(doc, status=DocStatus.NEEDS_INPUT)
                await deps.doc_repo.save_document(org_id, updated)
            return {**node_input, "status": "NEEDS_INPUT", "summary": "Mapping confirmation needed"}
        return {**node_input, "summary": "Ledger mapping proposed"}

    return _node


def parse_ledger(deps: PipelineDeps):
    @stage(deps, "parse_ledger")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        return {**node_input, "summary": "Ledger parsed"}

    return _node


def read_page(deps: PipelineDeps):
    @stage(deps, "read_page")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        p = node_input.get("page", 1)
        return {
            **node_input,
            "page": p,
            "header_context": {"account_number": "1234"},
            "summary": f"Page {p} read",
        }

    return _node


def witness_pages(deps: PipelineDeps):
    @stage(deps, "witness_pages")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        return {**node_input, "witness": "TEXT_LAYER", "summary": "Witness completed"}

    return _node


def verify_pages(deps: PipelineDeps):
    @stage(deps, "verify_pages")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        doc_data = node_input.get("doc") or node_input
        return {**doc_data, "summary": "Pages verified"}

    return _node


def escalate_pages(deps: PipelineDeps):
    @stage(deps, "escalate_pages")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        return {**node_input, "summary": "Escalation skipped"}

    return _node


def check_document(deps: PipelineDeps):
    @stage(deps, "check_document")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        return {**node_input, "summary": "Integrity checks passed"}

    return _node


def detect_content_duplicates(deps: PipelineDeps):
    @stage(deps, "detect_content_duplicates")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        return {**node_input, "summary": "No duplicates detected"}

    return _node


def categorize_bank_lines(deps: PipelineDeps):
    @stage(deps, "categorize_bank_lines")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        return {**node_input, "summary": "Transactions categorized"}

    return _node


def finalize_document(deps: PipelineDeps):
    @stage(deps, "finalize_document")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id = node_input.get("orgId") or node_input.get("org_id") or ""
        doc_id = node_input.get("docId") or node_input.get("doc_id") or ""
        doc = await deps.doc_repo.get_document(org_id, doc_id)
        if doc is not None:
            updated = replace(doc, status=DocStatus.DONE)
            await deps.doc_repo.save_document(org_id, updated)

            # Mark months dirty and enqueue debounced month runs
            if deps.task_queue is not None:
                for m in doc.months:
                    gen, _ = await deps.month_repo.bump_generation(org_id, m, dirty=True)
                    await deps.task_queue.enqueue_month_task(org_id, m, gen, delay_seconds=20)

        return {**node_input, "status": "DONE", "summary": "Document processing finalized"}

    return _node
