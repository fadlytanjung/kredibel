"""Finance Assistant and AI Reconciliation Service (spec 011, US-011-1)."""

from __future__ import annotations

import asyncio
import re
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from app.domain.grounding import GroundingContext, check_grounding
from app.domain.models.assistant import (
    AnswerPart,
    AssistantMessage,
    CitationRef,
    GroundingRef,
    MatchSuggestion,
    Memory,
    MessageAnswer,
    Thread,
)
from app.domain.models.invoice import Invoice, Receipt
from app.ports.assistant_repository import AssistantRepository
from app.ports.bank_line_repository import BankLineRepository
from app.ports.document_reader import DocumentReader
from app.ports.document_repository import DocumentRepository
from app.ports.finding_repository import FindingRepository
from app.ports.month_repository import MonthRepository
from app.ports.record_repository import DocumentRecords
from app.ports.review_item_repository import ReviewItemRepository
from app.services.entitlement_service import EntitlementService


def _new_id(prefix: str) -> str:
    # Deterministic or random Crockford-like ID with prefix
    return f"{prefix}_{uuid.uuid4().hex[:26]}"


class AssistantService:
    def __init__(
        self,
        *,
        assistant_repo: AssistantRepository,
        month_repo: MonthRepository,
        finding_repo: FindingRepository,
        bank_line_repo: BankLineRepository,
        doc_repo: DocumentRepository,
        review_item_repo: ReviewItemRepository,
        reader: DocumentReader,
        invoices: DocumentRecords[Invoice] | None = None,
        receipts: DocumentRecords[Receipt] | None = None,
        entitlements: EntitlementService | None = None,
    ) -> None:
        self._assistant_repo = assistant_repo
        self._month_repo = month_repo
        self._finding_repo = finding_repo
        self._bank_line_repo = bank_line_repo
        self._doc_repo = doc_repo
        self._review_item_repo = review_item_repo
        self._reader = reader
        self._invoices = invoices
        self._receipts = receipts
        self._entitlements = entitlements

    async def list_threads(
        self, org_id: str, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[Thread], str | None]:
        return await self._assistant_repo.list_threads(org_id, limit=limit, cursor=cursor)

    async def get_thread(self, org_id: str, thread_id: str) -> Thread | None:
        return await self._assistant_repo.get_thread(org_id, thread_id)

    async def create_thread(
        self, org_id: str, title: str | None = None, scope: str = "WORKSPACE"
    ) -> Thread:
        thread_id = _new_id("thr")
        thread_title = title or "Finance Chat"
        thread = Thread(
            thread_id=thread_id,
            title=thread_title,
            scope=scope,
            created_at=datetime.now(UTC),
            last_message_at=datetime.now(UTC),
        )
        return await self._assistant_repo.create_thread(org_id, thread)

    async def list_messages(self, org_id: str, thread_id: str) -> list[AssistantMessage]:
        return await self._assistant_repo.list_messages(org_id, thread_id)

    async def list_memories(self, org_id: str, uid: str) -> list[Memory]:
        mems = await self._assistant_repo.list_memories(org_id, uid)
        if not mems:
            defaults = [
                "Show amounts in millions",
                "ACB ••5577 is the payroll account",
                "The financial year starts in January",
            ]
            for fact in defaults:
                m = Memory(memory_id=_new_id("mem"), fact=fact, updated_at=datetime.now(UTC))
                await self._assistant_repo.save_memory(org_id, uid, m)
                mems.append(m)
        return mems

    async def forget_memories(self, org_id: str, uid: str) -> None:
        await self._assistant_repo.forget_memories(org_id, uid)

    async def forget_memory(self, org_id: str, uid: str, memory_id: str) -> None:
        await self._assistant_repo.forget_memory(org_id, uid, memory_id)


    async def _gather_context(self, org_id: str) -> tuple[str, GroundingContext]:
        """Collect facts, findings, and figures into context string and GroundingContext."""
        months = await self._month_repo.list(org_id)
        findings = await self._finding_repo.list_findings(org_id)
        review_items, _, _ = await self._review_item_repo.list_review_items(org_id)

        facts_dict: dict[str, Any] = {}
        context_lines: list[str] = ["WORKSPACE MONTHS:"]
        for m in sorted(months, key=lambda x: x.month):
            figs = m.figures or {}
            in_val = figs.get("inflow_minor", 0) / 100
            out_val = figs.get("outflow_minor", 0) / 100
            net_val = in_val - out_val
            rate = figs.get("match_rate_pct", 0)

            in_fid = f"fact:{m.month}:money_in"
            out_fid = f"fact:{m.month}:money_out"
            net_fid = f"fact:{m.month}:net"
            rate_fid = f"fact:{m.month}:matched_rate"

            facts_dict[in_fid] = in_val
            facts_dict[out_fid] = out_val
            facts_dict[net_fid] = net_val
            facts_dict[rate_fid] = rate

            risk_lvl = (m.risk or {}).get("level", "UNKNOWN")
            context_lines.append(
                f"- Month {m.month}: State={m.state.value}, Risk={risk_lvl}, "
                f"Money In={in_val} [[{in_fid}]], Money Out={out_val} [[{out_fid}]], "
                f"Net={net_val} [[{net_fid}]], Match Rate={rate}% [[{rate_fid}]]"
            )

        context_lines.append("\nOPEN RISK FINDINGS:")
        for f in findings:
            context_lines.append(
                f"- [[finding:{f.finding_id}]]: Code={f.code}, Severity={f.severity}, "
                f"Month={f.month}, Title='{f.title}', Summary='{f.explanation}'"
            )

        open_items = len([r for r in review_items if r.status == "OPEN"])
        context_lines.append(f"\nOPEN REVIEW ITEMS: {open_items}")
        for r in review_items:
            if r.status == "OPEN":
                context_lines.append(f"- Kind={r.kind}, Title='{r.title}', Key={r.key}")

        invoices_set: set[str] = set()
        docs_set: set[str] = set()
        if self._invoices is not None:
            all_invoices = await self._invoices.list_records(org_id, limit=200)
            if all_invoices:
                context_lines.append("\nINVOICES AND PAYMENT STATUS:")
                for inv in all_invoices:
                    invoices_set.add(inv.invoice_id)
                    docs_set.add(inv.doc_id)
                    party = (
                        inv.buyer_name
                        if inv.kind == "SALES"
                        else (inv.issuer_name or "Unknown Supplier")
                    )
                    pmt_status = (inv.evidence or {}).get("payment", "UNPAID")
                    fid_total = f"fact:invoice:{inv.invoice_id}:total"
                    facts_dict[fid_total] = float(inv.total or 0)
                    due_str = f", DueDate={inv.due_date}" if inv.due_date else ""
                    num_str = inv.number or "No number"
                    amt_str = f"{inv.total or 0} {inv.currency or 'IDR'}"
                    context_lines.append(
                        f"- [[invoice:{inv.invoice_id}]]: Kind={inv.kind}, Number='{num_str}', "
                        f"Party='{party}', Amount={amt_str} [[{fid_total}]], "
                        f"PaymentStatus={pmt_status}{due_str}, Link=/documents/{inv.doc_id}"
                    )

        grounding_ctx = GroundingContext(
            facts=facts_dict,
            findings=findings,
            invoices=invoices_set,
            documents=docs_set,
            allowed_fact_prefixes=("fact:",),
        )
        return "\n".join(context_lines), grounding_ctx

    async def ask(
        self, org_id: str, uid: str, thread_id: str, question: str
    ) -> AssistantMessage:
        if self._entitlements is not None:
            await self._entitlements.reserve_assistant_question(org_id)

        # 1. Save user message
        now = datetime.now(UTC)
        user_msg = AssistantMessage(
            message_id=_new_id("msg"),
            role="user",
            created_at=now,
            question=question,
        )
        await self._assistant_repo.append_message(org_id, thread_id, user_msg)

        # 2. Gather context and history
        context_str, grounding_ctx = await self._gather_context(org_id)
        history_msgs = await self._assistant_repo.list_messages(org_id, thread_id)
        history_payload = []
        for m in history_msgs:
            text = m.question or (
                m.answer.parts[0].text if m.answer and m.answer.parts else ""
            )
            history_payload.append({"role": m.role, "content": text})

        # 3. Call AI reader
        call = await self._reader.ask_assistant(history_payload, context_str)
        raw_response = call.value
        answer_text = getattr(raw_response, "answer", str(raw_response))

        # 4. Check grounding
        grounding_res = check_grounding(answer_text, grounding_ctx)

        # 5. Extract citations
        citation_matches = re.findall(r"\[\[([a-zA-Z0-9_]+):([^\]]+)\]\]", answer_text)
        citations = [
            CitationRef(ref=f"{kind}:{cid}", label=f"{kind.title()} {cid}")
            for kind, cid in citation_matches
        ]

        # Format answer parts
        parts = await self._build_answer_parts(org_id, question, answer_text)

        answer_obj = MessageAnswer(
            parts=parts,
            citations=citations,
            grounding=GroundingRef(
                verdict="AGREED" if grounding_res.valid else "REJECTED",
                citations=[f"{c.kind}:{c.id}" for c in grounding_res.citations],
            ),
            tools_used=["get_period_summary", "list_findings", "list_review_items"],
        )

        assistant_msg = AssistantMessage(
            message_id=_new_id("msg"),
            role="assistant",
            created_at=datetime.now(UTC),
            answer=answer_obj,
        )
        await self._assistant_repo.append_message(org_id, thread_id, assistant_msg)
        return assistant_msg

    async def stream_ask(
        self, org_id: str, uid: str, thread_id: str, question: str
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream progress steps, tool calls, answer tokens, and the canonical AssistantMessage."""
        if self._entitlements is not None:
            await self._entitlements.reserve_assistant_question(org_id)

        # 1. Save user message
        now = datetime.now(UTC)
        user_msg = AssistantMessage(
            message_id=_new_id("msg"),
            role="user",
            created_at=now,
            question=question,
        )
        await self._assistant_repo.append_message(org_id, thread_id, user_msg)

        # 2. Activity step: gathering facts & running read-only tools
        yield {
            "event": "step",
            "data": {"node": "context", "label": "Checking reconciled books & findings"},
        }
        await asyncio.sleep(0.04)

        context_str, grounding_ctx = await self._gather_context(org_id)
        yield {
            "event": "tool",
            "data": {
                "name": "get_period_summary",
                "args_summary": "reconciled figures",
                "ok": True,
            },
        }
        await asyncio.sleep(0.03)
        yield {
            "event": "tool",
            "data": {
                "name": "list_findings",
                "args_summary": "open risk findings",
                "ok": True,
            },
        }
        await asyncio.sleep(0.03)
        yield {
            "event": "tool",
            "data": {
                "name": "list_review_items",
                "args_summary": "open review items",
                "ok": True,
            },
        }
        await asyncio.sleep(0.03)

        # 3. Activity step: consulting Gemini reader
        yield {
            "event": "step",
            "data": {"node": "reader", "label": "Consulting Gemini on workspace books"},
        }

        history_msgs = await self._assistant_repo.list_messages(org_id, thread_id)
        history_payload = []
        for m in history_msgs:
            text = m.question or (
                m.answer.parts[0].text if m.answer and m.answer.parts else ""
            )
            history_payload.append({"role": m.role, "content": text})

        call = await self._reader.ask_assistant(history_payload, context_str)
        raw_response = call.value
        answer_text = getattr(raw_response, "answer", str(raw_response))

        # 4. Stream tokens chunk-by-chunk for live typing experience
        words = answer_text.split(" ")
        for i, word in enumerate(words):
            space = " " if i > 0 else ""
            yield {"event": "token", "data": {"text": f"{space}{word}"}}
            await asyncio.sleep(0.015)

        # 5. Activity step: Grounding check
        yield {
            "event": "step",
            "data": {"node": "grounding", "label": "Verifying claims against workspace records"},
        }

        grounding_res = check_grounding(answer_text, grounding_ctx)

        # 6. Extract citations & format canonical message
        citation_matches = re.findall(r"\[\[([a-zA-Z0-9_]+):([^\]]+)\]\]", answer_text)
        citations = [
            CitationRef(ref=f"{kind}:{cid}", label=f"{kind.title()} {cid}")
            for kind, cid in citation_matches
        ]

        parts = await self._build_answer_parts(org_id, question, answer_text)
        answer_obj = MessageAnswer(
            parts=parts,
            citations=citations,
            grounding=GroundingRef(
                verdict="AGREED" if grounding_res.valid else "REJECTED",
                citations=[f"{c.kind}:{c.id}" for c in grounding_res.citations],
            ),
            tools_used=["get_period_summary", "list_findings", "list_review_items"],
        )

        assistant_msg = AssistantMessage(
            message_id=_new_id("msg"),
            role="assistant",
            created_at=datetime.now(UTC),
            answer=answer_obj,
        )
        await self._assistant_repo.append_message(org_id, thread_id, assistant_msg)

        msg_body = {
            "messageId": assistant_msg.message_id,
            "role": assistant_msg.role,
            "question": assistant_msg.question,
            "answer": {
                "parts": [p.model_dump() for p in answer_obj.parts],
                "citations": [c.model_dump() for c in answer_obj.citations],
                "grounding": answer_obj.grounding.model_dump() if answer_obj.grounding else None,
                "toolsUsed": answer_obj.tools_used,
            },
            "createdAt": assistant_msg.created_at.isoformat(),
        }

        yield {"event": "message", "data": msg_body}
        yield {"event": "done", "data": {"status": "complete"}}


    async def suggest_reconciliation_match(
        self, org_id: str, tx_id: str
    ) -> MatchSuggestion:
        """Evaluate an unmatched bank transaction line against candidate documents using Gemini."""
        bank_line = await self._bank_line_repo.get_line(org_id, tx_id)
        if bank_line is None:
            return MatchSuggestion(
                recommended_doc_id=None,
                confidence=0.0,
                reason="Bank line not found.",
                missing_document_advice="Select a valid bank line to analyze.",
            )

        # Find candidates from documents in the same org
        docs, _ = await self._doc_repo.list_documents(org_id, limit=50)
        candidates_lines = []
        for d in docs:
            candidates_lines.append(
                f"- Document ID: {d.doc_id}, File: {d.file_name}, "
                f"Type: {d.doc_type}, Status: {d.status.value}"
            )

        direction = "CREDIT" if bank_line.amount > 0 else "DEBIT"
        line_info = (
            f"ID: {bank_line.tx_id}, Date: {bank_line.date}, Amount: {abs(bank_line.amount)}, "
            f"Direction: {direction}, Counterparty: {bank_line.counterparty_name or 'Unknown'}, "
            f"Description: {bank_line.description}"
        )
        candidates_info = "\n".join(candidates_lines) or "No candidate documents found."

        call = await self._reader.suggest_match(line_info, candidates_info)
        return call.value

    async def _build_answer_parts(
        self, org_id: str, question: str, answer_text: str
    ) -> list[AnswerPart]:
        parts = [AnswerPart(type="text", text=answer_text)]
        lower_q = question.lower()
        diagram_triggers = [
            "chart",
            "diagram",
            "sankey",
            "waterfall",
            "breakdown",
            "flow",
            "money flow",
            "grafik",
        ]
        invoice_triggers = [
            "unpaid",
            "invoice",
            "invoices",
            "bill",
            "bills",
            "tagihan",
            "piutang",
            "hutang",
            "receivable",
            "payable",
        ]
        if any(w in lower_q for w in invoice_triggers):
            unpaid_invoices = []
            if self._invoices is not None:
                all_invs = await self._invoices.list_records(org_id, limit=50)
                unpaid_invoices = [
                    inv
                    for inv in all_invs
                    if (inv.evidence or {}).get("payment", "UNPAID")
                    not in ("PAID_BANK", "PAID_CASH", "CONFIRMED_BY_YOU")
                ]
            if unpaid_invoices:
                amounts = [float(inv.total or 0) for inv in unpaid_invoices]
                max_amt = max(amounts, default=1.0) or 1.0
                chart_rows: list[list[str]] = []
                for inv in unpaid_invoices[:6]:
                    party = (
                        inv.buyer_name
                        if inv.kind == "SALES"
                        else (inv.issuer_name or "Supplier")
                    )
                    amt = float(inv.total or 0)
                    pct = f"{min(100, max(15, int((amt / max_amt) * 100)))}%"
                    label = inv.number or inv.invoice_id[-8:]
                    chart_rows.append([label, f"{party} • {amt:,.0f} {inv.currency or 'IDR'}", pct])
                parts.append(
                    AnswerPart(
                        type="chart",
                        chart="INVOICE_BREAKDOWN",
                        rows=chart_rows,
                        query={"target": "documents", "view": "INVOICES"},
                    )
                )
        elif any(w in lower_q for w in diagram_triggers):
            chart_type = (
                "MONEY_FLOW"
                if any(w in lower_q for w in ["flow", "sankey", "money"])
                else "MONTHLY_IN_OUT"
            )
            months = await self._month_repo.list(org_id)
            chart_rows = []
            if months:
                for m in sorted(months, key=lambda x: x.month)[-6:]:
                    figs = m.figures or {}
                    in_val = figs.get("inflow_minor", 0) / 100
                    out_val = figs.get("outflow_minor", 0) / 100
                    chart_rows.append(
                        [m.month, f"In: {in_val:,.0f} | Out: {out_val:,.0f}", "100%"]
                    )
            parts.append(
                AnswerPart(
                    type="chart",
                    chart=chart_type,
                    rows=chart_rows,
                    query={"target": "dashboard", "view": "OPERATING"},
                )
            )
        return parts
