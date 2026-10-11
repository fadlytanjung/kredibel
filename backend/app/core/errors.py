"""RFC 9457 Problem Details error handling.

Normative references: docs/10-api-contract.md §3, docs/13 §2.4, spec 001 AC-001-5.
"""

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.errors import (
    AlreadyInWorkspaceError,
    BankAccountExistsError,
    DocumentTooLargeError,
    DomainError,
    EncryptedDocumentError,
    ForbiddenError,
    LanguageNotAvailableError,
    NotFoundError,
    PlanLimitReachedError,
    RunQuotaExceededError,
    SignupClosedError,
    TooManyPagesError,
    TooManyRowsError,
    TrialExpiredError,
    UnauthenticatedError,
    UnsupportedMediaTypeError,
    ValidationProblem,
    WorkspaceRequiredError,
)

_log = structlog.get_logger()

__all__ = [
    "AlreadyInWorkspaceError",
    "BankAccountExistsError",
    "DocumentTooLargeError",
    "DomainError",
    "EncryptedDocumentError",
    "ForbiddenError",
    "LanguageNotAvailableError",
    "NotFoundError",
    "PlanLimitReachedError",
    "RunQuotaExceededError",
    "SignupClosedError",
    "TooManyPagesError",
    "TooManyRowsError",
    "TrialExpiredError",
    "UnauthenticatedError",
    "UnsupportedMediaTypeError",
    "ValidationProblem",
    "WorkspaceRequiredError",
    "register_error_handlers",
]


_HTTP_CODES: dict[int, tuple[str, str]] = {
    404: ("NOT_FOUND", "Not found"),
    405: ("METHOD_NOT_ALLOWED", "Method not allowed"),
    415: ("UNSUPPORTED_MEDIA_TYPE", "Unsupported media type"),
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
