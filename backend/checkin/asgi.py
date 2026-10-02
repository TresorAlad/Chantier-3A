"""Standalone ASGI application of the check-in module (deployment without the 3A middleware).

    CHECKIN_DATABASE_URL=postgresql://... uvicorn checkin.asgi:app --workers 4

It serves only ``/api/checkin/*``. It does not use the 3A ``session_middleware`` nor the 3A
``Store`` connection, so it is unaffected by the shared-connection defects described in
``docs/checkin/BUGS_3A.md``. Each worker process owns its own pool: total connections are
``workers x CHECKIN_DB_POOL_MAX``. Authentication: ``Authorization: Bearer`` (3A session token);
cookie sessions are refused unless a CSRF secret is provided to the adapter.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from checkin.runtime import Runtime, build_runtime
from http_layer.routes import checkin as checkin_routes


def _default_runtime() -> Runtime:
    """Runtime with the 3A configuration: its JWT secret (CHANTIER3A_SECRET_KEY) must be the one of the 3A API."""
    from config import load_config

    cfg3a = load_config()
    return build_runtime(database_url=cfg3a.database_url, session_secret=cfg3a.session_secret, config3a=cfg3a)


def create_standalone_app(runtime: Runtime | None = None) -> FastAPI:
    """Build the standalone app. A prebuilt ``runtime`` is injected in tests."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.checkin = runtime or _default_runtime()
        try:
            yield
        finally:
            app.state.checkin.close()

    app = FastAPI(title="TDEV check-in", version="0.1.0", lifespan=lifespan)
    if runtime is not None:
        app.state.checkin = runtime  # tests use the client without running the lifespan
    api = APIRouter(prefix="/api")
    api.include_router(checkin_routes.router)
    app.include_router(api)

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    return app


def _app_factory() -> FastAPI:
    return create_standalone_app()


app = _app_factory() if __name__ != "__main__" else None
