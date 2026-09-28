"""Persist and load user account rows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from store.store import NotFoundError, Store, new_ulid


@dataclass
class User:
    """User."""
    id: str
    email: str
    password_hash: str
    name: str
    created_at: datetime
    email_verified_at: datetime | None = None


def _parse_time(text: str) -> datetime:
    """Internal: parse time."""
    from datetime import timezone

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text).astimezone(timezone.utc)


def get_user_by_email(st: Store, email: str) -> User:
    """Get user by email."""
    row = st.fetchone(
        """
        SELECT id, email, password_hash, name, created_at, email_verified_at
        FROM users WHERE email = ?
        """,
        (email,),
    )
    if row is None:
        raise NotFoundError()
    return _row_user(row)


def get_user_by_id(st: Store, user_id: str) -> User:
    """Get user by id."""
    row = st.fetchone(
        """
        SELECT id, email, password_hash, name, created_at, email_verified_at
        FROM users WHERE id = ?
        """,
        (user_id,),
    )
    if row is None:
        raise NotFoundError()
    return _row_user(row)


def create_user(st: Store, email: str, password_hash: str, name: str) -> User:
    """Create user."""
    from datetime import timezone

    uid = new_ulid()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    st.execute(
        """
        INSERT INTO users (id, email, password_hash, name, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (uid, email, password_hash, name, now),
    )
    return User(
        id=uid,
        email=email,
        password_hash=password_hash,
        name=name,
        created_at=_parse_time(now),
    )


def update_password_hash(st: Store, user_id: str, password_hash: str) -> None:
    """Update password hash."""
    n = st.execute_rowcount(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (password_hash, user_id),
    )
    if n == 0:
        raise NotFoundError()


def _row_user(row) -> User:
    """Internal: row user."""
    if hasattr(row, "keys"):
        keys = row.keys()
        get = lambda k: row[k]
    else:
        get = lambda i: row[i]
        keys = range(len(row))

    if "id" in keys or (isinstance(keys, range) and len(row) >= 6):
        if hasattr(row, "keys"):
            ev = get("email_verified_at")
            return User(
                id=get("id"),
                email=get("email"),
                password_hash=get("password_hash"),
                name=get("name"),
                created_at=_parse_time(get("created_at")),
                email_verified_at=_parse_time(ev) if ev else None,
            )
    # sqlite Row or tuple
    if hasattr(row, "__getitem__") and not hasattr(row, "keys"):
        ev = row[5] if len(row) > 5 else None
        return User(
            id=row[0],
            email=row[1],
            password_hash=row[2],
            name=row[3],
            created_at=_parse_time(row[4]),
            email_verified_at=_parse_time(ev) if ev else None,
        )
    ev = get("email_verified_at")
    return User(
        id=get("id"),
        email=get("email"),
        password_hash=get("password_hash"),
        name=get("name"),
        created_at=_parse_time(get("created_at")),
        email_verified_at=_parse_time(ev) if ev else None,
    )
