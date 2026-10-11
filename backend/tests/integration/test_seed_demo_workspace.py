"""seed_demo_workspace (T013-09, AC-013-4)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from google.cloud.firestore import AsyncClient

from app.adapters.firestore.workspace_repo import FirestoreWorkspaceRepository
from app.adapters.policy_files import load_plans
from app.domain.plans import effective_limits
from app.ports.identity_admin import IdentityUser
from scripts.seed_demo_workspace import DEMO_OVERRIDES, build_demo_workspace, seed
from tests.fakes.identity_admin import FakeIdentityAdmin

PLANS = load_plans(Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml")
OWNER = IdentityUser(uid="u-demo", email="owner@demo.kredibel", email_verified=True)


def test_ac013_4_the_demo_trial_runs_to_the_end_of_31_december_in_jakarta():
    new = build_demo_workspace(
        org_id="org_demo",
        name="Sunrise Coffee Roasters",
        entity="COMPANY",
        trial_ends="2026-12-31",
        timezone="Asia/Jakarta",
        owner=OWNER,
        now=datetime(2026, 10, 11, tzinfo=UTC),
    )

    sub = new.workspace.subscription
    assert sub.trial_ends_at == datetime(2026, 12, 31, 17, 0, tzinfo=UTC)  # 1 Jan 00:00 WIB
    limits = effective_limits(PLANS.plan("free_trial"), sub.limit_overrides)
    assert limits.documents_per_month == 600
    assert limits.extracted_pages_per_month == 3000
    assert limits.month_runs_per_day == 200
    assert limits.ai_spend_usd_per_month == Decimal("40.00")
    assert DEMO_OVERRIDES["aiSpendUsdPerMonth"] == "40.00"
    assert new.owner.uid == "u-demo" and new.owner.role == "owner"


async def test_ac013_4_seeding_is_idempotent_and_sets_the_owner_claims(firestore_emulator):
    db = AsyncClient(project=f"test-{uuid.uuid4().hex[:12]}")
    identity = FakeIdentityAdmin()
    repo = FirestoreWorkspaceRepository(db)
    args = {
        "org_id": "org_demo",
        "name": "Sunrise Coffee Roasters",
        "entity": "COMPANY",
        "trial_ends": "2026-12-31",
        "timezone": "Asia/Jakarta",
        "owner": OWNER,
        "now": datetime(2026, 10, 11, tzinfo=UTC),
    }

    await seed(repo, identity, build_demo_workspace(**args))
    await seed(repo, identity, build_demo_workspace(**args))

    ws = await repo.get_workspace("org_demo")
    assert ws is not None and ws.name == "Sunrise Coffee Roasters"
    assert ws.subscription.limit_overrides == {
        "documentsPerMonth": 600,
        "extractedPagesPerMonth": 3000,
        "monthRunsPerDay": 200,
        "aiSpendUsdPerMonth": "40.00",
    }
    assert identity.claims["u-demo"] == {"orgId": "org_demo", "role": "owner"}
    assert await repo.count_members("org_demo") == 1
    user = (await db.document("system/signup/users/u-demo").get()).to_dict()
    assert user is not None and user["orgId"] == "org_demo"
    signup = (await db.document("system/signup").get()).to_dict()
    assert signup is None, "the seed does not count against MAX_WORKSPACES"
