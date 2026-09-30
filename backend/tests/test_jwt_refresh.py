from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest

from auth import service as auth_svc
from store.users import User


class _FakeStore:
    pass


def test_validate_access_token_rejects_disabled_user(monkeypatch):
    user = User(
        id="user-1",
        created_at=datetime.now(timezone.utc),
        login_at=datetime.now(timezone.utc),
        email="alice@example.com",
        name="Alice",
        disabled=True,
    )

    monkeypatch.setattr(
        auth_svc.user_store,
        "get_user_by_id",
        lambda st, user_id: user,
    )
    monkeypatch.setattr(
        auth_svc.session_store,
        "get_session_by_token_hash",
        lambda st, token_hash: SimpleNamespace(
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        ),
    )

    token = jwt.encode(
        {"sub": user.id, "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "test-secret",
        algorithm="HS256",
    )
    settings = SimpleNamespace(secret_key="test-secret", algorithm="HS256")

    with pytest.raises(auth_svc.SessionInvalid):
        auth_svc.validate_access_token(_FakeStore(), settings, token)


def test_refresh_token_rotation_returns_new_tokens(monkeypatch):
    user = User(
        id="user-2",
        created_at=datetime.now(timezone.utc),
        login_at=datetime.now(timezone.utc),
        email="bob@example.com",
        name="Bob",
        disabled=False,
    )
    saved = {}

    monkeypatch.setattr(
        auth_svc.user_store,
        "get_user_by_refresh_token",
        lambda st, token: user,
    )
    monkeypatch.setattr(
        auth_svc.user_store,
        "save_user_refresh_token",
        lambda st, user_id, token: saved.setdefault("token", token) or None,
    )
    monkeypatch.setattr(
        auth_svc.session_store,
        "create_session",
        lambda *args, **kwargs: None,
    )

    settings = SimpleNamespace(
        secret_key="test-secret",
        algorithm="HS256",
        access_token_expire_minutes=15,
    )

    access_token, refresh_token, expires = auth_svc.refresh_access_token(
        _FakeStore(), settings, "old-refresh-token"
    )

    assert access_token
    assert refresh_token
    assert refresh_token != "old-refresh-token"
    assert saved["token"] == refresh_token
    assert expires > datetime.now(timezone.utc)
