"""Session cookies, bearer tokens, and CSRF double-submit checks."""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone

from fastapi import Request, Response

SESSION_COOKIE = "chantier3a_session"
CSRF_COOKIE = "chantier3a_csrf"
CSRF_HEADER = "X-CSRF-Token"


def csrf_token_for(session_token: str, secret: str) -> str:
    """Derive the CSRF cookie value from the session token and server secret."""
    mac = hmac.new(secret.encode("utf-8"), session_token.encode("utf-8"), hashlib.sha256)
    return mac.hexdigest()


def extract_token(request: Request) -> tuple[str, bool]:
    """Read session token from ``Authorization`` bearer or session cookie."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and auth[7:].strip():
        return auth[7:].strip(), False
    token = request.cookies.get(SESSION_COOKIE, "")
    if token:
        return token, True
    return "", False


def set_session_cookies(response: Response, token: str, expires: datetime, secret: str, secure: bool) -> None:
    """Set HttpOnly session and CSRF cookies with matching max-age."""
    csrf = csrf_token_for(token, secret)
    max_age = int((expires - datetime.now(timezone.utc)).total_seconds())
    if max_age < 0:
        max_age = 0
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=max_age,
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf,
        httponly=False,
        secure=secure,
        samesite="lax",
        max_age=max_age,
        path="/",
    )


def clear_session_cookies(response: Response, secure: bool) -> None:
    """Remove session and CSRF cookies on logout."""
    response.delete_cookie(SESSION_COOKIE, path="/", secure=secure)
    response.delete_cookie(CSRF_COOKIE, path="/", secure=secure)


def check_csrf(request: Request, session_token: str, via_cookie: bool, secret: str) -> bool:
    """Validate double-submit CSRF header for cookie-authenticated mutating requests."""
    if not via_cookie:
        return True
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return True
    expected = csrf_token_for(session_token, secret)
    got = request.headers.get(CSRF_HEADER, "")
    return hmac.compare_digest(expected, got)
