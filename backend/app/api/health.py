"""Health check API router.

Normative references: docs/specs/001-foundation/spec.md AC-001-1 and AC-001-8.
"""

from fastapi import APIRouter

from app.core.settings import Settings


def create_health_router(settings: Settings) -> APIRouter:
    """Create health router reporting service status, version, and role."""
    router = APIRouter(prefix="/api/health", tags=["health"])

    @router.get("")
    async def get_health() -> dict[str, str]:
        return {
            "status": "ok",
            "version": settings.app_version,
            "role": settings.app_role,
        }

    return router
