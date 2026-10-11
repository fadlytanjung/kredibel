"""Single Page Application static file serving and fallback.

Normative reference: docs/specs/001-foundation/tasks.md T001-12 and docs/16 §5.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse


def mount_static_spa(app: FastAPI, static_dir: str = "/app/static") -> None:
    """Mount static directory and add SPA fallback for non-API, non-tasks client-side routes."""
    static_path = Path(static_dir)
    if not static_path.exists() or not static_path.is_dir():
        # Fallback to local dev path if run outside docker
        dev_path = Path(__file__).resolve().parents[3] / "frontend" / "dist"
        if dev_path.exists() and dev_path.is_dir():
            static_path = dev_path
        else:
            return

    index_html = static_path / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        if full_path in ("api", "tasks") or full_path.startswith(("api/", "tasks/")):
            raise HTTPException(status_code=404, detail="Not Found")

        target_file = static_path / full_path
        if target_file.is_file():
            return FileResponse(target_file)
        if index_html.is_file():
            return FileResponse(index_html)
        raise HTTPException(status_code=404, detail="Not Found")
