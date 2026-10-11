"""Plans, workspace and bank-account routes (T013-08, AC-013-1, -2, -6, -14, -15)."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.adapters.policy_files import load_plans
from app.core.settings import Settings
from app.main import AppDeps, create_app
from tests.fakes.clock import FixedClock
from tests.fakes.identity_admin import FakeIdentityAdmin
from tests.fakes.usage_repository import FakeUsageRepository
from tests.fakes.workspace_repository import FakeWorkspaceRepository
from tests.unit.test_auth import FakeTokenVerifier

PLANS_FILE = Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml"
NOW = datetime(2026, 10, 11, 8, 0, tzinfo=UTC)

CREATE = {
    "name": "Synthetic Roasters Ltd",
    "entityType": "COMPANY",
    "profile": {"industry": "Food and drink"},
    "taxId": "01.234.567.8-901.000",
    "timezone": "Asia/Jakarta",
    "bankAccounts": [
        {"bankName": "Bank Sintetis", "accountNumber": "123-456-4821", "holderName": "SR Ltd"}
    ],
}


class Harness:
    def __init__(self, signup_mode: str = "open") -> None:
        self.workspaces = FakeWorkspaceRepository()
        self.usage = FakeUsageRepository(workspaces=self.workspaces)
        self.identity = FakeIdentityAdmin()
        self.tokens = FakeTokenVerifier({"new": {"uid": "u-1", "email": "owner@example.test"}})
        settings = Settings(app_role="web", signup_mode=signup_mode)  # type: ignore[arg-type]
        deps = AppDeps(
            settings,
            load_plans(PLANS_FILE),
            workspace_repo=self.workspaces,
            usage_repo=self.usage,
            identity=self.identity,
            clock=FixedClock(NOW),
            token_verifier=self.tokens,
        )
        self.app = create_app(settings, deps=deps)

    def client(self) -> AsyncClient:
        return AsyncClient(transport=ASGITransport(app=self.app), base_url="http://test")

    async def onboard(self, client: AsyncClient) -> str:
        res = await client.post("/api/workspaces", json=CREATE, headers=self.auth("new"))
        assert res.status_code == 201, res.text
        org_id = res.json()["orgId"]
        # What the refreshed ID token carries after the server set the claims.
        self.tokens.valid_tokens["owner"] = {
            "uid": "u-1",
            "email": "owner@example.test",
            **self.identity.claims["u-1"],
        }
        return org_id

    @staticmethod
    def auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def h() -> Harness:
    return Harness()


async def test_ac013_6_plans_in_file_order_with_coming_soon_and_languages(h):
    async with h.client() as c:
        res = await c.get("/api/plans", headers=h.auth("new"))

    assert res.status_code == 200
    body = res.json()
    assert [p["id"] for p in body["plans"]] == [
        "free_trial",
        "starter",
        "professional",
        "enterprise",
    ]
    assert [p["status"] for p in body["plans"]] == ["AVAILABLE"] + ["COMING_SOON"] * 3
    assert body["plans"][0]["limits"]["aiSpendUsdPerMonth"] == "5.00"
    assert "limits" not in body["plans"][1]
    assert [f["id"] for f in body["comingSoonFeatures"]] == ["loan_readiness_report", "bank_feeds"]
    assert {"code": "id", "label": "Bahasa Indonesia", "status": "coming_soon"} in body["languages"]


async def test_ac013_2_create_returns_201_with_the_trial_and_sets_claims(h):
    async with h.client() as c:
        res = await c.post("/api/workspaces", json=CREATE, headers=h.auth("new"))

    assert res.status_code == 201
    body = res.json()
    assert body["entityType"] == "COMPANY"
    assert body["currency"] == "IDR"
    assert body["subscription"]["status"] == "TRIALING"
    assert body["subscription"]["trialDaysLeft"] == 30
    assert body["subscription"]["limits"]["documentsPerMonth"] == 150
    assert body["profile"]["taxIdMasked"] == "••••.000"
    assert "schemaVersion" not in res.text
    assert h.identity.claims["u-1"] == {"orgId": body["orgId"], "role": "owner"}


async def test_ac013_2_an_invalid_body_is_a_422_with_fields(h):
    async with h.client() as c:
        res = await c.post(
            "/api/workspaces", json={**CREATE, "entityType": "TRUST"}, headers=h.auth("new")
        )

    assert res.status_code == 422
    assert res.json()["code"] == "VALIDATION_ERROR"
    assert res.json()["errors"][0]["field"] == "body.entityType"


async def test_ac013_3_signup_closed():
    h = Harness(signup_mode="closed")
    async with h.client() as c:
        res = await c.post("/api/workspaces", json=CREATE, headers=h.auth("new"))

    assert res.status_code == 403
    assert res.json()["code"] == "SIGNUP_CLOSED"


async def test_ac013_3_creating_again_with_the_claim_is_409(h):
    async with h.client() as c:
        await h.onboard(c)
        res = await c.post("/api/workspaces", json=CREATE, headers=h.auth("owner"))

    assert res.status_code == 409
    assert res.json()["code"] == "ALREADY_IN_WORKSPACE"


async def test_ac013_12_me_carries_the_workspace_summary(h):
    async with h.client() as c:
        org_id = await h.onboard(c)
        res = await c.get("/api/me", headers=h.auth("owner"))

    body = res.json()
    assert body["orgId"] == org_id
    assert body["needsWorkspace"] is False
    assert body["workspace"] == {
        "name": "Synthetic Roasters Ltd",
        "entityType": "COMPANY",
        "planId": "free_trial",
        "subscriptionStatus": "TRIALING",
        "trialDaysLeft": 30,
    }


async def test_ac013_11_workspace_has_subscription_limits_and_usage(h):
    async with h.client() as c:
        await h.onboard(c)
        res = await c.get("/api/workspace", headers=h.auth("owner"))

    body = res.json()
    assert body["subscription"]["limits"]["extractedPagesPerMonth"] == 400
    assert body["usage"] == {
        "month": "2026-10",
        "documentsUploaded": 0,
        "extractedPages": 0,
        "monthRunsToday": 0,
        "assistantQuestionsToday": 0,
        "aiSpendUsd": "0",
        "seatsUsed": 1,
    }
    assert body["learning"] == {"shareVerifiedLabels": False}


async def test_ac013_14_patch_updates_the_profile_and_masks_the_tax_id(h):
    async with h.client() as c:
        await h.onboard(c)
        res = await c.patch(
            "/api/workspace",
            json={
                "profile": {"tradingName": "SR", "aliases": ["S. Roasters"]},
                "taxId": "9988776655",
            },
            headers=h.auth("owner"),
        )

    assert res.status_code == 200
    profile = res.json()["profile"]
    assert profile["tradingName"] == "SR"
    assert profile["industry"] == "Food and drink"
    assert profile["taxIdMasked"] == "••••6655"


async def test_ac013_14_the_entity_type_cannot_change(h):
    async with h.client() as c:
        await h.onboard(c)
        res = await c.patch(
            "/api/workspace", json={"entityType": "INDIVIDUAL"}, headers=h.auth("owner")
        )

    assert res.status_code == 422


@pytest.mark.parametrize(
    ("language", "code"), [("id", "LANGUAGE_NOT_AVAILABLE"), ("xx", "VALIDATION_ERROR")]
)
async def test_ac013_15_only_english_can_be_selected(h, language, code):
    async with h.client() as c:
        await h.onboard(c)
        res = await c.patch(
            "/api/workspace", json={"defaultLanguage": language}, headers=h.auth("owner")
        )

    assert res.status_code == 422
    assert res.json()["code"] == code


async def test_ac013_14_bank_accounts_list_add_update_delete(h):
    async with h.client() as c:
        await h.onboard(c)
        listed = (await c.get("/api/bank-accounts", headers=h.auth("owner"))).json()["items"]
        added = await c.post(
            "/api/bank-accounts",
            json={"bankName": "Bank Dua", "accountNumber": "9876-5432-10", "holderName": "SR Ltd"},
            headers=h.auth("owner"),
        )
        account_id = added.json()["accountId"]
        again = await c.post(
            "/api/bank-accounts",
            json={"bankName": "Bank Dua", "accountNumber": "9876543210", "holderName": "SR Ltd"},
            headers=h.auth("owner"),
        )
        patched = await c.patch(
            f"/api/bank-accounts/{account_id}",
            json={"nickname": "Payroll", "ledgerAccountCode": "1-1002"},
            headers=h.auth("owner"),
        )
        deleted = await c.delete(f"/api/bank-accounts/{account_id}", headers=h.auth("owner"))
        missing = await c.delete(f"/api/bank-accounts/{account_id}", headers=h.auth("owner"))
        after = (await c.get("/api/bank-accounts", headers=h.auth("owner"))).json()["items"]

    assert [a["accountMasked"] for a in listed] == ["••••4821"]
    assert added.status_code == 201 and added.json()["accountMasked"] == "••••3210"
    assert "9876543210" not in added.text
    assert again.status_code == 409 and again.json()["code"] == "BANK_ACCOUNT_EXISTS"
    assert patched.json()["nickname"] == "Payroll"
    assert patched.json()["ledgerAccountCode"] == "1-1002"
    assert deleted.status_code == 204
    assert missing.status_code == 404 and missing.json()["code"] == "NOT_FOUND"
    assert [a["accountMasked"] for a in after] == ["••••4821"]


async def test_ac013_1_me_with_a_claim_for_a_missing_workspace_needs_one(h):
    h.tokens.valid_tokens["stale"] = {"uid": "u-1", "orgId": "org_gone", "role": "owner"}
    async with h.client() as c:
        res = await c.get("/api/me", headers=h.auth("stale"))

    body = res.json()
    assert body["needsWorkspace"] is True
    assert body["orgId"] is None
    assert body["workspace"] is None
