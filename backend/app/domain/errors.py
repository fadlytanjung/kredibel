"""Pure domain error classes (RFC 9457 Problem Details shape).

Normative references: docs/10-api-contract.md §3, docs/13 §2.4.
Domain errors have no dependency on FastAPI or outer frameworks.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any


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


def _number(value: object) -> object:
    # Decimal limits (AI spend) travel as decimal strings, like all money in JSON (docs/10 §1).
    return str(value) if isinstance(value, Decimal) else value


def _limit_extras(limit: str | None, used: object, maximum: object) -> dict[str, Any]:
    return {"limit": limit, "used": _number(used), "max": _number(maximum)}


class PlanLimitReachedError(DomainError):
    def __init__(self, limit: str | None, used: object, maximum: object) -> None:
        super().__init__(
            code="PLAN_LIMIT_REACHED",
            status=403,
            title="Plan limit reached",
            detail=f"This would go over your plan's {limit} limit ({used} of {maximum} used).",
            type_uri="/problems/plan-limit-reached",
            extras=_limit_extras(limit, used, maximum),
        )


class TrialExpiredError(DomainError):
    def __init__(self, trial_ends_at: datetime | None) -> None:
        super().__init__(
            code="TRIAL_EXPIRED",
            status=403,
            title="Trial ended",
            detail="Your free trial has ended. Your books stay readable; new work is paused.",
            extras={"trialEndsAt": trial_ends_at.isoformat()} if trial_ends_at else {},
        )


class DocumentTooLargeError(DomainError):
    def __init__(self, limit: str | None, used: object, maximum: object) -> None:
        super().__init__(
            code="DOCUMENT_TOO_LARGE",
            status=413,
            title="File too large",
            detail=f"The file is {used} MB; the limit is {maximum} MB.",
            extras=_limit_extras(limit, used, maximum),
        )


class TooManyPagesError(DomainError):
    def __init__(self, used: object, maximum: object) -> None:
        super().__init__(
            code="TOO_MANY_PAGES",
            status=422,
            title="Too many pages",
            detail=f"The file has {used} pages; the limit is {maximum} per document.",
            extras={"maxPages": maximum, "splitAvailable": False},
        )


class TooManyRowsError(DomainError):
    def __init__(self, limit: str | None, used: object, maximum: object) -> None:
        super().__init__(
            code="TOO_MANY_ROWS",
            status=422,
            title="Too many rows",
            detail=f"The ledger file has {used} rows; the limit is {maximum}.",
            extras=_limit_extras(limit, used, maximum),
        )


class RunQuotaExceededError(DomainError):
    def __init__(self, used: object, maximum: object, retry_after_seconds: int) -> None:
        super().__init__(
            code="RUN_QUOTA_EXCEEDED",
            status=429,
            title="Too many runs today",
            detail=f"{used} of {maximum} month reconciliations used today.",
            extras={
                **_limit_extras("monthRunsPerDay", used, maximum),
                "retryAfterSeconds": retry_after_seconds,
            },
        )


class LanguageNotAvailableError(DomainError):
    def __init__(self, language: str) -> None:
        super().__init__(
            code="LANGUAGE_NOT_AVAILABLE",
            status=422,
            title="Language coming soon",
            detail=f"{language} is coming soon; English is the only language today.",
        )


class BankAccountExistsError(DomainError):
    def __init__(self, account_id: str) -> None:
        super().__init__(
            code="BANK_ACCOUNT_EXISTS",
            status=409,
            title="Bank account already added",
            detail="This account is already in the workspace.",
            extras={"accountId": account_id},
        )


class NotFoundError(DomainError):
    """Raised when a requested resource does not exist (404)."""

    def __init__(self, detail: str = "Resource not found", code: str = "NOT_FOUND") -> None:
        super().__init__(code=code, status=404, title="Not found", detail=detail)


class UnsupportedMediaTypeError(DomainError):
    """Raised when file content type is not supported (415, AC-003-2)."""

    def __init__(
        self,
        detail: str = "Only PDF, PNG, JPEG, CSV and XLSX files are supported.",
    ) -> None:
        super().__init__(
            code="UNSUPPORTED_MEDIA_TYPE",
            status=415,
            title="Unsupported media type",
            detail=detail,
        )


class UploadInProgressError(DomainError):
    """The same content is still being stored by another upload (409, docs/10 §3)."""

    def __init__(self) -> None:
        super().__init__(
            code="UPLOAD_IN_PROGRESS",
            status=409,
            title="Upload in progress",
            detail="This file is still being uploaded. Try again in a minute.",
        )


class EncryptedDocumentError(DomainError):
    """Raised when a PDF is password protected / encrypted (422, AC-003-3)."""

    def __init__(
        self,
        detail: str = (
            "Password-protected PDFs cannot be read. Remove the password and upload again."
        ),
    ) -> None:
        super().__init__(
            code="ENCRYPTED_DOCUMENT",
            status=422,
            title="Password-protected document",
            detail=detail,
        )


class RunsDisabledError(DomainError):
    """Raised when runs are disabled globally via RUNS_ENABLED=false (503, AC-004-10)."""

    def __init__(
        self,
        detail: str = "Background runs are currently disabled.",
        code: str = "RUNS_DISABLED",
    ) -> None:
        super().__init__(
            code=code,
            status=503,
            title="Runs disabled",
            detail=detail,
        )


class QueueUnavailableError(DomainError):
    """A task could not be queued (503): the work is not silently dropped (docs/10 §3)."""

    def __init__(
        self, detail: str = "The reading task could not be queued. Try again shortly."
    ) -> None:
        super().__init__(
            code="QUEUE_UNAVAILABLE", status=503, title="Queue unavailable", detail=detail
        )


class AlreadyMatchedError(DomainError):
    """Raised when a bank line or document is already matched in an active match (409)."""

    def __init__(self, record_id: str, match_id: str) -> None:
        super().__init__(
            code="ALREADY_MATCHED",
            status=409,
            title="Already matched",
            detail=f"Record {record_id} is already matched in {match_id}.",
            extras={"recordId": record_id, "matchId": match_id},
        )


class ToleranceExceededError(DomainError):
    """Raised when the difference between amounts exceeds the reconciliation tolerance (422)."""

    def __init__(self, difference: Decimal, max_tolerance: Decimal) -> None:
        super().__init__(
            code="TOLERANCE_EXCEEDED",
            status=422,
            title="Difference exceeds tolerance",
            detail=f"Amount difference {difference} exceeds the allowed tolerance {max_tolerance}.",
            extras={"difference": str(difference), "maxTolerance": str(max_tolerance)},
        )
