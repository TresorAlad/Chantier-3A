"""Signup, login, logout, and password reset HTTP handlers."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from auth import service as auth_svc
from http_layer.deps import AppState, get_app_state
from http_layer.errors import json_error
from http_layer.session import clear_session_cookies, set_session_cookies
from store.users import User

router = APIRouter(prefix="/auth", tags=["auth"])


class CredentialsBody(BaseModel):
    """Email, password, and optional display name for signup."""
    email: str = ""
    password: str = ""
    name: str = Field(default="", alias="name")

    model_config = {"populate_by_name": True}


class SignupWithInviteBody(BaseModel):
    """Create a staff account from an org invite token."""
    token: str = ""
    password: str = ""
    name: str = ""


def _user_view(u: User) -> dict:
    """Internal: user view."""
    out = {
        "id": u.id,
        "email": u.email,
        "name": u.name,
        "created_at": u.created_at.isoformat().replace("+00:00", "Z"),
    }
    if u.email_verified_at:
        out["email_verified_at"] = u.email_verified_at.isoformat().replace("+00:00", "Z")
    return out


def _secure_request(request: Request) -> bool:
    """Internal: secure request."""
    if request.url.scheme == "https":
        return True
    return request.headers.get("X-Forwarded-Proto", "").lower() == "https"


@router.post("/signup")
def signup(
    request: Request,
    body: CredentialsBody,
    state: AppState = Depends(get_app_state),
) -> Response:
    """Register a new user; disabled when public signup is off (staff uses invite flow)."""
    if not state.config.public_signup:
        return json_error(
            403,
            "forbidden",
            "public signup is disabled; use an administrator invite to create an account",
        )
    try:
        user = auth_svc.signup(state.store, body.email, body.password, body.name)
    except auth_svc.InvalidEmail:
        return json_error(400, "invalid_request", "invalid email address")
    except auth_svc.WeakPassword:
        return json_error(400, "invalid_request", "password too short")
    except auth_svc.EmailTaken:
        return json_error(409, "conflict", "an account with that email already exists")
    except Exception:
        return json_error(500, "internal_error", "internal error")

    token, expires = auth_svc.create_session(state.store, user.id)
    payload = {"user": _user_view(user), "token": token}
    resp = Response(content=json.dumps(payload), media_type="application/json")
    set_session_cookies(resp, token, expires, state.config.session_secret, _secure_request(request))
    return resp


@router.post("/signup-with-invite")
def signup_with_invite(
    request: Request,
    body: SignupWithInviteBody,
    state: AppState = Depends(get_app_state),
) -> Response:
    """Create a staff account from an org invite (replaces public signup)."""
    if not body.token or not body.password:
        return json_error(400, "invalid_request", "token and password are required")
    try:
        user, _org_id = auth_svc.signup_with_invite(
            state.store, body.token, body.password, body.name
        )
    except auth_svc.InvalidInvite:
        return json_error(400, "invalid_request", "invite is invalid, expired, or already used")
    except auth_svc.WeakPassword:
        return json_error(400, "invalid_request", "password too short")
    except auth_svc.EmailTaken:
        return json_error(409, "conflict", "an account with that email already exists; log in and accept the invite")
    except Exception:
        return json_error(500, "internal_error", "internal error")

    token, expires = auth_svc.create_session(state.store, user.id)
    payload = {"user": _user_view(user), "token": token}
    resp = Response(content=json.dumps(payload), media_type="application/json")
    set_session_cookies(resp, token, expires, state.config.session_secret, _secure_request(request))
    return resp


@router.post("/login")
def login(
    request: Request,
    body: CredentialsBody,
    state: AppState = Depends(get_app_state),
) -> Response:
    """Authenticate by email and password; raises on invalid credentials."""
    try:
        user = auth_svc.login(state.store, body.email, body.password)
    except auth_svc.InvalidCredentials:
        return json_error(401, "unauthorized", "invalid email or password")
    except auth_svc.InvalidEmail:
        return json_error(400, "invalid_request", "invalid email address")
    except Exception:
        return json_error(500, "internal_error", "internal error")

    token, expires = auth_svc.create_session(state.store, user.id)
    payload = {"user": _user_view(user), "token": token}
    resp = Response(content=json.dumps(payload), media_type="application/json")
    set_session_cookies(resp, token, expires, state.config.session_secret, _secure_request(request))
    return resp


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    state: AppState = Depends(get_app_state),
) -> Response:
    """Delete the session row for the given bearer token."""
    if state.session_token:
        auth_svc.logout(state.store, state.session_token)
    resp = Response(status_code=204)
    clear_session_cookies(resp, _secure_request(request))
    return resp


@router.get("/me")
def me(state: AppState = Depends(get_app_state)) -> Response:
    """Me."""
    if state.current_user is None:
        return json_error(401, "unauthorized", "authentication required")
    return Response(
        content=json.dumps({"user": _user_view(state.current_user)}),
        media_type="application/json",
    )


@router.get("/providers")
def providers() -> dict:
    """Providers."""
    return {"providers": []}


class PasswordResetBody(BaseModel):
    """Email address for initiating a password reset."""
    email: str = ""


class PasswordUpdateBody(BaseModel):
    """Reset token and new password for completing password reset."""
    token: str = ""
    password: str = ""


@router.post("/password-reset")
def password_reset(body: PasswordResetBody, state: AppState = Depends(get_app_state)) -> dict:
    """Password reset."""
    try:
        auth_svc.request_password_reset(state.store, body.email)
    except Exception:
        return json_error(500, "internal_error", "internal error")
    return {"ok": True}


@router.post("/password-update")
def password_update(body: PasswordUpdateBody, state: AppState = Depends(get_app_state)) -> dict:
    """Password update."""
    if not body.token or not body.password:
        return json_error(400, "invalid_request", "token and password are required")
    try:
        auth_svc.reset_password(state.store, body.token, body.password)
    except auth_svc.ResetTokenInvalid:
        return json_error(400, "invalid_request", "reset token invalid, expired, or already used")
    except auth_svc.WeakPassword:
        return json_error(400, "invalid_request", "password too short")
    except Exception:
        return json_error(500, "internal_error", "internal error")
    return {"ok": True}
