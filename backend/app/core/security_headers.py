"""Security headers middleware: CSP, HSTS, content-type, referrer and permissions policies.

Normative reference: docs/14-security-and-compliance.md §8 (values are tested against its table).
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

_CONNECT_SRC = (
    "connect-src 'self' https://*.googleapis.com https://*.firebaseio.com "
    "wss://*.firebaseio.com https://securetoken.googleapis.com "
    "https://identitytoolkit.googleapis.com"
)


def _csp(extra_script_style: str = "") -> str:
    extra = f" {extra_script_style}" if extra_script_style else ""
    return "; ".join(
        [
            "default-src 'self'",
            # Firebase Auth loads the Google API loader from apis.google.com for the popup.
            f"script-src 'self' https://apis.google.com{extra}",
            f"style-src 'self' 'unsafe-inline'{extra}",
            "font-src 'self'",
            "img-src 'self' data: blob:",
            "worker-src 'self' blob:",
            _CONNECT_SRC,
            "frame-src https://*.firebaseapp.com",
            "frame-ancestors 'none'",
        ]
    )


SECURITY_HEADERS: dict[str, str] = {
    "Content-Security-Policy": _csp(),
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(self), microphone=(), geolocation=()",
}

# FastAPI's Swagger UI and ReDoc pull bundles from jsDelivr and initialize via inline script;
# only those pages get the wider policy.
_API_DOCS_CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' https://apis.google.com https://cdn.jsdelivr.net",
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
        "font-src 'self' https://cdn.jsdelivr.net",
        "img-src 'self' data: blob: https://fastapi.tiangolo.com https://cdn.jsdelivr.net",
        "worker-src 'self' blob:",
        f"connect-src 'self' https://cdn.jsdelivr.net {_CONNECT_SRC.removeprefix('connect-src ')}",
        "frame-src https://*.firebaseapp.com",
        "frame-ancestors 'none'",
    ]
)
_API_DOCS_PATHS = ("/docs", "/docs/oauth2-redirect", "/redoc")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware applying the security response headers of docs/14 §8."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        if request.url.path in _API_DOCS_PATHS:
            response.headers["Content-Security-Policy"] = _API_DOCS_CSP
        return response
