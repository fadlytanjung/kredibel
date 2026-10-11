"""Single Page Application static file serving and fallback.

Normative reference: docs/specs/001-foundation/tasks.md T001-12 and docs/16 §5.
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import NotFoundError

# Vite emits content-hashed file names under assets/, so they can be cached forever.
_HASHED_ASSETS_PREFIX = "assets/"
_LONG_CACHE = "public, max-age=31536000, immutable"
_NO_CACHE = "no-cache"


def mount_static_spa(app: FastAPI, static_dir: str = "/app/static") -> None:
    """Mount static directory and add SPA fallback for non-API, non-tasks client-side routes."""
    static_path = Path(static_dir)
    if not static_path.is_dir():
        # Fallback to local dev path if run outside docker
        dev_path = Path(__file__).resolve().parents[3] / "frontend" / "dist"
        if not dev_path.is_dir():
            return
        static_path = dev_path

    root = static_path.resolve()
    index_html = root / "index.html"

    @app.api_route(
        "/{full_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
        include_in_schema=False,
    )
    async def spa_fallback(request: Request, full_path: str) -> FileResponse:
        if full_path in ("api", "tasks") or full_path.startswith(("api/", "tasks/")):
            raise NotFoundError()
        if request.method not in ("GET", "HEAD"):
            raise StarletteHTTPException(status_code=405, detail="Method Not Allowed")

        # The path arrives percent-decoded, so "..%2F" is a real "../" here: resolve and
        # require the result to stay inside the static root, or any container file is readable.
        target_file = (root / full_path).resolve()
        if target_file.is_relative_to(root) and target_file.is_file():
            cache = _LONG_CACHE if full_path.startswith(_HASHED_ASSETS_PREFIX) else _NO_CACHE
            return FileResponse(target_file, headers={"Cache-Control": cache})
        if index_html.is_file():
            return FileResponse(index_html, headers={"Cache-Control": _NO_CACHE})
        raise NotFoundError()

