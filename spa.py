"""Serve embedded frontend/dist or return 503 when the build is missing."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from http_layer.errors import error_body
from store.paths import FRONTEND_DIST

DIST = FRONTEND_DIST


def mount_spa(app: FastAPI) -> None:
    """Mount spa."""
    if not DIST.is_dir():
        @app.get("/{full_path:path}")
        async def frontend_missing(full_path: str, request: Request):
            """Frontend missing."""
            if full_path.startswith("api/") or full_path == "healthz":
                return JSONResponse(status_code=404, content=error_body("not_found", "no such route"))
            return JSONResponse(
                status_code=503,
                content=error_body(
                    "frontend_not_built",
                    "Frontend not built. Run npm run build in frontend/.",
                ),
            )
        return

    assets = DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    index = DIST / "index.html"

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        """Spa fallback."""
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content=error_body("not_found", "no such route"))
        candidate = DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)
