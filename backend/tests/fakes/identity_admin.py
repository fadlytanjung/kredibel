"""In-memory IdentityAdmin for tests."""

from app.ports.identity_admin import IdentityAdmin, IdentityUser


class FakeIdentityAdmin(IdentityAdmin):
    def __init__(self, users: dict[str, IdentityUser] | None = None) -> None:
        self.users = users or {}
        self.claims: dict[str, dict[str, str]] = {}
        self.fail_next_set_claims = False

    async def set_claims(self, uid: str, claims: dict[str, str]) -> None:
        if self.fail_next_set_claims:
            self.fail_next_set_claims = False
            raise RuntimeError("identity service unavailable")
        self.claims[uid] = dict(claims)

    async def get_user(self, uid: str) -> IdentityUser:
        return self.users.get(uid, IdentityUser(uid=uid, email=None, email_verified=False))
