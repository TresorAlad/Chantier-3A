"""Per-request application state and authentication dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Depends, Request

from bootstrap import AppServices
from config import Config
from http_layer.errors import json_error
from store import Store
from store.users import User


@dataclass
class AppState:
    """Appstate."""
    store: Store
    config: Config
    services: AppServices
    current_user: User | None = field(default=None)
    session_token: str = ""
    auth_via_cookie: bool = False


def get_app_state(request: Request) -> AppState:
    """FastAPI dependency returning per-request ``AppState``."""
    return request.state.app_state


def require_user(state: AppState = Depends(get_app_state)) -> AppState:
    """Dependency that requires an authenticated user or returns 401."""
    if state.current_user is None:
        raise _Unauthorized()
    return state


class _Unauthorized(Exception):
    """Internal: Unauthorized."""
    pass


async def unauthorized_handler(_request: Request, _exc: _Unauthorized):
    """Unauthorized handler."""
    return json_error(401, "unauthorized", "authentication required")
