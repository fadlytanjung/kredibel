"""RFC 9457 Problem Details error handling.

Normative reference: docs/specs/001-foundation/spec.md AC-001-5 and plan.md.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Base class for all domain errors rendered as RFC 9457 problem details."""

    def __init__(
        self,
        code: str,
        status: int,
        title: str,
        detail: str | None = None,
        type_uri: str = "about:blank",
        extras: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail or title)
        self.code = code
        self.status = status
        self.title = title
        self.detail = detail or title
        self.type_uri = type_uri
        self.extras = extras or {}

    def to_problem(self) -> dict[str, Any]:
        """Convert error to RFC 9457 problem details representation."""
        problem: dict[str, Any] = {
            "type": self.type_uri,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "code": self.code,
        }
        problem.update(self.extras)
        return problem


class UnauthenticatedError(DomainError):
    """Raised when no or invalid authentication credentials are provided (401)."""

    def __init__(
        self, detail: str = "Authentication required", code: str = "UNAUTHENTICATED"
    ) -> None:
        super().__init__(code=code, status=401, title="Unauthorized", detail=detail)


class ForbiddenError(DomainError):
    """Raised when the user is authenticated but not authorized (403)."""

    def __init__(self, detail: str = "Access forbidden", code: str = "FORBIDDEN") -> None:
        super().__init__(code=code, status=403, title="Forbidden", detail=detail)


class WorkspaceRequiredError(DomainError):
    """Raised when accessing a workspace-scoped route without an orgId claim (403)."""

    def __init__(
        self,
        detail: str = "Workspace selection required",
        code: str = "WORKSPACE_REQUIRED",
    ) -> None:
        super().__init__(code=code, status=403, title="Workspace required", detail=detail)


class NotFoundError(DomainError):
    """Raised when a requested resource does not exist (404)."""

    def __init__(self, detail: str = "Resource not found", code: str = "NOT_FOUND") -> None:
        super().__init__(code=code, status=404, title="Not found", detail=detail)


class ConflictError(DomainError):
    """Raised when a resource state conflicts with the requested action (409)."""

    def __init__(self, detail: str = "Resource state conflict", code: str = "CONFLICT") -> None:
        super().__init__(code=code, status=409, title="Conflict", detail=detail)


def register_error_handlers(app: FastAPI) -> None:
    """Register RFC 9457 exception handlers on the FastAPI application."""

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content=exc.to_problem(),
            media_type="application/problem+json",
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        problem = {
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "detail": str(exc.errors()),
            "code": "VALIDATION_ERROR",
            "errors": exc.errors(),
        }
        return JSONResponse(
            status_code=422,
            content=problem,
            media_type="application/problem+json",
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        problem = {
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred.",
            "code": "INTERNAL_SERVER_ERROR",
        }
        return JSONResponse(
            status_code=500,
            content=problem,
            media_type="application/problem+json",
        )
