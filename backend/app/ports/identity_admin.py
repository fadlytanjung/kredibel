"""Server-side identity operations: custom claims and user lookups (spec 013 plan, docs/14 §4)."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class IdentityUser:
    uid: str
    email: str | None
    email_verified: bool
    display_name: str | None = None


class IdentityAdmin(Protocol):
    async def set_claims(self, uid: str, claims: dict[str, str]) -> None:
        """Replace the user's custom claims (orgId, role); the client must refresh its token."""
        ...

    async def get_user(self, uid: str) -> IdentityUser: ...
