"""WorkspaceService.create (T013-06, AC-013-2, AC-013-3)."""

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.adapters.policy_files import load_plans
from app.core.auth import Principal
from app.core.errors import AlreadyInWorkspaceError, SignupClosedError, ValidationProblem
from app.domain.accounts import account_hash
from app.domain.models.workspace import WorkspaceCreate, WorkspaceUpdate
from app.services.workspace_service import WorkspaceService
from tests.fakes.clock import FixedClock
from tests.fakes.identity_admin import FakeIdentityAdmin
from tests.fakes.workspace_repository import FakeWorkspaceRepository

PLANS = load_plans(Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml")
NOW = datetime(2026, 10, 11, 8, 0, tzinfo=UTC)
NEW_USER = Principal(uid="u-1", email="owner@example.test", display_name="Demo Owner")

COMPANY = WorkspaceCreate.model_validate(
    {
        "name": "Synthetic Roasters Ltd",
        "entityType": "COMPANY",
        "profile": {"tradingName": "Synthetic Roasters", "industry": "Food and drink"},
        "timezone": "Asia/Jakarta",
        "bankAccounts": [
            {"bankName": "Bank Sintetis", "accountNumber": "123-456-4821", "holderName": "SR Ltd"}
        ],
    }
)


def _service(
    repo: FakeWorkspaceRepository | None = None,
    identity: FakeIdentityAdmin | None = None,
    signup_mode: str = "open",
    max_workspaces: int = 15,
) -> tuple[WorkspaceService, FakeWorkspaceRepository, FakeIdentityAdmin]:
    repo = repo or FakeWorkspaceRepository()
    identity = identity or FakeIdentityAdmin()
    service = WorkspaceService(
        repo=repo,
        identity=identity,
        plans=PLANS,
        clock=FixedClock(NOW),
        signup_mode=signup_mode,  # type: ignore[arg-type]
        max_workspaces=max_workspaces,
    )
    return service, repo, identity


async def test_ac013_2_a_company_gets_its_workspace_trial_owner_and_account():
    service, repo, identity = _service()

    workspace = await service.create(NEW_USER, COMPANY)

    org = repo.workspaces[workspace.org_id]
    assert workspace.org_id.startswith("org_")
    assert org.entity_type == "COMPANY"
    assert org.profile.legal_name == "Synthetic Roasters Ltd"
    assert org.profile.trading_name == "Synthetic Roasters"
    assert (org.currency, org.default_language, org.country) == ("IDR", "en", "ID")
    assert org.subscription.plan_id == "free_trial"
    assert org.subscription.status == "TRIALING"
    assert org.subscription.trial_ends_at == NOW + timedelta(days=30)
    assert repo.members[workspace.org_id]["u-1"].role == "owner"
    assert repo.workspaces_created == 1
    assert identity.claims["u-1"] == {"orgId": workspace.org_id, "role": "owner"}


async def test_ac013_2_the_bank_account_is_stored_masked_with_a_private_hash():
    service, repo, _ = _service()

    workspace = await service.create(NEW_USER, COMPANY)

    [account] = repo.bank_accounts[workspace.org_id].values()
    assert account.account_masked == "••••4821"
    assert account.account_id.startswith("acc_")
    assert "1234564821" not in account.model_dump_json()
    assert repo.account_hashes[workspace.org_id][account.account_id] == account_hash(
        workspace.org_id, "1234564821"
    )


async def test_ac013_2_creation_is_audited_in_the_same_transaction():
    service, repo, _ = _service()

    workspace = await service.create(NEW_USER, COMPANY)

    types = [event.type for event in repo.events[workspace.org_id]]
    assert types == ["WORKSPACE_CREATED", "BANK_ACCOUNT_ADDED"]
    assert all(event.actor_uid == "u-1" for event in repo.events[workspace.org_id])


async def test_ac013_2_every_new_workspace_is_a_company():
    service, repo, _ = _service()
    business = WorkspaceCreate.model_validate({"name": "Demo Roasters", "timezone": "Asia/Jakarta"})

    workspace = await service.create(NEW_USER, business)

    assert repo.workspaces[workspace.org_id].entity_type == "COMPANY"
    assert repo.workspaces[workspace.org_id].profile.legal_name == "Demo Roasters"
    with pytest.raises(ValidationError):
        WorkspaceCreate.model_validate(
            {"name": "Demo Freelancer", "entityType": "INDIVIDUAL", "timezone": "Asia/Jakarta"}
        )


async def test_ac013_3_a_caller_with_a_workspace_claim_gets_409():
    service, repo, _ = _service()
    existing = await service.create(Principal(uid="u-2"), COMPANY)
    member = Principal(uid="u-2", org_id=existing.org_id, role="owner")

    with pytest.raises(AlreadyInWorkspaceError):
        await service.create(member, COMPANY)
    assert list(repo.workspaces) == [existing.org_id]


async def test_ac013_3_a_double_submit_creates_one_workspace():
    service, repo, identity = _service()

    results = await asyncio.gather(
        service.create(NEW_USER, COMPANY),
        service.create(NEW_USER, COMPANY),
        return_exceptions=True,
    )

    created = [r for r in results if not isinstance(r, BaseException)]
    assert len(created) == 1
    assert isinstance(
        [r for r in results if isinstance(r, BaseException)][0], AlreadyInWorkspaceError
    )
    assert len(repo.workspaces) == 1
    assert identity.claims["u-1"]["orgId"] == created[0].org_id


async def test_ac013_2_lost_claims_are_repaired_on_the_next_attempt():
    identity = FakeIdentityAdmin()
    identity.fail_next_set_claims = True
    service, repo, _ = _service(identity=identity)

    with pytest.raises(RuntimeError):
        await service.create(NEW_USER, COMPANY)
    [org_id] = repo.workspaces
    assert "u-1" not in identity.claims

    with pytest.raises(AlreadyInWorkspaceError):
        await service.create(NEW_USER, COMPANY)
    assert identity.claims["u-1"] == {"orgId": org_id, "role": "owner"}


@pytest.mark.parametrize("mode", ["closed", "invite_only"])
async def test_ac013_3_signup_mode_closes_creation(mode):
    service, repo, _ = _service(signup_mode=mode)

    with pytest.raises(SignupClosedError):
        await service.create(NEW_USER, COMPANY)
    assert repo.workspaces == {}


async def test_ac013_3_max_workspaces_closes_creation():
    service, repo, _ = _service(repo=FakeWorkspaceRepository(workspaces_created=15))

    with pytest.raises(SignupClosedError):
        await service.create(NEW_USER, COMPANY)
    assert repo.workspaces == {}


async def test_ac013_3_two_users_racing_for_the_last_workspace():
    service, repo, _ = _service(repo=FakeWorkspaceRepository(workspaces_created=14))
    other = Principal(uid="u-9", email="other@example.test")

    results = await asyncio.gather(
        service.create(NEW_USER, COMPANY),
        service.create(other, COMPANY),
        return_exceptions=True,
    )

    assert sum(isinstance(r, SignupClosedError) for r in results) == 1
    assert len(repo.workspaces) == 1


async def test_ac013_2_an_unknown_time_zone_is_a_validation_error():
    service, _, _ = _service()
    bad = COMPANY.model_copy(update={"timezone": "Mars/Olympus"})

    with pytest.raises(ValidationProblem) as exc:
        await service.create(NEW_USER, bad)
    assert exc.value.extras["errors"] == [{"field": "timezone", "message": "Unknown time zone"}]


async def test_ac013_2_the_same_account_twice_is_a_validation_error():
    service, _, _ = _service()
    twice = COMPANY.model_copy(update={"bank_accounts": COMPANY.bank_accounts * 2})

    with pytest.raises(ValidationProblem):
        await service.create(NEW_USER, twice)


async def test_ac013_1_a_claim_for_a_missing_workspace_counts_as_none():
    """A stale claim (the workspace was never created or was reset) must not block onboarding."""
    service, repo, identity = _service()
    stale = Principal(uid="u-1", email="owner@example.test", org_id="org_gone", role="owner")

    workspace = await service.create(stale, COMPANY)

    assert workspace.org_id != "org_gone"
    assert identity.claims["u-1"] == {"orgId": workspace.org_id, "role": "owner"}


async def test_ac013_1_a_signup_record_for_a_deleted_workspace_does_not_block():
    service, repo, identity = _service()
    first = await service.create(NEW_USER, COMPANY)
    del repo.workspaces[first.org_id]  # a demo reset removed the workspace

    second = await service.create(NEW_USER, COMPANY)

    assert second.org_id != first.org_id
    assert identity.claims["u-1"]["orgId"] == second.org_id


async def test_ac013_2_the_workspace_books_in_the_currency_chosen_at_onboarding():
    service, repo, _ = _service()

    workspace = await service.create(NEW_USER, COMPANY.model_copy(update={"currency": "MYR"}))

    assert workspace.currency == "MYR"
    assert repo.workspaces[workspace.org_id].currency == "MYR"


def test_adr020_the_currency_cannot_be_patched():
    """Changing the currency after onboarding is coming soon; the PATCH body has no such field."""
    with pytest.raises(ValidationError):
        WorkspaceUpdate.model_validate({"currency": "SGD"})


def test_adr020_only_the_five_currencies():
    with pytest.raises(ValidationError):
        WorkspaceCreate.model_validate({**COMPANY.model_dump(by_alias=True), "currency": "EUR"})
