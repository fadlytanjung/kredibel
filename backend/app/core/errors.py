"""RFC 9457 Problem Details error handling.

Normative references: docs/10-api-contract.md §3, docs/13 §2.4, spec 001 AC-001-5.
"""

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

_log = structlog.get_logger()


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


class AlreadyInWorkspaceError(DomainError):
    """Creating a workspace or accepting an invite while already in one (409, docs/10 §3)."""

    def __init__(self, org_id: str | None = None) -> None:
        super().__init__(
            code="ALREADY_IN_WORKSPACE",
            status=409,
            title="Already in a workspace",
            detail="You already have a workspace. Refresh your session to open it.",
        )
        self.org_id = org_id


class SignupClosedError(DomainError):
    """SIGNUP_MODE is closed or invite-only, or MAX_WORKSPACES is reached (403, docs/10 §3)."""

    def __init__(self) -> None:
        super().__init__(
            code="SIGNUP_CLOSED",
            status=403,
            title="Sign-up is closed",
            detail="New workspaces cannot be created right now.",
        )


class ValidationProblem(DomainError):
    """A business-level validation failure, shaped like the 422 for invalid request bodies."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            status=422,
            title="Validation error",
            detail="The request is not valid.",
            extras={"errors": [{"field": field, "message": message}]},
        )


class NotFoundError(DomainError):
    """Raised when a requested resource does not exist (404)."""

    def __init__(self, detail: str = "Resource not found", code: str = "NOT_FOUND") -> None:
        super().__init__(code=code, status=404, title="Not found", detail=detail)


class ConflictError(DomainError):
    """Raised when a resource state conflicts with the requested action (409)."""

    def __init__(self, detail: str = "Resource state conflict", code: str = "CONFLICT") -> None:
        super().__init__(code=code, status=409, title="Conflict", detail=detail)


_HTTP_CODES: dict[int, tuple[str, str]] = {
    404: ("NOT_FOUND", "Not found"),
    405: ("METHOD_NOT_ALLOWED", "Method not allowed"),
}


def _problem(status: int, code: str, title: str, detail: str, **extra: Any) -> JSONResponse:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
        **extra,
    }
    return JSONResponse(status_code=status, content=body, media_type="application/problem+json")


def register_error_handlers(app: FastAPI) -> None:
    """Register RFC 9457 exception handlers on the FastAPI application (docs/10 §3)."""

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content=exc.to_problem(),
            media_type="application/problem+json",
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Router-level errors (unknown path, wrong method) speak the same problem+json as ours.
        code, title = _HTTP_CODES.get(exc.status_code, ("INTERNAL", "HTTP error"))
        return _problem(exc.status_code, code, title, title)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Only field and message: echoing the input could return an account number to a log or
        # a screen, and pydantic's ctx objects are not JSON-serializable.
        errors = [
            {"field": ".".join(str(part) for part in err.get("loc", ())), "message": err["msg"]}
            for err in exc.errors()
        ]
        return _problem(
            422, "VALIDATION_ERROR", "Validation error", "The request is not valid.", errors=errors
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        _log.exception("unhandled_error", path=request.url.path)
        return _problem(500, "INTERNAL", "Internal error", "An unexpected error occurred.")
