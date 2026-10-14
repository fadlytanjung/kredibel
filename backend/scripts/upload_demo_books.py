#!/usr/bin/env python3
"""Upload the synthetic demo books into a workspace, end to end (docs/18 §5, T002-17).

S1 in full, then only what each later scenario changes (S2 to S4): a file already uploaded with the
same content is not sent again, so the workspace holds the half-year once plus about ten scenario
files (an edited statement, copies, a scanned invoice, a diverted invoice, unpaid bills) instead of
four copies of everything. Uploads go through the same services the API calls, with the reader and
the queue the settings configure (Gemini on Vertex AI), four documents at a time; then every month
is reconciled again. Prints counts only. The workspace must keep its books in IDR.

Run it again after an interruption: it uploads only what is missing and finishes half-read
documents.

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


def upload_plan(
    demo_dir: Path,
    scenarios: tuple[str, ...] = SCENARIOS,
    already: set[tuple[str, str]] | None = None,
    months: set[str] | None = None,
) -> list[tuple[str, Path]]:
    """Every file of the first scenario, then each later scenario's files whose name and content
    were not uploaded before. A file with new content keeps its place in its scenario's order; a
    second name for the same bytes (an intended exact copy) is uploaded. `already` holds the
    (name, sha256) of the workspace's documents, so a run that stopped half way resumes."""
    plan: list[tuple[str, Path]] = []
    sent: set[tuple[str, str]] = set(already or ())
    for scenario in scenarios:
        folder = demo_dir / scenario / "seed-1"
        for name in _order(folder):
            is_ledger = name.startswith("ledger-") and any(
                m in name or "H1" in name for m in (months or ())
            )
            if months and not any(m in name for m in months) and not is_ledger:
                continue
            path = folder / name
            key = (name, hashlib.sha256(path.read_bytes()).hexdigest())
            if key in sent:
                continue
            sent.add(key)
            plan.append((scenario, path))
    return plan


def _log(*parts: object) -> None:
    print(time.strftime("%H:%M:%S"), *parts, flush=True)


async def _run(
    email: str,
    demo_dir: Path,
    dry_run: bool,
    months: set[str] | None = None,
    clean: bool = False,
    scenarios: tuple[str, ...] = SCENARIOS,
) -> int:
    import firebase_admin
    from firebase_admin import auth

    from app.adapters.cloud_tasks import InlineTaskQueue, month_task_id
    from app.core.auth import Principal
    from app.core.settings import Settings
    from app.domain.models.document import DocStatus
    from app.domain.models.run import RunStatus
    from app.domain.models.workspace import BankAccountCreate, WorkspaceUpdate
    from app.main import AppDeps, load_plans
    from app.observability.tracing import setup_tracing

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
    FINAL = {DocStatus.DONE, DocStatus.DUPLICATE, DocStatus.NEEDS_INPUT, DocStatus.FAILED}
    FINAL |= {DocStatus.QUARANTINED}
    workspace = await deps.workspace_repo.get_workspace(org_id)
    if workspace is None or workspace.currency != "IDR":
        print("The synthetic books are in IDR; this workspace is not.", file=sys.stderr)
        return 1

    if clean and not dry_run:
        from scripts.clean_workspace import clean_org_data

        _log(f"cleaning workspace {org_id} before upload...")
        deleted = await clean_org_data(org_id, settings)
        _log("cleaned:", {k: v for k, v in deleted.items() if v})

    # Resume: skip what the workspace already holds; finish documents a stopped run left half read.
    held, _ = await deps.doc_repo.list_documents(org_id, limit=500)
    plan = upload_plan(
        demo_dir,
        scenarios=scenarios,
        already={(d.file_name, d.sha256) for d in held},
        months=months,
    )
    _log(
        f"{len(plan)} files to upload, {len(held)} already there:",
        dict(Counter(s for s, _ in plan)),
    )
    if dry_run:
        for scenario, path in plan:
            print(f"  {scenario} {path.name}")
        return 0
    unfinished = [d for d in held if d.status not in FINAL]
    for doc in unfinished:
        runs = await deps.run_repo.list_by_target(org_id, doc.doc_id)
        stuck = next((r for r in runs if r.status == RunStatus.RUNNING), None)
        if stuck is not None:
            await deps.run_service.process_document_task(org_id, doc.doc_id, stuck.run_id, 2)
    if unfinished:
        _log(f"{len(unfinished)} half-read document(s) finished")

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
                content = path.read_bytes()
                if months and path.name.startswith("ledger-") and path.suffix == ".csv":
                    month_suffixes = tuple(f"/{m.split('-')[1]}/{m.split('-')[0]}" for m in months)
                    filtered_lines = []
                    for line in content.decode("utf-8", errors="replace").splitlines(keepends=True):
                        if line.startswith("#") or line.startswith("Date,"):
                            filtered_lines.append(line)
                            continue
                        date_str = line.split(",", 1)[0].strip()
                        if any(date_str.endswith(sfx) for sfx in month_suffixes):
                            filtered_lines.append(line)
                    content = "".join(filtered_lines).encode("utf-8")
                doc = await deps.document_service.upload(
                    principal=principal, file_bytes=content, filename=path.name
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

    months_to_reconcile = [
        m
        for m in sorted(await deps.month_repo.list(org_id), key=lambda m: m.month)
        if not months or m.month in months
    ]
    for month in months_to_reconcile:
        generation, _ = await deps.month_repo.bump_generation(org_id, month.month, dirty=True)
        await deps.run_service.reconcile_month_task(
            org_id=org_id,
            month=month.month,
            generation=generation,
            run_id=month_task_id(org_id, month.month, generation),
        )
    docs, _ = await deps.doc_repo.list_documents(org_id, limit=500)
    _log("documents:", dict(Counter(str(getattr(d.status, "value", d.status)) for d in docs)))
    for month in months_to_reconcile:
        fresh = await deps.month_repo.get(org_id, month.month)
        m_obj = fresh or month
        _log(f"  {m_obj.month}: {m_obj.state.value}, risk {(m_obj.risk or {}).get('level')}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload the synthetic demo books (docs/18 §5).")
    parser.add_argument("--email", required=True, help="The workspace owner's sign-in email")
    parser.add_argument("--demo-dir", type=Path, default=DEMO_DIR)
    parser.add_argument("--dry-run", action="store_true", help="List the files and stop")
    parser.add_argument("--months", help="Comma-separated months, e.g. 2026-04,2026-05,2026-06")
    parser.add_argument(
        "--clean", action="store_true", help="Wipe previous documents and runs before uploading"
    )
    parser.add_argument(
        "--scenarios",
        default="S1,S2,S3,S4",
        help="Comma-separated scenarios (default: S1,S2,S3,S4)",
    )
    args = parser.parse_args()
    months_filter = {m.strip() for m in args.months.split(",")} if args.months else None
    scenarios_tuple = tuple(s.strip() for s in args.scenarios.split(","))
    return asyncio.run(
        _run(
            args.email,
            args.demo_dir,
            args.dry_run,
            months=months_filter,
            clean=args.clean,
            scenarios=scenarios_tuple,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
