#!/usr/bin/env python3
"""Seed the demo workspace: org_demo on the free trial with demo limits and its owner (AC-013-4).

Run by infra/bootstrap.sh step 9 (docs/16 §3). Idempotent: running it again resets the profile,
trial end and limit overrides, and re-sets the owner's claims.

Usage (from backend/):
  uv run python -m scripts.seed_demo_workspace --org org_demo \\
    --name "Sunrise Coffee Roasters" --entity COMPANY --trial-ends 2026-12-31 \\
    --owner owner@demo.kredibel
"""

import argparse
import asyncio
import os
import sys
from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from app.domain.models.workspace import EntityType, Profile, Subscription, Workspace
from app.ports.identity_admin import IdentityAdmin, IdentityUser
from app.ports.workspace_repository import NewWorkspace, OwnerMember

# AC-013-4. Set by the server only; the API never accepts overrides.
DEMO_OVERRIDES: dict[str, int | str] = {
    "documentsPerMonth": 600,
    "extractedPagesPerMonth": 3000,
    "monthRunsPerDay": 200,
    "aiSpendUsdPerMonth": "40.00",
}


def build_demo_workspace(
    *,
    org_id: str,
    name: str,
    entity: EntityType,
    trial_ends: str,
    timezone: str,
    owner: IdentityUser,
    now: datetime,
) -> NewWorkspace:
    # "Free trial to 31 Dec" means through that whole day in the workspace's time zone.
    last_day = date.fromisoformat(trial_ends)
    ends_local = datetime.combine(last_day + timedelta(days=1), time(0), tzinfo=ZoneInfo(timezone))
    workspace = Workspace(
        org_id=org_id,
        name=name,
        entity_type=entity,
        profile=Profile(legal_name=name),
        country="ID",
        timezone=timezone,
        currency="IDR",
        default_language="en",
        subscription=Subscription(
            plan_id="free_trial",
            status="TRIALING",
            trial_started_at=now,
            trial_ends_at=ends_local.astimezone(UTC),
            limit_overrides=dict(DEMO_OVERRIDES),
        ),
        created_by=owner.uid,
        created_at=now,
    )
    member = OwnerMember(uid=owner.uid, email=owner.email, display_name=owner.display_name)
    return NewWorkspace(workspace=workspace, owner=member)


class SeedRepository(Protocol):
    """FirestoreWorkspaceRepository; a server-only operation, so not on the port."""

    async def seed_workspace(self, new: NewWorkspace) -> None: ...


async def seed(repo: SeedRepository, identity: IdentityAdmin, new: NewWorkspace) -> None:
    await repo.seed_workspace(new)
    await identity.set_claims(new.owner.uid, {"orgId": new.workspace.org_id, "role": "owner"})


def _owner(email: str) -> IdentityUser:
    from firebase_admin import auth

    try:
        record = auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        # No password is set here; set one in the Firebase console (never in the repository).
        record = auth.create_user(email=email, email_verified=True)
        print(f"Created {email}; set its password in the Firebase console.")
    return IdentityUser(
        uid=record.uid,
        email=record.email,
        email_verified=bool(record.email_verified),
        display_name=record.display_name,
    )


async def _main(args: argparse.Namespace) -> None:
    from google.cloud.firestore import AsyncClient

    from app.adapters.firebase_identity import FirebaseIdentityAdmin
    from app.adapters.firestore.workspace_repo import FirestoreWorkspaceRepository

    identity = FirebaseIdentityAdmin()
    new = build_demo_workspace(
        org_id=args.org,
        name=args.name,
        entity=args.entity,
        trial_ends=args.trial_ends,
        timezone=args.timezone,
        owner=_owner(args.owner),
        now=datetime.now(UTC),
    )
    client = AsyncClient(project=args.project, database=args.database)
    await seed(FirestoreWorkspaceRepository(client), identity, new)
    print(f"Seeded {args.org} ({args.name}); trial ends {new.workspace.subscription.trial_ends_at}")
    print(f"Owner {args.owner} has claims orgId={args.org}, role=owner")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--org", default="org_demo")
    parser.add_argument("--name", default="Sunrise Coffee Roasters")
    parser.add_argument("--entity", choices=["INDIVIDUAL", "COMPANY"], default="COMPANY")
    parser.add_argument("--trial-ends", default="2026-12-31")
    parser.add_argument("--timezone", default="Asia/Jakarta")
    parser.add_argument("--owner", required=True, help="Email of the demo owner")
    parser.add_argument("--project", default=None, help="Defaults to the ADC project")
    parser.add_argument(
        "--database",
        default=os.environ.get("FIRESTORE_DATABASE", "(default)"),
        help="Firestore database (ADR-021: kredibel)",
    )
    asyncio.run(_main(parser.parse_args()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
