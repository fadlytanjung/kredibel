"""Structured JSON logging and request tracing middleware.

Formats logs for Google Cloud Logging, binding trace and span IDs to
`logging.googleapis.com/trace` and `logging.googleapis.com/spanId`.
"""

import logging
import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp


def setup_logging(log_level: str = "INFO", project_id: str = "cloud-hack2skill") -> None:
    """Configure structlog for JSON logging compatible with Cloud Logging."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware binding request ID, trace context, and request latency to structured logs."""

    def __init__(self, app: ASGIApp, project_id: str = "cloud-hack2skill") -> None:
        super().__init__(app)
        self.project_id = project_id
        self.logger = structlog.get_logger()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        trace_header = request.headers.get("X-Cloud-Trace-Context")

        context: dict[str, str] = {"request_id": request_id}
        if trace_header and "/" in trace_header:
            trace_id = trace_header.split("/")[0]
            context["logging.googleapis.com/trace"] = (
                f"projects/{self.project_id}/traces/{trace_id}"
            )

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(**context)

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            response.headers["X-Request-ID"] = request_id
            self.logger.info(
                "request_finished",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=round(elapsed_ms, 2),
            )
            return response
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self.logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error=str(exc),
                duration_ms=round(elapsed_ms, 2),
            )
            raise
