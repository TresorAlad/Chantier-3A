"""Non-API browser paths: API-only (no bundled frontend/dist)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from http_layer.errors import error_body


def mount_spa(app: FastAPI) -> None:
    """Register root and catch-all routes; UI is served by Vite dev or a separate static host."""
    @app.get("/")
    async def api_root():
        """Identify this host as the billetterie API."""
        return {
            "service": "Chantier 3A Billetterie API",
            "health": "/healthz",
            "api_prefix": "/api",
        }

    @app.get("/{full_path:path}")
    async def frontend_not_served(full_path: str):
        """Browser UI is not served from this process."""
        if full_path.startswith("api/") or full_path == "healthz":
            return JSONResponse(status_code=404, content=error_body("not_found", "no such route"))
        return JSONResponse(
            status_code=404,
            content=error_body(
                "frontend_not_served",
                "Interface web non servie par l'API. En dev : npm run dev dans frontend/.",
            ),
        )
