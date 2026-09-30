"""Serve oauth route"""

from __future__ import annotations
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response, Depends
from authlib.integrations.starlette_client import OAuth
from auth import service as auth
from http_layer.deps import AppState, get_app_state
from http_layer.errors import json_error
from config import load_config, load_env_file
from store import NotFoundError
from store.users import User, Provider, UserPartial, create_user, get_user_by_email, get_user_by_provider_user_id
from http_layer.session import set_jwt_cookies, set_refresh_cookie
import os
import json
import logging

load_env_file()
config =load_config()

oauth_gle = OAuth()
oauth_gle.register(
    name="google",
    client_id=config.google_client_id,
    client_secret=config.google_client_secret,
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    authorize_params={"scope": "openid email profile"},
    access_token_url="https://oauth2.googleapis.com/token",
    client_kwargs={"scope":"openid email profile"},
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration"
)

router = APIRouter()

def _secure_request(request: Request) -> bool:
    if request.url.scheme == "https":
        return True
    return request.headers.get("X-Forwarded-Proto", "").lower() == "https"

def _user_view(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "avatar": u.avatar,
        "created_at": u.created_at.isoformat().replace("+00:00", "Z"),
    }

@router.get("/auth/google")
async def auth_google(request: Request):
    redirect_uri = os.getenv(
        "CHANTIER3A_GOOGLE_REDIRECT_URI",
        f"{config.base_url.rstrip('/')}/api/auth/google/callback",
    )
    return await oauth_gle.google.authorize_redirect(request, redirect_uri=redirect_uri)

@router.get("/auth/google/callback")
async def google_callback(request: Request, state: AppState = Depends(get_app_state)):
    try:
        token_gle = await oauth_gle.google.authorize_access_token(request)
        user_info = token_gle.get("userinfo") or {}

        sub = user_info.get("sub")
        email = user_info.get("email")
        email_verified = bool(user_info.get("email_verified"))

        if not sub or not email or not email_verified:
            return json_error(400, "invalid_request", "Google email not verified or missing")

        full_name = " ".join(
            part for part in (
                user_info.get("given_name"),
                user_info.get("family_name"),
                user_info.get("name"),
            ) if part
        )

        try:
            user = get_user_by_provider_user_id(state.store, Provider.Google, sub)
        except NotFoundError:
            try:
                user = get_user_by_email(state.store, email)
            except NotFoundError:
                user = create_user(
                    state.store,
                    UserPartial(
                        email=email,
                        name=user_info.get("name") or email.split("@")[0],
                        full_name=full_name,
                        avatar=user_info.get("picture"),
                        provider=Provider.Google,
                        provider_user_id=sub,
                    )
                )
            else:
                return json_error(409, "conflict", "account already exists; use local login instead")

        access_token, refresh_token, expires = auth.issue_auth_tokens(
            state.store,
            state.config,
            user,
            state.config.access_token_expire_minutes,
            auth_method="OAuth2/google",
        )
        payload = {
            "user": _user_view(user),
            "token": access_token,
            "refresh_token": refresh_token,
        }
        resp = Response(content=json.dumps(payload), media_type="application/json")
        set_jwt_cookies(
            resp,
            access_token,
            expires,
            state.config.session_secret,
            _secure_request(request),
        )
        set_refresh_cookie(
            resp,
            refresh_token,
            datetime.now(timezone.utc) + auth.SESSION_TTL,
            _secure_request(request),
        )
        return resp
    except Exception:
        logging.exception("Google OAuth callback failed")
        return json_error(500, "internal_error", "Google OAuth failed")