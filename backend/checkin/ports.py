"""Ports of the check-in module: what it needs from the outside world.

Adapters live in ``checkin.adapters``. A future Staff-session adapter (Amélie) or a
file-snapshot ``TicketSource`` (fallback deployment) only has to implement these protocols.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol

import psycopg
from fastapi import Request

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    """Default clock (injectable in tests)."""
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Principal:
    """The authenticated caller."""

    user_id: str
    email: str = ""


class AuthError(Exception):
    """Raised by a ``TerminalAuth`` adapter; carries the HTTP status and stable error code."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class TerminalAuth(Protocol):
    """Authenticates a request and checks its role on an event."""

    def authenticate(self, conn: psycopg.Connection, request: Request) -> Principal:
        """Return the caller or raise ``AuthError(401, 'unauthorized', …)``."""
        ...

    def require_role(self, conn: psycopg.Connection, principal: Principal, event_id: str, role: str) -> None:
        """Raise ``AuthError(403, 'forbidden', …)`` unless ``principal`` has ``role`` (scanner | admin) on the event."""
        ...


class KeySource(Protocol):
    """Provides the active Ed25519 public keys (kid -> raw bytes) of an event."""

    def issuer_keys(self, conn: psycopg.Connection, event_id: str) -> dict[str, bytes]:
        """Active public keys of ``event_id``."""
        ...
