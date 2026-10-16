"""Folds labels stored under an older identity into one per subject (spec 016, 16 Oct 2026): a bank
line's category label was keyed by the line's counterparty too, so a counterparty assigned after the
category forked the label. A person's decision is always kept. Prints counts only.

    uv run python -m scripts.relabel --org org_... [--dry-run]
    uv run python -m scripts.relabel --all [--dry-run]
"""

import argparse
import asyncio
import sys


async def _run(orgs: list[str] | None, dry_run: bool) -> int:
    from google.cloud.firestore import AsyncClient

    from app.adapters.firestore.label_repo import FirestoreLabelRepository
    from app.core.settings import Settings
    from app.domain.labels import relabel_plan

    settings = Settings()
    db = AsyncClient(project=settings.google_cloud_project, database=settings.firestore_database)
    repo = FirestoreLabelRepository(db)
    if orgs is None:
        orgs = [snap.id async for snap in db.collection("orgs").select([]).stream()]
    total_rekey = total_delete = 0
    for org_id in orgs:
        labels = await repo.list_labels(org_id, limit=None)
        plan = relabel_plan(labels)
        if not plan.rekey and not plan.delete:
            continue
        total_rekey += len(plan.rekey)
        total_delete += len(plan.delete)
        print(
            f"{org_id}: {len(labels)} labels, {len(plan.rekey)} moved, {len(plan.delete)} removed"
        )
        if not dry_run:
            await repo.relabel(org_id, plan.rekey, plan.delete)
    print(f"{'dry run: ' if dry_run else ''}{total_rekey} moved, {total_delete} removed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--org")
    group.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return asyncio.run(_run(None if args.all else [args.org], args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
