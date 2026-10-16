#!/usr/bin/env python3
"""Read a workspace's photos and scans again with the OCR witness (spec 022 phase B, AC-022-5).

Finds every read document whose pages have no stored chunks (no text layer, read before the OCR
witness), reads each again in a new run, then reconciles every month and rebuilds the extraction
store. Runs in this process with the settings' reader and OCR; prints counts only.

Usage (from backend/, with DOCAI_OCR_PROCESSOR_ID and DOCAI_OCR_VERSION set):
  uv run python -m scripts.reread_documents --org org_demo_template
"""

import argparse
import asyncio
import sys


async def _run(org: str) -> int:
    from app.adapters.cloud_tasks import InlineTaskQueue, month_task_id
    from app.adapters.policy_files import load_plans
    from app.core.settings import Settings
    from app.main import AppDeps
    from app.services.extraction_service import ExtractionPorts, rebuild_workspace

    settings = Settings()
    if not settings.docai_ocr_processor_id:
        print("DOCAI_OCR_PROCESSOR_ID is not set: nothing would change.", file=sys.stderr)
        return 1
    deps = AppDeps(settings, load_plans(settings.contract_path(settings.plans_file)))
    docs, _ = await deps.doc_repo.list_documents(org, limit=500)
    without = [
        d
        for d in docs
        if d.status.value in ("DONE", "NEEDS_INPUT")
        and d.doc_type.value != "LEDGER_EXPORT"
        and not await deps.chunk_repo.list_chunks(org, d.doc_id)
    ]
    for doc in without:
        run = await deps.run_service.reread_document(org, doc.doc_id)
        try:
            await deps.run_service.process_document_task(org, doc.doc_id, run.run_id, 2)
        except Exception as error:  # noqa: BLE001 - report it and go on with the others
            print(f"  {doc.doc_id}: {type(error).__name__}")
    if isinstance(deps.task_queue, InlineTaskQueue):
        await deps.task_queue.drain()
    for month in sorted(await deps.month_repo.list(org), key=lambda m: m.month):
        generation, _ = await deps.month_repo.bump_generation(org, month.month, dirty=True)
        await deps.run_service.reconcile_month_task(
            org_id=org,
            month=month.month,
            generation=generation,
            run_id=month_task_id(org, month.month, generation),
        )
    ports = ExtractionPorts(
        storage=deps.storage,
        page_text=deps.page_text,
        chunks=deps.chunk_repo,
        bank_lines=deps.bank_lines,
        invoices=deps.invoices,
        receipts=deps.receipts,
        labels=deps.label_repo,
        embedder=deps.embedder,
    )
    counts = await rebuild_workspace(ports, deps.doc_repo, org)
    print(f"{org}: {len(without)} read again; extraction {counts}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--org", required=True)
    return asyncio.run(_run(parser.parse_args().org))


if __name__ == "__main__":
    sys.exit(main())
