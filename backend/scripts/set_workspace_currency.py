#!/usr/bin/env python3
"""Support only: change a workspace's currency (ADR-020).

The currency is fixed after onboarding because stored amounts are in it. This script changes it
on a workspace with no documents, refuses when documents exist unless --force (their amounts would
then be labelled with the new currency), and records a CURRENCY_CHANGED audit event.

Usage (from backend/):
  uv run python -m scripts.set_workspace_currency --email owner@example.com --currency MYR
  uv run python -m scripts.set_workspace_currency --org org_01J... --currency MYR --dry-run
"""

import argparse
import asyncio
import os
import sys
from datetime import UTC, datetime
from typing import Any, get_args

from google.cloud.firestore import AsyncClient

from app.core.ids import new_id
from app.domain.models.workspace import Currency

CURRENCIES: tuple[str, ...] = get_args(Currency)


class CurrencyChangeRefused(Exception):
    pass


async def set_workspace_currency(
    db: AsyncClient,
    org_id: str,
    currency: str,
    *,
    actor: str,
    now: datetime,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    if currency not in CURRENCIES:
        raise CurrencyChangeRefused(f"{currency} is not one of {', '.join(CURRENCIES)}")
    org_ref = db.collection("orgs").document(org_id)
    snap = await org_ref.get()
    if not snap.exists:
        raise CurrencyChangeRefused(f"workspace {org_id} does not exist")
    current = (snap.to_dict() or {}).get("currency")
    count = await org_ref.collection("documents").count().get()
    documents = int(count[0][0].value)
    result = {"orgId": org_id, "from": current, "to": currency, "documents": documents}
    if documents and not force:
        raise CurrencyChangeRefused(
            f"{org_id} has {documents} document(s) read in {current}; their amounts would be shown "
            f"as {currency}. Remove them first, or pass --force."
        )
    if dry_run or current == currency:
        return result
    event_id = new_id("evt")
    batch = db.batch()
    batch.update(org_ref, {"currency": currency})
    batch.set(
        org_ref.collection("events").document(event_id),
        {
            "schemaVersion": 1,
            "eventId": event_id,
            "orgId": org_id,
            "type": "CURRENCY_CHANGED",
            "actorUid": actor,
            "actorRole": "support",
            "at": now,
            "subject": {"orgId": org_id},
            "details": {"from": current or "", "to": currency, "documents": documents},
        },
    )
    await batch.commit()
    return result


def _org_of_email(email: str) -> str:
    from firebase_admin import auth

    from app.adapters.firebase_identity import _ensure_app

    _ensure_app()
    user = auth.get_user_by_email(email)
    org_id = (user.custom_claims or {}).get("orgId")
    if not org_id:
        raise CurrencyChangeRefused(f"{email} has no workspace claim")
    return str(org_id)


async def _main(args: argparse.Namespace) -> int:
    org_id = args.org or _org_of_email(args.email)
    db = AsyncClient(project=args.project, database=args.database)
    try:
        result = await set_workspace_currency(
            db,
            org_id,
            args.currency,
            actor="support-script",
            now=datetime.now(UTC),
            force=args.force,
            dry_run=args.dry_run,
        )
    except CurrencyChangeRefused as refused:
        print(f"Refused: {refused}", file=sys.stderr)
        return 1
    verb = "Would change" if args.dry_run else "Changed"
    print(
        f"{verb} {result['orgId']} from {result['from']} to {result['to']} "
        f"({result['documents']} documents)"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    who = parser.add_mutually_exclusive_group(required=True)
    who.add_argument("--org", help="Workspace ID")
    who.add_argument("--email", help="Owner email; the workspace comes from their claim")
    parser.add_argument("--currency", required=True, choices=CURRENCIES)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--project", default=None, help="Defaults to the ADC project")
    parser.add_argument(
        "--database",
        default=os.environ.get("FIRESTORE_DATABASE", "(default)"),
        help="Firestore database (ADR-021: kredibel)",
    )
    return asyncio.run(_main(parser.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
