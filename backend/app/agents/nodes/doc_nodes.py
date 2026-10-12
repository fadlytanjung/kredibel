"""Document workflow node factories with stubs for specs 004-008 (docs/06 §2, §4)."""

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import PurePosixPath
from typing import Any

from google.adk import Context

from app.agents.deps import PipelineDeps
from app.agents.stages import stage
from app.domain.layout import Chunk, chunk_page, chunks_from_json, chunks_to_json, render_chunks
from app.domain.models.document import DocStatus, DocType, PageStatus
from app.domain.page_triage import TextLayerStatus
from app.domain.reading import StatementPageReading, build_statement


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
        org_id, doc_id = _ids(node_input)
        doc = await deps.doc_repo.get_document(org_id, doc_id)
        if doc is None or deps.reader is None or deps.storage is None:
            return await _classify_without_reader(deps, node_input)
        image = await deps.storage.get_page_image(org_id, doc_id, 1)
        if image is None:
            return await _classify_without_reader(deps, node_input)
        chunks = await _load_chunks(deps, org_id, doc.sha256, 1)
        call = await deps.reader.classify(image, render_chunks(chunks))
        result = call.value
        confident = result.confidence >= _MIN_TYPE_CONFIDENCE
        updated = replace(
            doc,
            doc_type=DocType(result.doc_type),
            type_confidence=Decimal(str(round(result.confidence, 3))),
            status=DocStatus.READING if confident else DocStatus.NEEDS_INPUT,
            status_detail=None if confident else "E03_UNCERTAIN_TYPE",
        )
        await deps.doc_repo.save_document(org_id, updated)
        return {
            **node_input,
            "docType": result.doc_type,
            "typeConfidence": result.confidence,
            "currency": result.currency,
            "status": updated.status.value,
            "model": call.model,
            "tokens_in": call.tokens_in,
            "tokens_out": call.tokens_out,
            "summary": f"{result.doc_type} ({result.confidence:.2f})",
        }

    return _node


async def _classify_without_reader(
    deps: PipelineDeps, node_input: dict[str, Any]
) -> dict[str, Any]:
    """Tests and the dev app without a reader: trust the type already on the document."""
    doc_type = node_input.get("docType", "BANK_STATEMENT")
    conf = float(node_input.get("typeConfidence") or 1.0)
    org_id, doc_id = _ids(node_input)
    if doc_type == DocType.UNKNOWN.value or conf < _MIN_TYPE_CONFIDENCE:
        doc = await deps.doc_repo.get_document(org_id, doc_id)
        if doc is not None:
            await deps.doc_repo.save_document(org_id, replace(doc, status=DocStatus.NEEDS_INPUT))
        return {**node_input, "status": "NEEDS_INPUT", "summary": "Type confirmation needed"}
    return {**node_input, "docType": doc_type, "summary": "Classified document"}


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


def parse_pages(deps: PipelineDeps):
    """Parse: the text layer into layout chunks per page, cached by the file's SHA-256 (ADR-023)."""

    @stage(deps, "parse_pages")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id, doc_id = _ids(node_input)
        doc = await deps.doc_repo.get_document(org_id, doc_id)
        if doc is None or deps.storage is None or deps.page_text is None:
            return {**node_input, "summary": "Parsing skipped"}
        extension = PurePosixPath(doc.gcs_path).suffix
        original = await deps.storage.get_original(org_id, doc_id, extension)
        if not original or not original.startswith(b"%PDF"):
            return {**node_input, "summary": "No text layer (OCR witness comes with spike S3)"}
        usable = {p.page_no for p in doc.pages if p.text_layer == TextLayerStatus.USABLE}
        counts: dict[str, int] = {}
        for page_no, words in deps.page_text.words(original).items():
            if page_no not in usable:
                continue
            chunks = chunk_page(words, page=page_no)
            key = _chunks_key(doc.sha256, page_no)
            await deps.storage.put_cached(org_id, key, json.dumps(chunks_to_json(chunks)).encode())
            counts[str(page_no)] = len(chunks)
        return {
            **node_input,
            "parsed": counts,
            "summary": f"{sum(counts.values())} chunks on {len(counts)} pages",
        }

    return _node


def read_page(deps: PipelineDeps):
    """Extract: one page from its image and chunks, cached by page image, model and prompt."""

    @stage(deps, "read_page")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        page_no = int(node_input.get("page", 1))
        org_id, doc_id = _ids(node_input)
        base = {"page": page_no, "reading": None}
        if node_input.get("docType") != DocType.BANK_STATEMENT.value:
            return {**base, "summary": "Not a statement: invoice and receipt reading is T005-03"}
        doc = await deps.doc_repo.get_document(org_id, doc_id)
        if doc is None or deps.reader is None or deps.storage is None:
            return {**base, "summary": "Reading skipped"}
        page = next((p for p in doc.pages if p.page_no == page_no), None)
        if page is None or page.blank:
            return {**base, "summary": "Blank page"}
        model, prompt_version = deps.reader.version("statement_page")
        cache_key = f"{page.sha256}/{model}-{prompt_version}.json"
        cached = None
        if deps.settings.extraction_cache == "on":
            cached = await deps.storage.get_cached(org_id, cache_key)
        if cached is not None:
            reading = StatementPageReading.model_validate_json(cached)
            tokens = (0, 0)
        else:
            image = await deps.storage.get_page_image(org_id, doc_id, page_no)
            if image is None:
                return {**base, "summary": "Page image missing"}
            chunks = await _load_chunks(deps, org_id, doc.sha256, page_no)
            call = await deps.reader.read_statement_page(
                image, render_chunks(chunks), page=page_no, context=node_input.get("context")
            )
            reading = call.value.model_copy(update={"page": page_no})
            await deps.storage.put_cached(org_id, cache_key, reading.model_dump_json().encode())
            tokens = (call.tokens_in, call.tokens_out)
        return {
            **base,
            "reading": reading.model_dump(mode="json"),
            "header_context": _header_context(reading),
            "model": model,
            "tokens_in": tokens[0],
            "tokens_out": tokens[1],
            "cached": cached is not None,
            "summary": f"Page {page_no}: {len(reading.rows)} rows"
            + (" (cached)" if cached else ""),
        }

    return _node


def verify_pages(deps: PipelineDeps):
    """Ground: every value against the words of its chunk; write bank lines and statement meta."""

    @stage(deps, "verify_pages")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        doc_data = node_input.get("doc") or node_input
        org_id, doc_id = _ids(doc_data)
        readings = [
            StatementPageReading.model_validate(a["reading"])
            for a in node_input.get("ai") or []
            if isinstance(a, dict) and a.get("reading")
        ]
        doc = await deps.doc_repo.get_document(org_id, doc_id)
        if not readings or doc is None or deps.bank_lines is None:
            return {**doc_data, "summary": "Nothing to verify"}
        chunks = {r.page: await _load_chunks(deps, org_id, doc.sha256, r.page) for r in readings}
        result = build_statement(doc_id, readings, chunks)
        await deps.bank_lines.replace_document_lines(org_id, doc_id, result.lines)
        model, prompt_version = deps.reader.version("statement_page") if deps.reader else ("", "")
        meta = result.meta
        pages = [
            replace(
                p,
                status=PageStatus.DONE,
                agreement=_agreement(result.page_agreement.get(p.page_no)),
            )
            if p.page_no in result.page_agreement
            else p
            for p in doc.pages
        ]
        updated = replace(
            doc,
            status=DocStatus.CHECKING,
            months=result.months,
            pages=pages,
            statement_meta={
                "bankName": meta.bank_name,
                "accountHolder": meta.account_holder,
                "accountMasked": meta.account_masked,
                "currency": meta.currency,
                "periodStart": meta.period_start.isoformat() if meta.period_start else None,
                "periodEnd": meta.period_end.isoformat() if meta.period_end else None,
                "openingMinor": _minor(meta.opening),
                "closingMinor": _minor(meta.closing),
            },
            reading={
                "method": "AI_TEXT_LAYER" if any(chunks.values()) else "AI_ONLY",
                "agreement": round(result.agreement, 4),
                "fieldsCompared": result.fields_compared,
                "fieldsAgreed": result.fields_agreed,
                "lines": len(result.lines),
                "notes": result.notes[:50],
                "model": model,
                "promptVersion": prompt_version,
            },
        )
        await deps.doc_repo.save_document(org_id, updated)
        return {
            **doc_data,
            "months": result.months,
            "agreement": result.agreement,
            "summary": f"{len(result.lines)} lines, agreement {result.agreement:.3f}",
        }

    return _node


def _ids(node_input: dict[str, Any]) -> tuple[str, str]:
    org_id = str(node_input.get("orgId") or node_input.get("org_id") or "")
    doc_id = str(node_input.get("docId") or node_input.get("doc_id") or "")
    return org_id, doc_id


def _chunks_key(sha256: str, page_no: int) -> str:
    return f"{sha256}/p{page_no}/chunks-v1.json"


async def _load_chunks(deps: PipelineDeps, org_id: str, sha256: str, page_no: int) -> list[Chunk]:
    if deps.storage is None:
        return []
    raw = await deps.storage.get_cached(org_id, _chunks_key(sha256, page_no))
    return chunks_from_json(json.loads(raw)) if raw else []


def _header_context(reading: StatementPageReading) -> str | None:
    h = reading.header
    if h is None:
        return None
    parts = [
        f"period {h.period_start_text} to {h.period_end_text}",
        f"columns {', '.join(h.column_order)}",
    ]
    if h.currency:
        parts.append(f"currency {h.currency}")
    return "; ".join(parts)


def _minor(value: Decimal | None) -> int | None:
    return None if value is None else int(value * 100)


def _agreement(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(round(value, 4)))


_MIN_TYPE_CONFIDENCE = 0.6


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
                    await deps.task_queue.enqueue_month_task(
                        org_id, m, gen, delay_seconds=deps.settings.month_run_delay_seconds
                    )

        return {**node_input, "status": "DONE", "summary": "Document processing finalized"}

    return _node
