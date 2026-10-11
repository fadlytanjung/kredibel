"""Firebase token authentication and Principal identity.

Normative references: docs/specs/001-foundation/spec.md AC-001-4, AC-001-5, and docs/14 §3.
"""

from collections.abc import Callable, Coroutine
from typing import Any, Protocol

from fastapi import Header
from pydantic import BaseModel

from app.core.errors import UnauthenticatedError, WorkspaceRequiredError


class Principal(BaseModel):
    """Authenticated user context derived from verified Firebase ID token claims."""

    uid: str
    email: str | None = None
    display_name: str | None = None
    org_id: str | None = None
    role: str | None = None

    @property
    def needs_workspace(self) -> bool:
        """True when the user is signed in but has not created or joined a workspace."""
        return self.org_id is None


class TokenVerifier(Protocol):
    """Protocol for verifying authentication tokens."""

    def verify_token(self, token: str) -> dict[str, Any]:
        """Verify token and return decoded claims dictionary or raise ValueError."""
        ...


class FirebaseTokenVerifier:
    """Production verifier validating Firebase ID tokens via the Firebase Admin SDK."""

    def verify_token(self, token: str) -> dict[str, Any]:
        import firebase_admin.auth

        try:
            return firebase_admin.auth.verify_id_token(token)
        except Exception as exc:
            raise ValueError(f"Failed to verify Firebase token: {exc}") from exc


_default_verifier: TokenVerifier = FirebaseTokenVerifier()


def get_principal_dependency(
    verifier: TokenVerifier | None = None,
) -> Callable[..., Coroutine[Any, Any, Principal]]:
    """Factory creating an authenticated Principal FastAPI dependency with injectable verifier."""
    active_verifier = verifier or _default_verifier

    async def verify_request(
        authorization: str | None = Header(None, alias="Authorization"),
    ) -> Principal:
        if not authorization or not authorization.startswith("Bearer "):
            raise UnauthenticatedError(detail="Missing or malformed Authorization header")

        token = authorization[len("Bearer ") :].strip()
        if not token:
            raise UnauthenticatedError(detail="Empty bearer token")

        try:
            claims = active_verifier.verify_token(token)
        except Exception as exc:
            raise UnauthenticatedError(detail=f"Invalid or expired token: {exc}") from exc

        uid = claims.get("uid") or claims.get("sub") or claims.get("user_id")
        if not uid:
            raise UnauthenticatedError(detail="Token missing uid claim")

        return Principal(
            uid=str(uid),
            email=claims.get("email"),
            display_name=claims.get("name"),
            org_id=claims.get("orgId"),
            role=claims.get("role"),
        )

    return verify_request


def require_workspace(
    principal_dep: Callable[..., Coroutine[Any, Any, Principal]],
) -> Callable[..., Coroutine[Any, Any, Principal]]:
    """Dependency wrapper requiring the authenticated Principal to have an orgId claim."""

    async def guard(
        authorization: str | None = Header(None, alias="Authorization"),
    ) -> Principal:
        principal = await principal_dep(authorization=authorization)
        if principal.org_id is None:
            raise WorkspaceRequiredError(
                detail="A workspace (orgId) claim is required to access this resource."
            )
        return principal

    return guard
