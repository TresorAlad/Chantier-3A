"""Assemble the FastAPI app, middleware, API routers, and SPA fallback."""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter

from auth import service as auth_svc
from config import Config
from http_layer.deps import AppState, get_app_state
from http_layer.errors import json_error
from bootstrap import AppServices, build_services
from http_layer.deps import _Unauthorized, unauthorized_handler
from http_layer.middleware.rate_limit import ScanRateLimitMiddleware
from http_layer.routes import (
    auth,
    event_pages,
    events,
    events_admin,
    extras,
    media,
    meta,
    orders,
    orgs,
    payments,
    scan,
    stubs,
    sync,
    tickets,
)
from http_layer.session import check_csrf, extract_token
from spa import mount_spa
from store import Store

log = logging.getLogger("cackle.http")


def create_app(
    store: Store,
    config: Config,
    services: AppServices | None = None,
) -> FastAPI:
    """Create a configured FastAPI application for the given store and services."""
    app = FastAPI(title="Cackle (Python)", version="0.1.0")
    app.state.store = store
    app.state.config = config
    app.state.services = services or build_services(store, config)
    app.add_exception_handler(_Unauthorized, unauthorized_handler)

    origins = [config.base_url.rstrip("/")] if config.base_url else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    )

    @app.middleware("http")
    async def session_middleware(request: Request, call_next):
        """Session middleware."""
        token, via_cookie = extract_token(request)
        user = None
        if token:
            try:
                user = auth_svc.validate_session(app.state.store, token)
            except auth_svc.SessionInvalid:
                user = None
            if user and via_cookie and not check_csrf(
                request, token, via_cookie, app.state.config.session_secret
            ):
                return json_error(403, "forbidden", "CSRF token missing or invalid")
        request.state.app_state = AppState(
            store=app.state.store,
            config=app.state.config,
            services=app.state.services,
            current_user=user,
            session_token=token,
            auth_via_cookie=via_cookie,
        )
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    app.include_router(meta.root_router)
    app.include_router(media.router)

    api = APIRouter(prefix="/api")
    api.include_router(meta.api_router)
    api.include_router(auth.router)
    api.include_router(events.router)
    api.include_router(events_admin.router)
    api.include_router(events_admin.ticket_router)
    api.include_router(orgs.router)
    api.include_router(orgs.invites_router)
    api.include_router(event_pages.router)
    api.include_router(orders.router)
    api.include_router(payments.router)
    api.include_router(tickets.router)
    api.include_router(scan.router)
    api.include_router(sync.router)
    api.include_router(sync.peer_router)
    api.include_router(extras.router)
    api.include_router(extras.images_router)
    app.add_middleware(ScanRateLimitMiddleware)
    stubs.register_stubs(api)
    app.include_router(api)

    mount_spa(app)
    return app
