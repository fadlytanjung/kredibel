"""Document workflow node factories with stubs for specs 004-008 (docs/06 §2, §4)."""

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from pathlib import PurePosixPath
from typing import Any

from google.adk import Context
from pydantic import BaseModel

from app.agents.deps import PipelineDeps
from app.agents.stages import stage
from app.domain.categorize import (
    Categorized,
    CategoryPolicy,
    Framework,
    by_rules,
    from_model,
    keep_person_categories,
)
from app.domain.checks.base import CheckContext, DeclaredAccount, PdfInfo, run_document_checks
from app.domain.corrections import keep_corrections
from app.domain.duplicates import (
    InvoiceKey,
    Match,
    ReceiptKey,
    StatementKey,
    invoice_duplicate,
    receipt_duplicate,
    statement_duplicate,
)
from app.domain.findings import Evidence, Finding, finding_id
from app.domain.invoice_records import build_invoices, build_receipts, document_type_of
from app.domain.layout import Chunk, chunk_page, chunks_from_json, chunks_to_json, render_chunks
from app.domain.ledger_parse import parse_ledger_content
from app.domain.models.bank_line import BankLine
from app.domain.models.document import (
    DocStatus,
    DocType,
    DuplicateDecision,
    DuplicateInfo,
    DuplicateKind,
    PageStatus,
)
from app.domain.page_triage import TextLayerStatus
from app.domain.reading import (
    CategorizeResult,
    InvoicePageReading,
    ReceiptPageReading,
    StatementPageReading,
    TransactionItem,
    build_statement,
)
from app.domain.risk import assess_document_risk
from app.domain.verdict import integrity_verdict


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


def _pdf_key(sha256: str) -> str:
    return f"{sha256}/pdf-v1.json"


def inspect_file(deps: PipelineDeps):
    """The original PDF's metadata, saves and value fonts (docs/07 §3.3): the full inspection goes
    to the extraction cache for check_document, a summary onto the document."""

    @stage(deps, "inspect_file")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        if node_input.get("_simulate_failure"):
            raise RuntimeError("Simulated inspection failure")
        org_id, doc_id = _ids(node_input)
        doc = await deps.doc_repo.get_document(org_id, doc_id)
        if doc is None or deps.inspector is None or deps.storage is None:
            return {**node_input, "summary": "Inspection skipped"}
        first_page = await deps.storage.get_page_image(org_id, doc_id, 1)
        if first_page is not None:  # every type: receipts photographed twice are found by it (D05)
            doc = replace(doc, p_hash=deps.inspector.page_hash(first_page))
            await deps.doc_repo.save_document(org_id, doc)
        if not doc.content_type.endswith("pdf"):
            return {**node_input, "summary": "Not a PDF"}
        original = await deps.storage.get_original(
            org_id, doc_id, PurePosixPath(doc.gcs_path).suffix
        )
        if original is None:
            return {**node_input, "summary": "Original missing"}
        info = deps.inspector.inspect_pdf(original)
        await deps.storage.put_cached(
            org_id, _pdf_key(doc.sha256), json.dumps(info.to_dict()).encode()
        )
        summary = {k: v for k, v in info.to_dict().items() if k != "valueFonts"}
        await deps.doc_repo.save_document(org_id, replace(doc, pdf=summary))
        return {
            **node_input,
            "summary": f"{info.revisions} save(s), producer {info.producer or 'unknown'}",
        }

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
        if node_input.get("mappingConfirmed"):
            return {**node_input, "summary": "Ledger mapping confirmed"}

        org_id, doc_id = _ids(node_input)
        doc = await deps.doc_repo.get_document(org_id, doc_id)
        if doc is None or deps.storage is None:
            return {**node_input, "summary": "Ledger mapping skipped"}

        ext = PurePosixPath(doc.gcs_path).suffix if doc.gcs_path else ".csv"
        content_bytes = await deps.storage.get_original(org_id, doc_id, ext)
        if not content_bytes:
            return {**node_input, "summary": "Empty ledger content"}

        text = content_bytes.decode("utf-8", errors="replace")
        lines = [ln for ln in text.splitlines() if not ln.startswith("#") and ln.strip()]
        if not lines:
            return {**node_input, "summary": "Empty ledger rows"}

        import csv
        reader = csv.DictReader(lines)
        headers = [h.lower().strip() for h in (reader.fieldnames or []) if h]

        has_date = any(k in headers for k in ("date", "posting date", "trans date"))
        has_acct = any(k in headers for k in ("account", "account code", "acct", "code"))
        has_debit_credit = "debit" in headers and "credit" in headers
        has_signed_amount = any(k in headers for k in ("amount", "net"))

        is_standard = has_date and has_acct and (has_debit_credit or has_signed_amount)
        if is_standard:
            return {
                **node_input,
                "mappingConfirmed": True,
                "summary": "Standard ledger layout auto-confirmed",
            }

        updated = replace(
            doc,
            status=DocStatus.NEEDS_INPUT,
            status_detail="Ledger mapping confirmation needed",
        )
        await deps.doc_repo.save_document(org_id, updated)
        return {**node_input, "status": "NEEDS_INPUT", "summary": "Mapping confirmation needed"}

    return _node


def parse_ledger(deps: PipelineDeps):
    @stage(deps, "parse_ledger")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id, doc_id = _ids(node_input)
        if deps.storage is not None and deps.ledger is not None:
            doc = await deps.doc_repo.get_document(org_id, doc_id)
            if doc is not None and doc.gcs_path:
                ext = PurePosixPath(doc.gcs_path).suffix
                content_bytes = await deps.storage.get_original(org_id, doc_id, ext)
                if content_bytes:
                    text = content_bytes.decode("utf-8", errors="replace")

                    currency = "IDR"
                    if deps.workspaces is not None:
                        ws = await deps.workspaces.get_workspace(org_id)
                        if ws and ws.currency:
                            currency = ws.currency

                    res = parse_ledger_content(text, doc_id=doc_id, currency=currency)
                    if res.too_many_bad_rows:
                        msg = f"Over 2% invalid rows ({len(res.bad_rows)} bad rows)"
                        updated = replace(
                            doc,
                            status=DocStatus.NEEDS_INPUT,
                            status_detail=msg,
                        )
                        await deps.doc_repo.save_document(org_id, updated)
                        return {
                            **node_input,
                            "status": "NEEDS_INPUT",
                            "summary": "Excessive bad rows in ledger",
                        }

                    if res.rows:
                        await deps.ledger.save_rows(org_id, res.rows)
                        months = sorted({r.date.strftime("%Y-%m") for r in res.rows})
                        ledger_meta = {
                            "rowsImported": len(res.rows),
                            "rows": len(res.rows),
                            "dateFrom": min(r.date for r in res.rows).isoformat(),
                            "dateTo": max(r.date for r in res.rows).isoformat(),
                            "badRowsCount": len(res.bad_rows),
                        }
                        updated = replace(doc, months=months, ledger_meta=ledger_meta)
                        await deps.doc_repo.save_document(org_id, updated)
                        return {
                            **node_input,
                            "months": months,
                            "ledgerMeta": ledger_meta,
                            "summary": f"Ledger parsed: {len(res.rows)} entries",
                        }
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


# What each document type is read with: the reader task (prompt) and its response schema.
_READERS: dict[str, tuple[str, type[BaseModel]]] = {
    DocType.BANK_STATEMENT.value: ("statement_page", StatementPageReading),
    DocType.SALES_INVOICE.value: ("invoice_page", InvoicePageReading),
    DocType.PURCHASE_INVOICE.value: ("invoice_page", InvoicePageReading),
    DocType.RECEIPT.value: ("receipt_page", ReceiptPageReading),
}


def _read_summary(page_no: int, reading: BaseModel) -> str:
    count = len(
        getattr(reading, "rows", None)
        or getattr(reading, "lines", None)
        or getattr(reading, "items", None)
        or []
    )
    return (
        f"Page {page_no}: {count} "
        + {
            "StatementPageReading": "rows",
            "InvoicePageReading": "lines",
            "ReceiptPageReading": "items",
        }[type(reading).__name__]
    )


def read_page(deps: PipelineDeps):
    """Extract: one page from its image and chunks, cached by page image, model and prompt."""

    @stage(deps, "read_page")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        page_no = int(node_input.get("page", 1))
        org_id, doc_id = _ids(node_input)
        base = {"page": page_no, "reading": None}
        reader = _READERS.get(str(node_input.get("docType")))
        if reader is None:
            return {**base, "summary": f"Not read: {node_input.get('docType')}"}
        task, schema = reader
        doc = await deps.doc_repo.get_document(org_id, doc_id)
        if doc is None or deps.reader is None or deps.storage is None:
            return {**base, "summary": "Reading skipped"}
        page = next((p for p in doc.pages if p.page_no == page_no), None)
        if page is None or page.blank:
            return {**base, "summary": "Blank page"}
        model, prompt_version = deps.reader.version(task)
        cache_key = f"{page.sha256}/{model}-{prompt_version}.json"
        cached = None
        if deps.settings.extraction_cache == "on":
            cached = await deps.storage.get_cached(org_id, cache_key)
        reading: BaseModel
        if cached is not None:
            reading = schema.model_validate_json(cached)
            tokens = (0, 0)
        else:
            image = await deps.storage.get_page_image(org_id, doc_id, page_no)
            if image is None:
                return {**base, "summary": "Page image missing"}
            chunks = render_chunks(await _load_chunks(deps, org_id, doc.sha256, page_no))
            if task == "statement_page":
                call: Any = await deps.reader.read_statement_page(
                    image, chunks, page=page_no, context=node_input.get("context")
                )
            elif task == "invoice_page":
                call = await deps.reader.read_invoice_page(image, chunks, page=page_no)
            else:
                call = await deps.reader.read_receipt_page(image, chunks, page=page_no)
            reading = call.value.model_copy(update={"page": page_no})
            await deps.storage.put_cached(org_id, cache_key, reading.model_dump_json().encode())
            tokens = (call.tokens_in, call.tokens_out)
        header = _header_context(reading) if isinstance(reading, StatementPageReading) else None
        return {
            **base,
            "reading": reading.model_dump(mode="json"),
            "header_context": header,
            "model": model,
            "tokens_in": tokens[0],
            "tokens_out": tokens[1],
            "cached": cached is not None,
            "summary": _read_summary(page_no, reading) + (" (cached)" if cached else ""),
        }

    return _node


def verify_pages(deps: PipelineDeps):
    """Ground: every value against the page's words; write the records and the document's
    reading summary (statements: bank lines and statement meta; invoices; receipts)."""

    @stage(deps, "verify_pages")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        doc_data = node_input.get("doc") or node_input
        org_id, doc_id = _ids(doc_data)
        raw = [
            a["reading"]
            for a in node_input.get("ai") or []
            if isinstance(a, dict) and a.get("reading")
        ]
        doc = await deps.doc_repo.get_document(org_id, doc_id)
        reader = _READERS.get(str(doc_data.get("docType") or (doc.doc_type.value if doc else "")))
        if not raw or doc is None or reader is None:
            return {**doc_data, "summary": "Nothing to verify"}
        task, schema = reader
        readings: list[Any] = [schema.model_validate(r) for r in raw]
        chunks = {r.page: await _load_chunks(deps, org_id, doc.sha256, r.page) for r in readings}
        model, prompt_version = deps.reader.version(task) if deps.reader else ("", "")
        if task == "statement_page":
            outcome = await _statement(deps, org_id, doc_id, readings, chunks)
        else:
            outcome = await _records(deps, org_id, doc, task, readings, chunks)
        if outcome is None:
            return {**doc_data, "summary": "Nothing to verify"}
        pages = [
            replace(
                p,
                status=PageStatus.DONE,
                agreement=_agreement(outcome.page_agreement.get(p.page_no)),
            )
            if p.page_no in outcome.page_agreement
            else p
            for p in doc.pages
        ]
        updated = replace(
            doc,
            doc_type=DocType(outcome.doc_type) if outcome.doc_type else doc.doc_type,
            status=DocStatus.CHECKING,
            months=outcome.months,
            pages=pages,
            statement_meta=outcome.statement_meta or doc.statement_meta,
            reading={
                "method": "AI_TEXT_LAYER" if any(chunks.values()) else "AI_ONLY",
                "agreement": round(outcome.agreement, 4),
                "fieldsCompared": outcome.compared,
                "fieldsAgreed": outcome.agreed,
                "lines": outcome.records,
                "notes": outcome.notes[:50],
                "model": model,
                "promptVersion": prompt_version,
            },
        )
        await deps.doc_repo.save_document(org_id, updated)
        return {
            **doc_data,
            "months": outcome.months,
            "agreement": outcome.agreement,
            "summary": f"{outcome.records} {outcome.noun}, agreement {outcome.agreement:.3f}",
        }

    return _node


@dataclass
class _Verified:
    records: int
    noun: str
    agreed: int
    compared: int
    page_agreement: dict[int, float]
    months: list[str]
    notes: list[str]
    statement_meta: dict[str, Any] | None = None
    doc_type: str | None = None  # an invoice document's type, decided in code (AC-005-1)

    @property
    def agreement(self) -> float:
        return 1.0 if self.compared == 0 else self.agreed / self.compared


async def _statement(
    deps: PipelineDeps,
    org_id: str,
    doc_id: str,
    readings: list[StatementPageReading],
    chunks: dict[int, list[Chunk]],
) -> _Verified | None:
    if deps.bank_lines is None:
        return None
    result = build_statement(doc_id, readings, chunks)
    stored = await deps.bank_lines.list_lines(org_id, doc_id=doc_id, limit=5000)
    lines = keep_corrections(result.lines, stored)
    keep_person_categories(lines, stored)  # a re-read never undoes a person's category
    await deps.bank_lines.replace_document_lines(org_id, doc_id, lines)
    meta = result.meta
    return _Verified(
        records=len(lines),
        noun="lines",
        agreed=result.fields_agreed,
        compared=result.fields_compared,
        page_agreement=result.page_agreement,
        months=result.months,
        notes=result.notes,
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
    )


async def _own_names(deps: PipelineDeps, org_id: str) -> list[str]:
    workspace = await deps.workspaces.get_workspace(org_id) if deps.workspaces else None
    if workspace is None:
        return []
    profile = workspace.profile
    return [workspace.name, profile.legal_name or "", profile.trading_name or "", *profile.aliases]


async def _records(
    deps: PipelineDeps,
    org_id: str,
    doc: Any,
    task: str,
    readings: list[Any],
    chunks: dict[int, list[Chunk]],
) -> _Verified | None:
    words = {page: [w for c in cs for w in c.words] for page, cs in chunks.items()}
    if task == "invoice_page":
        if deps.invoices is None:
            return None
        names = await _own_names(deps, org_id)
        result: Any = build_invoices(
            doc.doc_id, readings, words, classified=doc.doc_type.value, own_names=names
        )
        stored = await deps.invoices.list_records(org_id, doc_id=doc.doc_id)
        records = keep_corrections(result.records, stored)
        await deps.invoices.replace_for_document(org_id, doc.doc_id, records)
        noun = "invoices"
        doc_type = document_type_of([r.kind for r in result.records], doc.doc_type.value)
    else:
        if deps.receipts is None:
            return None
        result = build_receipts(doc.doc_id, readings, words)
        stored = await deps.receipts.list_records(org_id, doc_id=doc.doc_id)
        records = keep_corrections(result.records, stored)
        await deps.receipts.replace_for_document(org_id, doc.doc_id, records)
        noun = "receipts"
        doc_type = None
    return _Verified(
        records=len(result.records),
        noun=noun,
        agreed=result.agreed,
        compared=result.compared,
        page_agreement=result.page_agreement,
        months=result.months,
        notes=result.notes,
        doc_type=doc_type,
    )


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
    """Integrity checks (docs/08 §2): arithmetic, structure, extraction and holder findings with
    evidence, upserted by ID; the document gets its verdict (docs/08 §3)."""

    @stage(deps, "check_document")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id, doc_id = _ids(node_input)
        doc = await deps.doc_repo.get_document(org_id, doc_id)
        if doc is None or deps.forensics is None or deps.findings is None:
            return {**node_input, "summary": "Checks skipped"}
        if doc.doc_type == DocType.LEDGER_EXPORT:
            return {**node_input, "summary": "Ledger exports have no integrity verdict"}
        context = await _check_context(deps, org_id, doc)
        fresh = run_document_checks(context)
        stored = await deps.findings.replace_document_findings(
            org_id, doc_id, fresh, run_id=node_input.get("runId")
        )
        live = [f for f in stored if f.status in ("OPEN", "ACKNOWLEDGED")]
        verdict = integrity_verdict(live, deps.forensics)
        doc_risk = (
            assess_document_risk(verdict, stored, deps.risk_policy)
            if deps.risk_policy is not None
            else None
        )
        risk_dict = (
            {
                "level": doc_risk.level,
                "score": doc_risk.score,
                "reasons": list(doc_risk.reasons),
            }
            if doc_risk is not None
            else None
        )
        await deps.doc_repo.save_document(
            org_id,
            replace(
                doc,
                integrity={"verdict": verdict, "findingIds": [f.finding_id for f in live]},
                risk=risk_dict,
            ),
        )
        codes = sorted({f.code for f in fresh})
        return {
            **node_input,
            "verdict": verdict,
            "summary": f"{verdict}: {len(fresh)} finding(s)"
            + (f" ({', '.join(codes)})" if codes else ""),
        }

    return _node


async def _check_context(deps: PipelineDeps, org_id: str, doc: Any) -> CheckContext:
    assert deps.forensics is not None
    pdf = None
    if deps.storage is not None:
        cached = await deps.storage.get_cached(org_id, _pdf_key(doc.sha256))
        pdf = PdfInfo.from_dict(json.loads(cached)) if cached else None
    meta = doc.statement_meta or {}
    minor = lambda v: None if v is None else Decimal(v) / 100  # noqa: E731
    accounts: list[DeclaredAccount] = []
    if deps.workspaces is not None:
        accounts = [
            DeclaredAccount(a.bank_name, a.account_masked, a.holder_name)
            for a in await deps.workspaces.list_bank_accounts(org_id)
        ]
    return CheckContext(
        doc=doc,
        policy=deps.forensics,
        pdf=pdf,
        lines=await deps.bank_lines.list_lines(org_id, doc_id=doc.doc_id, limit=5000)
        if deps.bank_lines and doc.doc_type == DocType.BANK_STATEMENT
        else [],
        opening=minor(meta.get("openingMinor")),
        closing=minor(meta.get("closingMinor")),
        invoices=await deps.invoices.list_records(org_id, doc_id=doc.doc_id)
        if deps.invoices
        else [],
        receipts=await deps.receipts.list_records(org_id, doc_id=doc.doc_id)
        if deps.receipts
        else [],
        own_names=[n for n in await _own_names(deps, org_id) if n],
        accounts=accounts,
    )


def detect_content_duplicates(deps: PipelineDeps):
    """D02–D05 (docs/08 §2.2): the same statement period, invoice or receipt in another file. The
    newer document is held, its values not counted until a person decides (AC-006-5)."""

    @stage(deps, "detect_content_duplicates")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id, doc_id = _ids(node_input)
        doc = await deps.doc_repo.get_document(org_id, doc_id)
        if doc is None or deps.forensics is None or deps.findings is None:
            return {**node_input, "summary": "Duplicate detection skipped"}
        if doc.duplicate is not None and doc.duplicate.kind == DuplicateKind.EXACT:
            return {**node_input, "summary": "Exact copy: not read"}
        others, _ = await deps.doc_repo.list_documents(org_id, limit=500)
        others = [o for o in others if o.doc_id != doc_id and not _exact_copy(o)]
        match = await _find_duplicate(deps, org_id, doc, others)
        findings = [_duplicate_finding(doc, match)] if match else []
        await deps.findings.replace_document_findings(
            org_id, doc_id, findings, run_id=node_input.get("runId"), categories={"DUPLICATE"}
        )
        decided = doc.duplicate is not None and doc.duplicate.decision != DuplicateDecision.PENDING
        if not decided:
            hold = match is not None and match.hold
            info = (
                DuplicateInfo(
                    DuplicateKind.CONTENT, match.code, match.of_doc_id, DuplicateDecision.PENDING
                )
                if match is not None and match.hold
                else None
            )
            if hold != doc.held_as_duplicate or info != doc.duplicate:
                await deps.doc_repo.save_document(
                    org_id, replace(doc, duplicate=info, held_as_duplicate=hold)
                )
                for store in (deps.bank_lines, deps.invoices, deps.receipts):
                    if store is not None:
                        await store.set_held(org_id, doc_id, hold)
        summary = f"{match.code} of {match.of_doc_id}" if match else "No duplicates detected"
        return {**node_input, "summary": summary}

    return _node


def _exact_copy(doc: Any) -> bool:
    return doc.duplicate is not None and doc.duplicate.kind == DuplicateKind.EXACT


async def _find_duplicate(
    deps: PipelineDeps, org_id: str, doc: Any, others: list[Any]
) -> Match | None:
    assert deps.forensics is not None
    policy = deps.forensics.duplicates
    uploaded = {o.doc_id: o.uploaded_at for o in [doc, *others]}
    if doc.doc_type == DocType.BANK_STATEMENT and deps.bank_lines is not None:
        keys = []
        for d in [doc, *[o for o in others if o.doc_type == DocType.BANK_STATEMENT]]:
            if key := await _statement_key(deps, org_id, d):
                keys.append(key)
        mine = next((k for k in keys if k.doc_id == doc.doc_id), None)
        return statement_duplicate(mine, keys, policy) if mine else None
    if doc.doc_type in (DocType.SALES_INVOICE, DocType.PURCHASE_INVOICE) and deps.invoices:
        everything = await deps.invoices.list_records(org_id, limit=1000)
        keys = [
            InvoiceKey(
                i.doc_id,
                uploaded[i.doc_id],
                i.issuer_name,
                i.number,
                i.issue_date,
                i.total,
                i.pay_to_masked,
            )
            for i in everything
            if i.doc_id in uploaded
        ]
        for mine in [k for k in keys if k.doc_id == doc.doc_id]:
            if match := invoice_duplicate(mine, keys, policy):
                return match
        return None
    if doc.doc_type == DocType.RECEIPT and deps.receipts:
        hashes = {o.doc_id: o.p_hash for o in [doc, *others]}
        everything = await deps.receipts.list_records(org_id, limit=1000)
        keys = [
            ReceiptKey(
                r.doc_id, uploaded[r.doc_id], r.merchant_name, r.date, r.total, hashes.get(r.doc_id)
            )
            for r in everything
            if r.doc_id in uploaded
        ]
        for mine in [k for k in keys if k.doc_id == doc.doc_id]:
            if match := receipt_duplicate(mine, keys, policy):
                return match
    return None


async def _statement_key(deps: PipelineDeps, org_id: str, doc: Any) -> StatementKey | None:
    meta = doc.statement_meta or {}
    if not (meta.get("periodStart") and meta.get("periodEnd") and deps.bank_lines):
        return None
    lines = await deps.bank_lines.list_lines(org_id, doc_id=doc.doc_id, limit=5000)
    return StatementKey(
        doc_id=doc.doc_id,
        uploaded_at=doc.uploaded_at,
        bank=meta.get("bankName"),
        last4=(meta.get("accountMasked") or "")[-4:] or None,
        start=date.fromisoformat(meta["periodStart"]),
        end=date.fromisoformat(meta["periodEnd"]),
        rows=frozenset((ln.date, ln.amount, ln.balance) for ln in lines),
    )


_DUPLICATE_TITLES = {
    "D02_STATEMENT_PERIOD_DUPLICATE": "This statement covers days another statement already covers",
    "D03_INVOICE_DUPLICATE": "This invoice was already uploaded",
    "D04_INVOICE_NUMBER_REUSED": "Another invoice from this issuer has the same number",
    "D05_RECEIPT_DUPLICATE": "This receipt was already uploaded",
}


_PAID_ELSEWHERE = "This invoice was already uploaded, with another account to pay into"


def _duplicate_finding(doc: Any, match: Match) -> Finding:
    elsewhere = match.code == "D03_INVOICE_DUPLICATE" and "payTo" in match.facts
    return Finding(
        finding_id=finding_id(match.code, f"{doc.doc_id}|{match.of_doc_id}"),
        code=match.code,
        category="DUPLICATE",
        severity=match.severity,
        title=_PAID_ELSEWHERE if elsewhere else _DUPLICATE_TITLES[match.code],
        facts={
            **match.facts,
            "otherDocument": match.of_doc_id,
            "held": "yes" if match.hold else "no",
        },
        evidence=[
            Evidence(doc_id=doc.doc_id, page=1, label="This document"),
            Evidence(doc_id=match.of_doc_id, page=1, label="Earlier document"),
        ],
        doc_id=doc.doc_id,
        month=doc.months[0] if doc.months else None,
    )


_CATEGORIZE_BATCH = 100


# Every bank line gets a category (docs/08 §4.1): keyword rules first, the model for the rest in
# batches of 100 (cached), unsure answers stay UNKNOWN; the cash-flow class follows from the
# workspace's accounting framework, never from the model.
def categorize_bank_lines(deps: PipelineDeps):

    @stage(deps, "categorize_bank_lines")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id, doc_id = _ids(node_input)
        doc = await deps.doc_repo.get_document(org_id, doc_id)
        policy = deps.categories
        if doc is None or doc.doc_type != DocType.BANK_STATEMENT or policy is None:
            return {**node_input, "summary": "Nothing to categorize"}
        if deps.bank_lines is None:
            return {**node_input, "summary": "Categorization skipped"}
        lines = await deps.bank_lines.list_lines(org_id, doc_id=doc_id, limit=5000)
        framework = await _framework(deps, org_id)
        decided: dict[str, Categorized] = {}
        left: list[tuple[BankLine, list[str]]] = []
        for line in lines:
            if line.categorized_by == "USER":
                continue
            rule, tags = by_rules(line.description, line.counterparty_name, line.amount, policy)
            if rule is not None:
                decided[line.tx_id] = rule
            else:
                left.append((line, tags))
        tokens = [0, 0]
        if left and deps.reader is not None and deps.storage is not None:
            for start in range(0, len(left), _CATEGORIZE_BATCH):
                batch = left[start : start + _CATEGORIZE_BATCH]
                answers = await _model_categories(deps, org_id, batch, policy, tokens)
                for i, (line, tags) in enumerate(batch):
                    category, confidence, name = answers.get(i, (None, None, None))
                    decided[line.tx_id] = from_model(
                        category, confidence, line.amount, tags, policy
                    )
                    if name and not line.counterparty_name:
                        line.counterparty_name = name
        else:
            for line, tags in left:
                decided[line.tx_id] = from_model(None, None, line.amount, tags, policy)
        for line in lines:
            if (c := decided.get(line.tx_id)) is None:
                continue
            line.category, line.categorized_by = c.category, c.categorized_by
            line.category_confidence, line.risk_tags = c.confidence, c.risk_tags
            line.cashflow_class = policy.categories[c.category].cashflow_class(framework)
        await deps.bank_lines.replace_document_lines(org_id, doc_id, lines)
        by = Counter(line.categorized_by for line in lines)
        asked = deps.reader is not None and tokens[0] > 0  # cache hits call no model
        return {
            **node_input,
            **({"model": deps.reader.version("categorize")[0]} if asked and deps.reader else {}),
            "tokens_in": tokens[0],
            "tokens_out": tokens[1],
            "summary": ", ".join(f"{n} by {k.lower()}" for k, n in sorted(by.items())),
        }

    return _node


async def _framework(deps: PipelineDeps, org_id: str) -> Framework:
    workspace = await deps.workspaces.get_workspace(org_id) if deps.workspaces else None
    framework = workspace.profile.accounting_framework if workspace else "IFRS"
    return "US_GAAP" if framework == "US_GAAP" else "IFRS"


def _vocabulary(policy: CategoryPolicy) -> str:
    way = {"in": "money in", "out": "money out", "either": "either"}
    return "\n".join(f"{c.id} ({way[c.direction]}): {c.label}" for c in policy.categories.values())


async def _model_categories(
    deps: PipelineDeps,
    org_id: str,
    batch: list[tuple[BankLine, list[str]]],
    policy: CategoryPolicy,
    tokens: list[int],
) -> dict[int, tuple[str | None, float | None, str | None]]:
    """The model's answers for one batch, cached by the batch's content, model and prompt."""
    assert deps.reader is not None and deps.storage is not None
    items = [
        TransactionItem(
            id=i,
            description=" ".join(line.description.split()),
            direction="in" if line.amount > 0 else "out",
            amount=f"{abs(line.amount):.2f}",
        )
        for i, (line, _) in enumerate(batch)
    ]
    model, prompt_version = deps.reader.version("categorize")
    payload = json.dumps([item.model_dump() for item in items], sort_keys=True)
    key = f"categories/{hashlib.sha256(payload.encode()).hexdigest()}/{model}-{prompt_version}.json"
    cached = await deps.storage.get_cached(org_id, key)
    if cached is not None:
        result = CategorizeResult.model_validate_json(cached)
    else:
        call = await deps.reader.categorize(items, _vocabulary(policy))
        result = call.value
        tokens[0] += call.tokens_in
        tokens[1] += call.tokens_out
        await deps.storage.put_cached(org_id, key, result.model_dump_json().encode())
    return {c.id: (c.category, c.confidence, c.counterparty_name) for c in result.items}


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
