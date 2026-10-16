"""Document workflow node factories with stubs for specs 004-008 (docs/06 §2, §4)."""

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from pathlib import PurePosixPath
from typing import Any

import structlog
from google.adk import Context
from pydantic import BaseModel

from app.agents.deps import PipelineDeps
from app.agents.labels import (
    decision,
    extraction_path,
    page_image,
    verified_examples,
    write_labels,
)
from app.agents.stages import stage
from app.domain.accounts import account_hash, mask_numbers_in_text
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
from app.domain.counterparties import fold_name
from app.domain.duplicates import (
    InvoiceKey,
    LedgerCopy,
    Match,
    ReceiptKey,
    StatementKey,
    invoice_duplicate,
    ledger_entry_duplicates,
    receipt_duplicate,
    statement_duplicate,
)
from app.domain.findings import Evidence, Finding, finding_id
from app.domain.invoice_records import build_invoices, build_receipts, document_type_of
from app.domain.label_sync import (
    ReadRecord,
    document_records,
    line_records,
    value_labels,
)
from app.domain.labels import LabelSubject, propose
from app.domain.layout import Chunk, chunk_page, chunks_from_json, chunks_to_json, render_chunks
from app.domain.ledger_parse import (
    LedgerMapping,
    compute_layout_signature,
    is_auto_confirmable,
    mask_value_shapes,
    merge_model_proposal,
    parse_ledger_content,
    propose_mapping,
    read_table,
)
from app.domain.models.bank_line import BankLine
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
from app.domain.page_triage import TextLayerStatus, WitnessType
from app.domain.profile_suggestions import StatementFacts, build_profile_suggestions
from app.domain.profit_loss import LedgerRow
from app.domain.reading import (
    CategorizeResult,
    InvoicePageReading,
    ReceiptPageReading,
    StatementPageReading,
    TransactionItem,
    build_statement,
)
from app.domain.review_items import confirm_mapping_item, confirm_type_item
from app.domain.risk import assess_document_risk
from app.domain.verdict import integrity_verdict
from app.domain.verify import Word
from app.services.extraction_service import ExtractionPorts, build_extraction

log = structlog.get_logger()


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
        if doc.type_set_by:
            return _type_chosen(node_input, doc)
        image = await deps.storage.get_page_image(org_id, doc_id, 1)
        if image is None:
            return await _classify_without_reader(deps, node_input)
        chunks = await _load_chunks(deps, org_id, doc.sha256, 1)
        page_text = mask_numbers_in_text(" ".join(c.text for c in chunks))[:1000]
        examples = await verified_examples(deps, org_id, "DOC_TYPE", [page_text])
        call = await deps.reader.classify(image, render_chunks(chunks), examples or None)
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
        if not confident:
            await _ask_for_type(deps, updated, result.doc_type, result.confidence, node_input)
        if deps.learning is not None:
            model, prompt_version = deps.reader.version("classify")
            await write_labels(
                deps,
                org_id,
                [
                    propose(
                        "DOC_TYPE",
                        LabelSubject(display=doc.file_name, doc_id=doc_id, page_no=1),
                        decision(
                            result.doc_type,
                            source="MODEL",
                            at=deps.clock.now(),
                            confidence=result.confidence,
                            model=model,
                            prompt_version=prompt_version,
                            run_id=node_input.get("runId"),
                        ),
                        policy=deps.learning,
                        page_image_url=page_image(doc_id, 1),
                        example_text=page_text or None,
                    )
                ],
            )
        return {
            **node_input,
            "docType": result.doc_type,
            "typeConfidence": result.confidence,
            "currency": result.currency,
            "status": updated.status.value,
            "model": call.model,
            "prompt_version": call.prompt_version,
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
    doc = await deps.doc_repo.get_document(org_id, doc_id)
    if doc is not None and doc.type_set_by:
        return _type_chosen(node_input, doc)
    if doc_type == DocType.UNKNOWN.value or conf < _MIN_TYPE_CONFIDENCE:
        if doc is not None:
            updated = replace(doc, status=DocStatus.NEEDS_INPUT, status_detail="E03_UNCERTAIN_TYPE")
            await deps.doc_repo.save_document(org_id, updated)
            guess = "" if doc_type == DocType.UNKNOWN.value else doc_type
            await _ask_for_type(deps, updated, guess, conf, node_input)
        return {**node_input, "status": "NEEDS_INPUT", "summary": "Type confirmation needed"}
    return {**node_input, "docType": doc_type, "summary": "Classified document"}


def _type_chosen(node_input: dict[str, Any], doc: Document) -> dict[str, Any]:
    """A person chose the type (AC-005-2): the classifier never overrides it."""
    return {
        **node_input,
        "docType": doc.doc_type.value,
        "typeConfidence": 1.0,
        "summary": f"{doc.doc_type.value} (chosen by a person)",
    }


async def _ask_for_type(
    deps: PipelineDeps, doc: Document, guess: str, confidence: float, node_input: dict[str, Any]
) -> None:
    """E03 as a finding and the CONFIRM_TYPE item that resolves it (AC-005-2, AC-006-9)."""
    org_id = node_input["orgId"]
    shown = f"{confidence:.2f}"
    if deps.findings is not None:
        finding = Finding(
            finding_id=finding_id("E03_UNCERTAIN_TYPE", doc.doc_id),
            code="E03_UNCERTAIN_TYPE",
            category="EXTRACTION",
            severity="LOW",
            title="Kredibel is not sure what kind of document this is",
            facts={"docType": guess, "confidence": shown},
            evidence=[Evidence(doc_id=doc.doc_id, page=1, label="Page 1")],
            scope="DOCUMENT",
            doc_id=doc.doc_id,
        )
        await deps.findings.replace_document_findings(
            org_id,
            doc.doc_id,
            [finding],
            run_id=str(node_input.get("runId") or "") or None,
            categories={"EXTRACTION"},
        )
    if deps.review_items is not None:
        await deps.review_items.upsert_review_item(
            org_id, confirm_type_item(doc.doc_id, doc.file_name, guess=guess, confidence=shown)
        )


def propose_ledger_mapping(deps: PipelineDeps):
    """AC-005-11: reuse a confirmed mapping, confirm a standard layout by code, or propose and
    wait for a person (NEEDS_INPUT with a CONFIRM_LEDGER_MAPPING item)."""

    @stage(deps, "propose_ledger_mapping")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        if node_input.get("mappingConfirmed") and node_input.get("mapping"):
            return {**node_input, "summary": "Ledger mapping confirmed"}

        org_id, doc_id = _ids(node_input)
        doc = await deps.doc_repo.get_document(org_id, doc_id)
        if doc is None or deps.storage is None:
            return {**node_input, "summary": "Ledger mapping skipped"}

        ext = PurePosixPath(doc.gcs_path).suffix if doc.gcs_path else ".csv"
        content_bytes = await deps.storage.get_original(org_id, doc_id, ext)
        if not content_bytes:
            return {**node_input, "summary": "Empty ledger content"}
        headers, rows = read_table(content_bytes.decode("utf-8", errors="replace"))
        if not headers or not rows:
            return {**node_input, "summary": "Empty ledger rows"}
        signature = compute_layout_signature(headers)
        meta = dict(doc.ledger_meta or {})

        # 1. A mapping a person confirmed for this layout, on the workspace or on this document.
        confirmed: dict[str, Any] | None = None
        if deps.workspaces is not None:
            workspace = await deps.workspaces.get_workspace(org_id)
            confirmed = (workspace.ledger_mappings if workspace else {}).get(signature)
        if (
            confirmed is None
            and meta.get("mappingStatus") == "CONFIRMED"
            and meta.get("layoutSignature") == signature
        ):
            confirmed = meta.get("mapping")
        if confirmed:
            mapping = LedgerMapping.from_dict(confirmed)
            if mapping.complete:
                meta.update(
                    {
                        "layoutSignature": signature,
                        "mappingStatus": "CONFIRMED",
                        "mapping": mapping.to_dict(),
                    }
                )
                await deps.doc_repo.save_document(org_id, replace(doc, ledger_meta=meta))
                return {
                    **node_input,
                    "mappingConfirmed": True,
                    "mapping": mapping.to_dict(),
                    "summary": "Confirmed ledger mapping reused",
                }

        # 2. Code proposes from the header words and the value shapes, never from the values.
        proposal = propose_mapping(headers, rows)
        model_call: dict[str, Any] = {}
        if not proposal.complete and deps.reader is not None:
            # The model fills the columns code's synonyms missed, from the header and the value
            # shapes only; code checks every answer against the header (AC-005-11).
            try:
                call = await deps.reader.map_ledger_columns(
                    headers, [mask_value_shapes(r) for r in rows[:5]]
                )
                proposal = merge_model_proposal(proposal, call.value, headers)
                model_call = {
                    "model": call.model,
                    "prompt_version": call.prompt_version,
                    "tokens_in": call.tokens_in,
                    "tokens_out": call.tokens_out,
                }
            except Exception as exc:  # a person maps the columns either way
                model_call = {"mapperError": str(exc)[:200]}
        if is_auto_confirmable(proposal, headers):
            meta.update(
                {
                    "layoutSignature": signature,
                    "mappingStatus": "CONFIRMED",
                    "mapping": proposal.to_dict(),
                }
            )
            await deps.doc_repo.save_document(org_id, replace(doc, ledger_meta=meta))
            return {
                **node_input,
                "mappingConfirmed": True,
                "mapping": proposal.to_dict(),
                "summary": "Standard ledger layout auto-confirmed",
            }

        # 3. A new layout: a person checks which column is which, once.
        meta.update(
            {
                "layoutSignature": signature,
                "mappingStatus": "PROPOSED",
                "mapping": proposal.to_dict(),
                "header": headers,
                "sampleRows": rows[:5],
            }
        )
        updated = replace(
            doc,
            status=DocStatus.NEEDS_INPUT,
            status_detail="Ledger mapping confirmation needed",
            ledger_meta=meta,
        )
        await deps.doc_repo.save_document(org_id, updated)
        if deps.review_items is not None:
            item = confirm_mapping_item(
                doc_id,
                doc.file_name,
                mapping=proposal.to_dict(),
                header=headers,
                sample_rows=rows[:5],
                layout_signature=signature,
            )
            await deps.review_items.upsert_review_item(org_id, item)
        return {
            **node_input,
            **model_call,
            "status": "NEEDS_INPUT",
            "summary": "Mapping confirmation needed",
        }

    return _node


def _hold_ledger_copies(
    fresh: list[LedgerRow], stored: list[LedgerRow], doc_id: str
) -> tuple[list[LedgerRow], list[LedgerCopy]]:
    """D06: the file's rows that repeat an earlier entry (in this file or one stored before) are
    held pending a decision; a decision already taken on the same entry (a re-read) is kept."""
    decided = {
        r.entry_id: (r.duplicate or {}).get("decision")
        for r in stored
        if r.doc_id == doc_id and (r.duplicate or {}).get("decision") in ("CONFIRMED", "REJECTED")
    }
    others = [r for r in stored if r.doc_id != doc_id]
    order = {r.doc_id: 0 for r in others}
    order[doc_id] = 1  # whatever was stored before came first
    copies = [
        c for c in ledger_entry_duplicates([*others, *fresh], doc_order=order) if c.doc_id == doc_id
    ]
    by_id = {c.entry_id: c for c in copies}
    rows: list[LedgerRow] = []
    for r in fresh:
        c = by_id.get(r.entry_id)
        if c is None:
            rows.append(r)
            continue
        decision = decided.get(r.entry_id) or "PENDING"
        rows.append(
            r.model_copy(
                update={
                    "held_as_duplicate": decision != "REJECTED",
                    "duplicate": {
                        "code": "D06_LEDGER_ENTRY_DUPLICATE",
                        "ofEntryId": c.of_entry_id,
                        "ofDocId": c.of_doc_id,
                        "decision": decision,
                    },
                }
            )
        )
    return rows, copies


def _ledger_copy_findings(
    doc_id: str, copies: list[LedgerCopy], rows: list[LedgerRow]
) -> list[Finding]:
    by_id = {r.entry_id: r for r in rows}
    out: list[Finding] = []
    for c in copies:
        row = by_id[c.entry_id]
        out.append(
            Finding(
                finding_id=finding_id("D06_LEDGER_ENTRY_DUPLICATE", f"{doc_id}|{c.entry_id}"),
                code="D06_LEDGER_ENTRY_DUPLICATE",
                category="DUPLICATE",
                severity="MEDIUM",
                title="This ledger entry appears twice",
                facts={
                    "date": row.date.isoformat(),
                    "accountCode": row.account_code,
                    "reference": row.journal_id or "",
                    "amount": f"{row.debit - row.credit:.2f}",
                    "entryId": c.entry_id,
                    "ofEntryId": c.of_entry_id,
                },
                evidence=[
                    Evidence(doc_id=doc_id, ledger_entry_id=c.entry_id, label="This entry"),
                    Evidence(
                        doc_id=c.of_doc_id, ledger_entry_id=c.of_entry_id, label="Earlier entry"
                    ),
                ],
                scope="DOCUMENT",
                doc_id=doc_id,
                month=f"{row.date:%Y-%m}",
            )
        )
    return out


def parse_ledger(deps: PipelineDeps):
    """AC-005-12: every row becomes a ledger entry through the mapping; more than 2% bad rows
    reopen the mapping item."""

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

                    mapping = (
                        LedgerMapping.from_dict(node_input["mapping"])
                        if node_input.get("mapping")
                        else None
                    )
                    res = parse_ledger_content(
                        text, doc_id=doc_id, currency=currency, mapping=mapping
                    )
                    meta = dict(doc.ledger_meta or {})
                    if res.too_many_bad_rows:
                        msg = f"Over 2% invalid rows ({len(res.bad_rows)} bad rows)"
                        meta.update(
                            {
                                "mappingStatus": "PROPOSED",
                                "rowErrors": [
                                    {"row": r, "reason": "could not be read"}
                                    for r in res.bad_rows[:100]
                                ],
                            }
                        )
                        updated = replace(
                            doc, status=DocStatus.NEEDS_INPUT, status_detail=msg, ledger_meta=meta
                        )
                        await deps.doc_repo.save_document(org_id, updated)
                        if deps.review_items is not None and mapping is not None:
                            headers, rows = read_table(text)
                            item = confirm_mapping_item(
                                doc_id,
                                doc.file_name,
                                mapping=mapping.to_dict(),
                                header=headers,
                                sample_rows=rows[:5],
                                bad_rows=res.bad_rows,
                                layout_signature=res.layout_signature,
                            )
                            await deps.review_items.upsert_review_item(org_id, item)
                        return {
                            **node_input,
                            "status": "NEEDS_INPUT",
                            "summary": "Excessive bad rows in ledger",
                        }

                    if res.rows:
                        rows, copies = _hold_ledger_copies(
                            res.rows, await deps.ledger.list_rows(org_id), doc_id
                        )
                        res.rows[:] = rows
                        await deps.ledger.save_rows(org_id, rows)
                        if deps.findings is not None:
                            await deps.findings.replace_document_findings(
                                org_id,
                                doc_id,
                                _ledger_copy_findings(doc_id, copies, rows),
                                run_id=str(node_input.get("runId") or "") or None,
                                categories={"DUPLICATE"},
                            )
                        months = sorted({r.date.strftime("%Y-%m") for r in res.rows})
                        meta.update(
                            {
                                "rowsImported": len(res.rows),
                                "rows": len(res.rows),
                                "dateFrom": min(r.date for r in res.rows).isoformat(),
                                "dateTo": max(r.date for r in res.rows).isoformat(),
                                "badRowsCount": len(res.bad_rows),
                                "layoutSignature": res.layout_signature,
                                "mappingStatus": "CONFIRMED",
                            }
                        )
                        if mapping is not None:
                            meta["mapping"] = mapping.to_dict()
                        updated = replace(doc, months=months, ledger_meta=meta)
                        await deps.doc_repo.save_document(org_id, updated)
                        return {
                            **node_input,
                            "months": months,
                            "ledgerMeta": meta,
                            "summary": f"Ledger parsed: {len(res.rows)} entries",
                        }
        return {**node_input, "summary": "Ledger parsed"}

    return _node


def parse_pages(deps: PipelineDeps):
    # Parse: each page into layout chunks, cached by the file's SHA-256 (ADR-023): from the PDF's
    # own text layer, else from Document AI OCR of the page image (spec 022 phase B), the witness
    # of scans and photos.

    @stage(deps, "parse_pages")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id, doc_id = _ids(node_input)
        doc = await deps.doc_repo.get_document(org_id, doc_id)
        if doc is None or deps.storage is None:
            return {**node_input, "summary": "Parsing skipped"}
        extension = PurePosixPath(doc.gcs_path).suffix
        original = await deps.storage.get_original(org_id, doc_id, extension)
        usable = {p.page_no for p in doc.pages if p.text_layer == TextLayerStatus.USABLE}
        counts: dict[str, int] = {}
        if original and original.startswith(b"%PDF") and deps.page_text is not None:
            for page_no, words in deps.page_text.words(original).items():
                if page_no not in usable:
                    continue
                await _cache_chunks(deps, org_id, doc.sha256, page_no, words, counts)
        ocr_pages: list[int] = []
        if deps.ocr is not None:
            for page in doc.pages:
                if page.blank or str(page.page_no) in counts:
                    continue
                words = await _ocr_words(deps, org_id, doc_id, page)
                if words is None:
                    continue
                await _cache_chunks(deps, org_id, doc.sha256, page.page_no, words, counts)
                ocr_pages.append(page.page_no)
        if ocr_pages:
            pages = [
                replace(p, witness=WitnessType.OCR) if p.page_no in ocr_pages else p
                for p in doc.pages
            ]
            await deps.doc_repo.save_document(org_id, replace(doc, pages=pages))
        summary = f"{sum(counts.values())} chunks on {len(counts)} pages"
        if ocr_pages:
            summary += f", {len(ocr_pages)} by OCR"
        elif not counts:
            summary = "No text layer and no OCR"
        return {**node_input, "parsed": counts, "ocrPages": ocr_pages, "summary": summary}

    return _node


async def _cache_chunks(
    deps: PipelineDeps,
    org_id: str,
    sha256: str,
    page_no: int,
    words: list[Word],
    counts: dict[str, int],
) -> None:
    assert deps.storage is not None
    chunks = chunk_page(words, page=page_no)
    key = _chunks_key(sha256, page_no)
    await deps.storage.put_cached(org_id, key, json.dumps(chunks_to_json(chunks)).encode())
    counts[str(page_no)] = len(chunks)


async def _ocr_words(
    deps: PipelineDeps, org_id: str, doc_id: str, page: PageRecord
) -> list[Word] | None:
    """A page image's OCR words, cached by the image's hash and the OCR version (docs/07 §8); a
    failure leaves the page without a witness rather than failing the document."""
    if deps.ocr is None or deps.storage is None:
        return None
    key = f"{page.sha256}/ocr-{deps.ocr.version}.json"
    cached = await deps.storage.get_cached(org_id, key)
    if cached is not None:
        return [Word(*w) for w in json.loads(cached)]
    image = await deps.storage.get_page_image(org_id, doc_id, page.page_no)
    if not image:
        return None
    try:
        words = await deps.ocr.words(image)
    except Exception:  # noqa: BLE001 - the reading goes on with one source (E01)
        log.warning("ocr_failed", doc_id=doc_id, page=page.page_no)
        return None
    await deps.storage.put_cached(org_id, key, json.dumps([list(w) for w in words]).encode())
    return words


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
        page_type = getattr(reading, "page_type", None)
        if page_type and deps.learning is not None:
            confidence = getattr(reading, "page_type_confidence", None)
            await write_labels(
                deps,
                org_id,
                [
                    propose(
                        "PAGE_TYPE",
                        LabelSubject(
                            display=f"{doc.file_name}, page {page_no}",
                            doc_id=doc_id,
                            page_no=page_no,
                        ),
                        decision(
                            page_type,
                            source="MODEL",
                            at=deps.clock.now(),
                            confidence=confidence,
                            model=model,
                            prompt_version=prompt_version,
                            run_id=node_input.get("runId"),
                        ),
                        policy=deps.learning,
                        page_image_url=page_image(doc_id, page_no),
                        extraction_url=extraction_path(doc_id, page_no),
                    )
                ],
            )
        return {
            **base,
            "reading": reading.model_dump(mode="json"),
            "header_context": header,
            "model": model,
            "prompt_version": prompt_version,
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
                "method": _reading_method(doc, chunks),
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
        if outcome.statement_meta and outcome.account_hash:
            await _suggest_account(deps, org_id, updated.doc_id, outcome)
        records = await _read_records(deps, org_id, updated, task)
        page_types = {
            r.page: (r.page_type, getattr(r, "page_type_confidence", None))
            for r in readings
            if getattr(r, "page_type", None)
        }
        # Spec 022: the page's chunks and Markdown, from what was just stored.
        ports = extraction_ports(deps)
        if ports is not None:
            await build_extraction(
                ports,
                org_id,
                updated,
                page_types=page_types,
                page_agreement=outcome.page_agreement,
            )
        await _value_labels(deps, org_id, updated, records, model, prompt_version, node_input)
        return {
            **doc_data,
            "months": outcome.months,
            "agreement": outcome.agreement,
            "summary": f"{outcome.records} {outcome.noun}, agreement {outcome.agreement:.3f}",
        }

    return _node


def _first_line(text: str | None) -> str:
    return text.splitlines()[0] if text else ""


async def _read_records(
    deps: PipelineDeps, org_id: str, doc: Document, task: str
) -> list[ReadRecord]:
    if task == "statement_page" and deps.bank_lines is not None:
        return line_records(await deps.bank_lines.list_lines(org_id, doc_id=doc.doc_id, limit=5000))
    if task == "invoice_page" and deps.invoices is not None:
        return document_records(
            "Invoice", await deps.invoices.list_records(org_id, doc_id=doc.doc_id)
        )
    if task == "receipt_page" and deps.receipts is not None:
        return document_records(
            "Receipt", await deps.receipts.list_records(org_id, doc_id=doc.doc_id)
        )
    return []


def _reading(info: dict[str, Any], source: str) -> str | None:
    """One source's reading of a value from its consensus ("GEMINI" or "TEXT_LAYER")."""
    raw = info.get("raw")
    value = raw.get(source) if isinstance(raw, dict) else None
    return str(value) if value is not None else None


async def _value_labels(
    deps: PipelineDeps,
    org_id: str,
    doc: Document,
    records: list[ReadRecord],
    model: str,
    prompt_version: str,
    node_input: dict[str, Any],
) -> None:
    if deps.learning is None or deps.labels is None:
        return
    at = deps.clock.now()
    run_id = node_input.get("runId")
    labels = value_labels(
        doc.doc_id,
        doc.file_name,
        records,
        decision=lambda value: decision(
            value, source="MODEL", at=at, model=model, prompt_version=prompt_version, run_id=run_id
        ),
        policy=deps.learning,
    )
    await write_labels(deps, org_id, labels)


def _reading_method(doc: Document, chunks: dict[int, list[Chunk]]) -> str:
    """docs/07 §8: which witness the readings were checked against."""
    witnessed = [p for p in doc.pages if chunks.get(p.page_no)]
    if not witnessed:
        return "AI_ONLY"
    ocr = sum(1 for p in witnessed if p.witness == WitnessType.OCR)
    return "AI_OCR" if ocr == len(witnessed) else "AI_MIXED" if ocr else "AI_TEXT_LAYER"


def extraction_ports(deps: PipelineDeps) -> ExtractionPorts | None:
    return (
        None
        if deps.storage is None
        else ExtractionPorts(
            storage=deps.storage,
            page_text=deps.page_text,
            chunks=deps.chunks,
            bank_lines=deps.bank_lines,
            invoices=deps.invoices,
            receipts=deps.receipts,
            labels=deps.labels,
        )
    )


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
    account_hash: str | None = None  # keyed hash of the statement's account digits (spec 014)

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
        account_hash=account_hash(org_id, meta.account_digits) if meta.account_digits else None,
        statement_meta={
            "bankName": meta.bank_name,
            "accountHolder": meta.account_holder,
            "accountMasked": meta.account_masked,
            "holderAddress": meta.holder_address,
            "currency": meta.currency,
            "periodStart": meta.period_start.isoformat() if meta.period_start else None,
            "periodEnd": meta.period_end.isoformat() if meta.period_end else None,
            "openingMinor": _minor(meta.opening),
            "closingMinor": _minor(meta.closing),
        },
    )


async def _suggest_account(
    deps: PipelineDeps, org_id: str, doc_id: str, outcome: "_Verified"
) -> None:
    """A statement account the workspace has not declared becomes a suggestion (spec 014); the
    digits' keyed hash travels with it to orgPrivate, never the digits."""
    if deps.suggestions is None or deps.workspaces is None:
        return
    workspace = await deps.workspaces.get_workspace(org_id)
    if workspace is None:
        return
    meta = outcome.statement_meta or {}
    start = meta.get("periodStart")
    facts = StatementFacts(
        doc_id=doc_id,
        page=1,
        bank_name=meta.get("bankName"),
        account_masked=meta.get("accountMasked"),
        account_hash=outcome.account_hash,
        holder_name=meta.get("accountHolder"),
        holder_address=meta.get("holderAddress"),
        period_start=date.fromisoformat(start) if start else None,
        agreed=outcome.agreement >= 0.99,
    )
    rejected = {
        s.suggestion_id for s in await deps.suggestions.list_suggestions(org_id, status="REJECTED")
    }
    fresh = build_profile_suggestions(
        profile=workspace.profile,
        accounts=await deps.workspaces.list_bank_accounts(org_id),
        statements=[facts],
        invoices=[],
        own_names=[n for n in await _own_names(deps, org_id) if n],
        rejected=rejected,
    )
    await deps.suggestions.upsert_open(org_id, [s for s in fresh if s.field == "BANK_ACCOUNT"])


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
        # AC-016-7: what a person remembered for a party and direction decides before any rule.
        remembered = {
            (r.counterparty_key, r.direction): r
            for r in (await deps.labels.list_rules(org_id) if deps.labels is not None else [])
        }
        for line in lines:
            if line.categorized_by == "USER":
                continue
            way = "in" if line.amount > 0 else "out"
            party_key = line.counterparty_id or (
                fold_name(line.counterparty_name) if line.counterparty_name else ""
            )
            kept = remembered.get((party_key, way)) if party_key else None
            if kept is not None:
                decided[line.tx_id] = Categorized(kept.category, "RULE", None, [], kept.rule_id)
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
        if deps.learning is not None:
            version = deps.reader.version("categorize") if deps.reader else (None, None)
            at = deps.clock.now()
            labels = []
            for line in lines:
                c = decided.get(line.tx_id)
                if c is None or c.categorized_by == "NONE":
                    continue
                by_model = c.categorized_by == "MODEL"
                labels.append(
                    propose(
                        "CATEGORY",
                        LabelSubject(
                            display=line.description.splitlines()[0]
                            if line.description
                            else line.tx_id,
                            doc_id=doc_id,
                            page_no=line.page,
                            tx_id=line.tx_id,
                            counterparty_id=line.counterparty_id,
                        ),
                        decision(
                            c.category,
                            source="MODEL" if by_model else "RULE",
                            at=at,
                            confidence=c.confidence,
                            model=version[0] if by_model else None,
                            prompt_version=version[1] if by_model else None,
                            run_id=node_input.get("runId"),
                            rule_id=c.rule_id,
                        ),
                        policy=deps.learning,
                        month=line.month,
                        framework=framework,
                        cashflow_class=line.cashflow_class,
                        page_image_url=page_image(doc_id, line.page),
                        extraction_url=extraction_path(doc_id, line.page),
                        example_text=mask_numbers_in_text(_first_line(line.description)) or None,
                    )
                )
            await write_labels(deps, org_id, labels)
        by = Counter(line.categorized_by for line in lines)
        asked = deps.reader is not None and tokens[0] > 0  # cache hits call no model
        return {
            **node_input,
            **(
                {
                    "model": deps.reader.version("categorize")[0],
                    "prompt_version": deps.reader.version("categorize")[1],
                }
                if asked and deps.reader
                else {}
            ),
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
    texts = [mask_numbers_in_text(item.description) for item in items]
    examples = await verified_examples(deps, org_id, "CATEGORY", texts)
    # The examples shape the answer, so they are part of the cache key.
    payload = json.dumps([[item.model_dump() for item in items], examples], sort_keys=True)
    key = f"categories/{hashlib.sha256(payload.encode()).hexdigest()}/{model}-{prompt_version}.json"
    cached = await deps.storage.get_cached(org_id, key)
    if cached is not None:
        result = CategorizeResult.model_validate_json(cached)
    else:
        call = await deps.reader.categorize(items, _vocabulary(policy), examples or None)
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
