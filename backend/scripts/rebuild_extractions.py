#!/usr/bin/env python3
"""Rebuild every read document's chunks and page Markdown in a workspace (spec 022, AC-022-3).

No model call: the chunks come from the extraction cache, else the stored PDF's text layer. Prints
counts only.

Usage (from backend/):
  uv run python -m scripts.rebuild_extractions --org org_demo_template
  uv run python -m scripts.rebuild_extractions --email owner@example.com
"""

import argparse
import asyncio
import sys


async def _run(org: str | None, email: str | None) -> int:
    from app.adapters.policy_files import load_plans
    from app.core.settings import Settings
    from app.main import AppDeps
    from app.services.extraction_service import ExtractionPorts, rebuild_workspace

    settings = Settings()
    if org is None:
        import firebase_admin
        from firebase_admin import auth

        if not firebase_admin._apps:
            firebase_admin.initialize_app(options={"projectId": settings.google_cloud_project})
        org = (auth.get_user_by_email(email or "").custom_claims or {}).get("orgId")
        if not org:
            print("This account has no workspace.", file=sys.stderr)
            return 1
    deps = AppDeps(settings, load_plans(settings.contract_path(settings.plans_file)))
    ports = ExtractionPorts(
        storage=deps.storage,
        page_text=deps.page_text,
        chunks=deps.chunk_repo,
        bank_lines=deps.bank_lines,
        invoices=deps.invoices,
        receipts=deps.receipts,
        labels=deps.label_repo,
    )
    counts = await rebuild_workspace(ports, deps.doc_repo, org)
    print(f"{org}: {counts}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--org")
    group.add_argument("--email")
    args = parser.parse_args()
    return asyncio.run(_run(args.org, args.email))


if __name__ == "__main__":
    sys.exit(main())
