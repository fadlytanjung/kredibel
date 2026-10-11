"""Structured JSON logging in the Cloud Logging shape and request tracing middleware.

Normative reference: docs/17-observability.md §3 (every line has severity, message, service,
version and the trace field), spec 001 non-functional requirements.
"""

import logging
import time
import uuid
from collections.abc import MutableMapping
from typing import Any

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

TRACE_FIELD = "logging.googleapis.com/trace"


def _cloud_logging_fields(
    _logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Rename structlog's keys to the ones Cloud Logging reads (severity, message)."""
    event_dict["severity"] = str(event_dict.pop("level", method_name)).upper()
    event_dict["message"] = event_dict.pop("event", "")
    return event_dict


def setup_logging(log_level: str = "INFO", service: str = "kredibel", version: str = "dev") -> None:
    """Configure structlog for JSON lines that Cloud Logging parses into structured entries."""

    def add_service(
        _logger: Any, _name: str, event_dict: MutableMapping[str, Any]
    ) -> MutableMapping[str, Any]:
        event_dict.setdefault("service", service)
        event_dict.setdefault("version", version)
        return event_dict

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
            add_service,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            _cloud_logging_fields,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


def _trace_id(request: Request) -> str | None:
    """Trace ID from W3C traceparent (current Cloud Run) or X-Cloud-Trace-Context (legacy)."""
    traceparent = request.headers.get("traceparent")
    if traceparent:
        parts = traceparent.split("-")
        if len(parts) >= 3 and len(parts[1]) == 32:
            return parts[1]
    legacy = request.headers.get("X-Cloud-Trace-Context")
    if legacy:
        trace_id = legacy.split("/", 1)[0]
        return trace_id or None
    return None


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware binding request ID, trace context, and request latency to structured logs."""

    def __init__(self, app: ASGIApp, project_id: str) -> None:
        super().__init__(app)
        self.project_id = project_id
        self.logger = structlog.get_logger()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        context: dict[str, str] = {"requestId": request_id}
        trace_id = _trace_id(request)
        if trace_id:
            context[TRACE_FIELD] = f"projects/{self.project_id}/traces/{trace_id}"

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(**context)

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            self.logger.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                durationMs=round((time.perf_counter() - start_time) * 1000, 2),
            )
            raise

        response.headers["X-Request-ID"] = request_id
        self.logger.info(
            "request_finished",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            durationMs=round((time.perf_counter() - start_time) * 1000, 2),
        )
        return response
