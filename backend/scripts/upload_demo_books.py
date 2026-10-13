#!/usr/bin/env python3
"""Upload the synthetic demo books into a workspace, end to end (docs/18 §5, T002-17).

S1 in full, then only what each later scenario changes (S2 to S4): a file already uploaded with the
same content is not sent again, so the workspace holds the half-year once plus about ten scenario
files (an edited statement, copies, a scanned invoice, a diverted invoice, unpaid bills) instead of
four copies of everything. Uploads go through the same services the API calls, with the reader and
the queue the settings configure (Gemini on Vertex AI), four documents at a time; then every month
is reconciled again. Prints counts only. The workspace must keep its books in IDR.

Usage (from backend/; keep the machine awake: a sleeping laptop freezes open network calls):
  caffeinate -i uv run python -m scripts.upload_demo_books --email owner@example.com
  uv run python -m scripts.upload_demo_books --email owner@example.com --dry-run
"""

import argparse
import asyncio
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parents[2] / "tools" / "synthetic" / "out" / "demo"
SCENARIOS = ("S1", "S2", "S3", "S4")
CHUNK = 4


def _order(folder: Path) -> list[str]:
    truth = json.loads((folder / "truth.json").read_text(encoding="utf-8"))
    return [x if isinstance(x, str) else x["file"] for x in truth["uploadOrder"]]


def upload_plan(demo_dir: Path, scenarios: tuple[str, ...] = SCENARIOS) -> list[tuple[str, Path]]:
    """Every file of the first scenario, then each later scenario's files whose name and content
    were not uploaded before. A file with new content keeps its place in its scenario's order; a
    second name for the same bytes (an intended exact copy) is uploaded."""
    plan: list[tuple[str, Path]] = []
    sent: set[tuple[str, str]] = set()
    for scenario in scenarios:
        folder = demo_dir / scenario / "seed-1"
        for name in _order(folder):
            path = folder / name
            key = (name, hashlib.sha256(path.read_bytes()).hexdigest())
            if key in sent:
                continue
            sent.add(key)
            plan.append((scenario, path))
    return plan


def _log(*parts: object) -> None:
    print(time.strftime("%H:%M:%S"), *parts, flush=True)


async def _run(email: str, demo_dir: Path, dry_run: bool) -> int:
    import firebase_admin
    from firebase_admin import auth

    from app.adapters.cloud_tasks import InlineTaskQueue, month_task_id
    from app.core.auth import Principal
    from app.core.settings import Settings
    from app.domain.models.workspace import BankAccountCreate, WorkspaceUpdate
    from app.main import AppDeps, load_plans
    from app.observability.tracing import setup_tracing

    plan = upload_plan(demo_dir)
    _log(f"{len(plan)} files:", dict(Counter(scenario for scenario, _ in plan)))
    if dry_run:
        for scenario, path in plan:
            print(f"  {scenario} {path.name}")
        return 0

    settings = Settings()
    if not firebase_admin._apps:
        firebase_admin.initialize_app(options={"projectId": settings.google_cloud_project})
    user = auth.get_user_by_email(email)
    claims = user.custom_claims or {}
    org_id = claims.get("orgId")
    if not org_id:
        print("This account has no workspace yet: onboard first.", file=sys.stderr)
        return 1
    principal = Principal(
        uid=user.uid, email=email, org_id=org_id, role=claims.get("role", "owner")
    )
    setup_tracing(settings)
    deps = AppDeps(settings, load_plans(settings.contract_path(settings.plans_file)))
    workspace = await deps.workspace_repo.get_workspace(org_id)
    if workspace is None or workspace.currency != "IDR":
        print("The synthetic books are in IDR; this workspace is not.", file=sys.stderr)
        return 1

    # The books belong to the synthetic business: its legal name and its declared bank account.
    truth = json.loads((demo_dir / "S1" / "seed-1" / "truth.json").read_text(encoding="utf-8"))
    business = truth["workspace"]
    if workspace.profile.legal_name != business["profile"]["legalName"]:
        profile = workspace.profile.model_copy(
            update={"legal_name": business["profile"]["legalName"]}
        )
        await deps.workspace_service.update(principal, org_id, WorkspaceUpdate(profile=profile))
        _log("legal name set to", business["profile"]["legalName"])
    declared = await deps.workspace_repo.list_bank_accounts(org_id)
    for account in business["bankAccounts"]:
        if any(a.account_masked.endswith(account["accountNumber"][-4:]) for a in declared):
            continue
        await deps.workspace_service.add_bank_account(
            principal,
            org_id,
            BankAccountCreate(
                bank_name=account["bankName"],
                account_number=account["accountNumber"],
                holder_name=account["holderName"],
            ),
        )
        _log("bank account declared:", account["bankName"])

    # Locally the queue runs tasks in this process; with Cloud Tasks the deployed worker reads them.
    queue = deps.task_queue if isinstance(deps.task_queue, InlineTaskQueue) else None
    outcomes: Counter[str] = Counter()
    for start in range(0, len(plan), CHUNK):
        for scenario, path in plan[start : start + CHUNK]:
            try:
                doc = await deps.document_service.upload(
                    principal=principal, file_bytes=path.read_bytes(), filename=path.name
                )
                outcomes[str(getattr(doc.status, "value", doc.status))] += 1
            except Exception as error:  # noqa: BLE001 - report every refused file and go on
                outcomes[type(error).__name__] += 1
                _log(f"  {scenario} {path.name}: {type(error).__name__}")
        if queue:
            await queue.drain()
        if (start // CHUNK) % 5 == 4:
            _log(f"  {min(start + CHUNK, len(plan))}/{len(plan)} uploaded")
    if queue:
        await queue.drain()
    _log("uploads:", dict(outcomes))

    for month in sorted(await deps.month_repo.list(org_id), key=lambda m: m.month):
        generation, _ = await deps.month_repo.bump_generation(org_id, month.month, dirty=True)
        await deps.run_service.reconcile_month_task(
            org_id=org_id,
            month=month.month,
            generation=generation,
            run_id=month_task_id(org_id, month.month, generation),
        )
    docs, _ = await deps.doc_repo.list_documents(org_id, limit=500)
    _log("documents:", dict(Counter(str(getattr(d.status, "value", d.status)) for d in docs)))
    for month in sorted(await deps.month_repo.list(org_id), key=lambda m: m.month):
        _log(f"  {month.month}: {month.state.value}, risk {(month.risk or {}).get('level')}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload the synthetic demo books (docs/18 §5).")
    parser.add_argument("--email", required=True, help="The workspace owner's sign-in email")
    parser.add_argument("--demo-dir", type=Path, default=DEMO_DIR)
    parser.add_argument("--dry-run", action="store_true", help="List the files and stop")
    args = parser.parse_args()
    return asyncio.run(_run(args.email, args.demo_dir, args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
