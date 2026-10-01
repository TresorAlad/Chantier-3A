"""Default adapters: reuse 3A sessions, RBAC and key ring, read-only, on pooled connections.

The 3A helpers take a ``Store``; a ``Store`` only wraps a psycopg connection, so each call gets
a pooled connection wrapped in a throwaway ``Store``. Nothing here writes: ``Store.execute``
commits on every call and must not be used inside the module's own transactions.
"""

from __future__ import annotations

import threading
import time

import psycopg
from fastapi import Request

from auth import rbac
from auth import service as auth_svc
from checkin.ports import AuthError, Principal
from events import issue as issue_mod
from store.store import Store


class Sessions3AAuth:
    """Bearer/cookie session of the 3A + org roles (``scanner`` / ``admin``)."""

    def __init__(self, session_secret: str = "", config3a=None) -> None:
        self._secret = session_secret
        self._config = config3a  # the 3A Config: its JWT secret validates the access tokens

    def authenticate(self, conn: psycopg.Connection, request: Request) -> Principal:
        """Validate the 3A session token on the pooled connection."""
        # Imported lazily: ``http_layer`` imports the check-in routes, which import this module.
        from http_layer.session import check_csrf, extract_token

        token, via_cookie = extract_token(request)
        if not token:
            raise AuthError(401, "unauthorized", "authentication required")
        if via_cookie:
            # Cookie sessions need the CSRF secret; without it only Bearer tokens are accepted.
            if not self._secret:
                raise AuthError(401, "unauthorized", "cookie sessions are not accepted here; use Authorization: Bearer")
            if not check_csrf(request, token, via_cookie, self._secret):
                raise AuthError(403, "forbidden", "CSRF token missing or invalid")
        try:
            if self._config is not None:  # 3A access tokens are JWTs backed by a session row
                user = auth_svc.validate_access_token(Store(_pg=conn), self._config, token)
            else:
                user = auth_svc.validate_session(Store(_pg=conn), token)
        except auth_svc.SessionInvalid as err:
            raise AuthError(401, "unauthorized", "authentication required") from err
        return Principal(user_id=user.id, email=getattr(user, "email", "") or "")

    def require_role(self, conn: psycopg.Connection, principal: Principal, event_id: str, role: str) -> None:
        """Check the caller's role in the organisation owning the event."""
        minimum = rbac.ROLE_ADMIN if role == "admin" else rbac.ROLE_SCANNER
        if not rbac.can_manage_event(Store(_pg=conn), principal.user_id, event_id, minimum):
            raise AuthError(403, "forbidden", "you are not allowed to use check-in for this event")


class Ring3AKeySource:
    """Active event public keys, via the 3A ``issuer_public_keys`` (crypto is never rewritten)."""

    def issuer_keys(self, conn: psycopg.Connection, event_id: str) -> dict[str, bytes]:
        """Return ``{kid: public_key_bytes}`` for the event."""
        ring = issue_mod.issuer_public_keys(Store(_pg=conn), event_id)
        return dict(ring.keys)


class CachedKeySource:
    """TTL cache of the event public keys (they change only on rotation/revocation).

    Trade-off: a revoked key is still accepted for up to ``ttl`` seconds by this process.
    """

    def __init__(self, inner, ttl: float) -> None:
        self._inner = inner
        self._ttl = ttl
        self._data: dict[str, tuple[float, dict[str, bytes]]] = {}
        self._lock = threading.Lock()

    def issuer_keys(self, conn: psycopg.Connection, event_id: str) -> dict[str, bytes]:
        """Return the event keys, from memory while fresh."""
        now = time.monotonic()
        with self._lock:
            hit = self._data.get(event_id)
        if hit is not None and now - hit[0] < self._ttl:
            return hit[1]
        keys = self._inner.issuer_keys(conn, event_id)
        with self._lock:
            self._data[event_id] = (now, keys)
        return keys


class CachedAuth:
    """Optional short-lived cache of authentication and role decisions (off by default).

    Trade-off: a logged-out session or a removed role keeps working for up to ``ttl`` seconds in this
    process. It saves four SQL round trips per request; enable it only if that delay is acceptable.
    """

    def __init__(self, inner, ttl: float) -> None:
        self._inner = inner
        self._ttl = ttl
        self._principals: dict[str, tuple[float, Principal]] = {}
        self._roles: dict[tuple[str, str, str], float] = {}
        self._lock = threading.Lock()

    def authenticate(self, conn: psycopg.Connection, request: Request) -> Principal:
        """Authenticate, from memory while fresh (Bearer tokens only; cookies always go to the database)."""
        header = request.headers.get("Authorization", "")
        now = time.monotonic()
        cacheable = header.startswith("Bearer ")
        if cacheable:
            with self._lock:
                hit = self._principals.get(header)
            if hit is not None and now - hit[0] < self._ttl:
                return hit[1]
        principal = self._inner.authenticate(conn, request)
        if cacheable:
            with self._lock:
                self._principals[header] = (now, principal)
        return principal

    def require_role(self, conn: psycopg.Connection, principal: Principal, event_id: str, role: str) -> None:
        """Check the role, from memory while fresh; only successful checks are cached."""
        key = (principal.user_id, event_id, role)
        now = time.monotonic()
        with self._lock:
            ts = self._roles.get(key)
        if ts is not None and now - ts < self._ttl:
            return
        self._inner.require_role(conn, principal, event_id, role)
        with self._lock:
            self._roles[key] = now
