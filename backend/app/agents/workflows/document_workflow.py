"""Document workflow orchestrator (AC-004-1, AC-004-2, AC-004-3, docs/06 §2.2)."""

import asyncio
from dataclasses import replace
from typing import Any

from google.adk import Context, Workflow
from google.adk.workflow import node

from app.agents.deps import PipelineDeps
from app.agents.nodes import doc_nodes as n
from app.agents.stages import node_input_dict
from app.domain.models.document import DocStatus


def build_document_workflow(deps: PipelineDeps) -> Workflow:
    """Build dynamic ADK document_workflow graph with stub or real nodes."""
    page_concurrency = deps.settings.page_concurrency or 6
    page_sem = asyncio.Semaphore(page_concurrency)

    @node(name="document_workflow", rerun_on_resume=True)
    async def document_workflow(ctx: Context, node_input: Any = None) -> dict[str, Any]:
        input_data = node_input_dict(ctx, node_input)
        org_id = str(input_data.get("orgId") or input_data.get("org_id") or "")
        doc_id = str(input_data.get("docId") or input_data.get("doc_id") or "")
        attempt = int(input_data.get("attempt", 1))

        try:
            doc = await ctx.run_node(n.load_document(deps), input_data)
            if doc.get("status") == "SKIPPED":
                return doc

            doc = await ctx.run_node(n.screen_document(deps), doc)
            doc = await ctx.run_node(n.inspect_file(deps), doc)
            # Parse first, so the classifier and the reader get the page's chunks (ADR-023).
            doc = await ctx.run_node(n.parse_pages(deps), doc)
            doc = await ctx.run_node(n.classify_document(deps), doc)
            if doc.get("status") == "NEEDS_INPUT":
                return doc

            if doc.get("docType") == "LEDGER_EXPORT":
                doc = await ctx.run_node(n.propose_ledger_mapping(deps), doc)
                if doc.get("status") == "NEEDS_INPUT":
                    return doc
                doc = await ctx.run_node(n.parse_ledger(deps), doc)
            else:

                async def read(page_no: int, context: dict[str, Any] | None):
                    async with page_sem:
                        return await ctx.run_node(
                            n.read_page(deps),
                            {**doc, "page": page_no, "context": context},
                        )

                pages = n.pages_to_read(doc)
                first = await read(1, None)
                rest = await asyncio.gather(
                    *(read(p, first.get("header_context")) for p in pages[1:])
                )
                doc = await ctx.run_node(
                    n.verify_pages(deps), {**doc, "doc": doc, "ai": [first, *rest]}
                )
                doc = await ctx.run_node(n.escalate_pages(deps), doc)
                doc = await ctx.run_node(n.check_document(deps), doc)

            doc = await ctx.run_node(n.detect_content_duplicates(deps), doc)
            doc = await ctx.run_node(n.categorize_bank_lines(deps), doc)
            return await ctx.run_node(n.finalize_document(deps), doc)

        except Exception:
            if attempt >= 3:
                existing = await deps.doc_repo.get_document(org_id, doc_id)
                if existing is not None:
                    failed = replace(
                        existing,
                        status=DocStatus.FAILED,
                        status_detail="E02_EXTRACTION_FAILED",
                    )
                    await deps.doc_repo.save_document(org_id, failed)
            raise

    return Workflow(name="document_workflow", edges=[("START", document_workflow)])
