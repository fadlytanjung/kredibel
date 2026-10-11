"""Application composition root and router mounting by role.

Normative reference: docs/specs/001-foundation/spec.md AC-001-1, AC-001-10, and docs/13 §1.
"""

from typing import Any

from fastapi import FastAPI

from app.adapters.policy_files import load_plans
from app.api.health import create_health_router
from app.api.me import create_me_router
from app.api.static import mount_static_spa
from app.api.tasks import create_tasks_router
from app.core.auth import TokenVerifier, get_principal_dependency
from app.core.errors import register_error_handlers
from app.core.logging import LoggingMiddleware, setup_logging
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.settings import Settings


def create_app(
    settings: Settings | None = None,
    deps: Any = None,
    token_verifier: TokenVerifier | None = None,
) -> FastAPI:
    """Create and configure FastAPI application instance with role-based routing."""
    active_settings = settings or Settings()

    # Configure structured logging
    setup_logging(
        log_level=active_settings.log_level,
        service=active_settings.service_name,
        version=active_settings.app_version,
    )

    # AC-013-5: an invalid plan catalog stops the process before it serves anything.
    plans = load_plans(active_settings.contract_path(active_settings.plans_file))

    app = FastAPI(
        title="Kredibel API",
        version=active_settings.app_version,
        docs_url="/docs" if active_settings.app_role != "worker" else None,
        redoc_url=None,
    )

    app.state.plans = plans

    # Middleware pipeline
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(LoggingMiddleware, project_id=active_settings.google_cloud_project)

    # RFC 9457 Problem Details error handling
    register_error_handlers(app)

    # Authentication dependency
    principal_dep = get_principal_dependency(verifier=token_verifier)

    # 1. Health check endpoint (always present on all roles)
    app.include_router(create_health_router(active_settings))

    # 2. Web role endpoints
    if active_settings.app_role in ("web", "all"):
        app.include_router(create_me_router(principal_dep))

    # 3. Worker role endpoints
    if active_settings.app_role in ("worker", "all"):
        app.include_router(create_tasks_router())

    # 4. The SPA catch-all matches every path, so it must be registered after every router.
    if active_settings.app_role in ("web", "all"):
        mount_static_spa(app, static_dir=active_settings.static_dir)

    return app


# Default app instance for ASGI servers (Uvicorn)
app = create_app()
