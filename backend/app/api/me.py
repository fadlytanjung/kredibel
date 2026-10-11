"""User identity API endpoint returning principal claims and workspace status.

Normative reference: docs/specs/001-foundation/spec.md AC-001-4 and AC-001-6.
"""

from typing import Any

from fastapi import APIRouter, Depends

from app.core.auth import Principal


def create_me_router(principal_dep: Any) -> APIRouter:
    """Create /api/me router using the provided Principal dependency."""
    router = APIRouter(prefix="/api/me", tags=["me"])

    @router.get("")
    async def get_me(principal: Principal = Depends(principal_dep)) -> dict[str, Any]:
        return {
            "uid": principal.uid,
            "email": principal.email,
            "displayName": principal.display_name,
            "orgId": principal.org_id,
            "role": principal.role,
            "needsWorkspace": principal.needs_workspace,
            "language": "en",
        }

    return router
