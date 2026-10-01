"""Default adapters: reuse 3A sessions, RBAC and key ring, read-only, on pooled connections.

The 3A helpers take a ``Store``; a ``Store`` only wraps a psycopg connection, so each call gets
a pooled connection wrapped in a throwaway ``Store``. Nothing here writes: ``Store.execute``
commits on every call and must not be used inside the module's own transactions.
"""

from __future__ import annotations

import psycopg
from fastapi import Request

from auth import rbac
from auth import service as auth_svc
from checkin.ports import AuthError, Principal
from events import issue as issue_mod
from http_layer.session import check_csrf, extract_token
from store.store import Store


class Sessions3AAuth:
    """Bearer/cookie session of the 3A + org roles (``scanner`` / ``admin``)."""

    def __init__(self, session_secret: str = "", config3a=None) -> None:
        self._secret = session_secret
        self._config = config3a  # the 3A Config: its JWT secret validates the access tokens

    def authenticate(self, conn: psycopg.Connection, request: Request) -> Principal:
        """Validate the 3A session token on the pooled connection."""
        token, via_cookie = extract_token(request)
        if not token:
            raise AuthError(401, "unauthorized", "authentication required")
        if via_cookie and self._secret and not check_csrf(request, token, via_cookie, self._secret):
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
