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
        folder = demo_dir if (demo_dir / "truth.json").exists() else demo_dir / scenario / "seed-1"
        if not folder.exists():
            continue
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


DEFAULT_CLASSIFICATIONS: dict[str, tuple[str, str]] = {
    "1000": ("BALANCE_SHEET", "CASH"),
    "1110": ("BALANCE_SHEET", "CASH"),
    "1200": ("BALANCE_SHEET", "RECEIVABLES"),
    "1300": ("BALANCE_SHEET", "PAYABLES"),
    "1400": ("BALANCE_SHEET", "PAYABLES"),
    "2100": ("BALANCE_SHEET", "PAYABLES"),
    "2200": ("BALANCE_SHEET", "RECEIVABLES"),
    "2300": ("BALANCE_SHEET", "CASH"),
    "3100": ("BALANCE_SHEET", "GENERAL"),
    "4000": ("REVENUE", "RECEIVABLES"),
    "4100": ("REVENUE", "CASH"),
    "5100": ("COST_OF_SALES", "PAYABLES"),
    "5200": ("COST_OF_SALES", "PAYABLES"),
    "6000": ("OPERATING_EXPENSES", "PAYROLL"),
    "6050": ("OPERATING_EXPENSES", "PAYABLES"),
    "6100": ("OPERATING_EXPENSES", "CASH"),
    "6150": ("OPERATING_EXPENSES", "PAYABLES"),
    "6200": ("OPERATING_EXPENSES", "PAYABLES"),
    "6300": ("OPERATING_EXPENSES", "PAYABLES"),
    "6400": ("OPERATING_EXPENSES", "CASH"),
    "6500": ("OPERATING_EXPENSES", "PAYABLES"),
    "6600": ("OPERATING_EXPENSES", "PAYABLES"),
    "6900": ("OPERATING_EXPENSES", "CASH"),
    "7100": ("FINANCE_COSTS", "CASH"),
}


async def seed_demo_ledger(
    deps,
    org_id: str,
    principal,
    demo_dir: Path,
    months: set[str] | None = None,
) -> int:
    from dataclasses import replace
    from datetime import UTC, datetime

    from app.core.ids import new_id
    from app.domain.ledger_csv import parse_ledger_csv
    from app.domain.models.document import DocStatus, DocType
    from app.domain.models.events import AuditEvent
    from app.domain.profit_loss import Classification

    csv_path = demo_dir / "S1" / "seed-1" / "ledger-2026-H1.csv"
    if not csv_path.exists():
        csv_candidates = list(demo_dir.glob("**/ledger-*.csv")) or list(
            demo_dir.glob("ledger-*.csv")
        )
        if csv_candidates:
            csv_path = csv_candidates[0]
        else:
            _log(f"ledger file not found at {csv_path}")
            return 0

    content = csv_path.read_text(encoding="utf-8")
    held_docs, _ = await deps.doc_repo.list_documents(org_id, limit=500)
    ledger_doc = next(
        (
            d
            for d in held_docs
            if d.file_name.startswith("ledger-") or d.doc_type == DocType.LEDGER_EXPORT
        ),
        None,
    )
    if ledger_doc is None:
        ledger_doc = await deps.document_service.upload(
            principal=principal, file_bytes=content.encode("utf-8"), filename="ledger-2026-H1.csv"
        )
    queue = getattr(deps, "task_queue", None)
    if queue and hasattr(queue, "drain"):
        await queue.drain()
    fresh = await deps.doc_repo.get_document(org_id, ledger_doc.doc_id)
    if fresh is not None:
        ledger_doc = fresh
    if ledger_doc.status != DocStatus.DONE or ledger_doc.doc_type != DocType.LEDGER_EXPORT:
        ledger_doc = replace(ledger_doc, status=DocStatus.DONE, doc_type=DocType.LEDGER_EXPORT)
        await deps.doc_repo.save_document(org_id, ledger_doc)

    rows = parse_ledger_csv(content, doc_id=ledger_doc.doc_id, currency="IDR")
    if months:
        rows = [r for r in rows if r.date.strftime("%Y-%m") in months]

    await deps.ledger_repo.save_rows(org_id, rows)
    row_months = sorted({r.date.strftime("%Y-%m") for r in rows})
    ledger_meta = {
        "rowsImported": len(rows),
        "rows": len(rows),
        "dateFrom": min(r.date for r in rows).isoformat() if rows else None,
        "dateTo": max(r.date for r in rows).isoformat() if rows else None,
    }
    ledger_doc = replace(ledger_doc, months=row_months, ledger_meta=ledger_meta)
    await deps.doc_repo.save_document(org_id, ledger_doc)
    _log(f"seeded {len(rows)} ledger entries for {org_id}")

    existing_classifications = await deps.ledger_repo.classifications(org_id)
    confirmed_count = 0
    now = datetime.now(UTC)
    for code, (pnl_line, subledger) in DEFAULT_CLASSIFICATIONS.items():
        if code not in existing_classifications:
            decision = Classification(account_code=code, pnl_line=pnl_line, subledger=subledger)
            event = AuditEvent(
                event_id=new_id("evt"),
                type="ACCOUNT_CLASSIFIED",
                actor_uid=principal.uid,
                actor_role=principal.role,
                at=now,
                subject={"accountCode": code},
                details={"pnlLine": pnl_line, "subledger": subledger},
            )
            await deps.ledger_repo.confirm(org_id, decision, event)
            confirmed_count += 1
    if confirmed_count:
        _log(f"confirmed {confirmed_count} account classifications")
    return len(rows)



async def _run(
    email: str,
    demo_dir: Path,
    dry_run: bool,
    months: set[str] | None = None,
    clean: bool = False,
    scenarios: tuple[str, ...] = SCENARIOS,
    seed_ledger_only: bool = False,
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

    if seed_ledger_only:
        _log(f"seeding ledger entries and classifications for workspace {org_id}...")
        await seed_demo_ledger(deps, org_id, principal, demo_dir, months)
        _log("ledger seeding complete.")
        return 0

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
    truth_file = (
        demo_dir / "truth.json"
        if (demo_dir / "truth.json").exists()
        else demo_dir / "S1" / "seed-1" / "truth.json"
    )
    truth = json.loads(truth_file.read_text(encoding="utf-8"))
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

    # Seed general ledger rows and account classifications for company P&L
    await seed_demo_ledger(deps, org_id, principal, demo_dir, months)

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
    parser.add_argument(
        "--seed-ledger-only",
        action="store_true",
        help="Seed ledger rows and account classifications without uploading documents",
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
            seed_ledger_only=args.seed_ledger_only,
        )
    )


if __name__ == "__main__":
    sys.exit(main())

