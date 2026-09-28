"""One-time password reset tokens with expiry and use tracking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from store.store import NotFoundError, Store
from store.timeutil import text_to_null_time, text_to_time, time_to_text


@dataclass
class PasswordResetToken:
    """Passwordresettoken."""
    token_hash: str
    user_id: str
    expires_at: datetime
    created_at: datetime
    used_at: datetime | None


def create_password_reset_token(st: Store, rec: PasswordResetToken) -> None:
    """Create password reset token."""
    st.execute(
        """
        INSERT INTO password_reset_tokens (token_hash, user_id, expires_at, created_at, used_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            rec.token_hash,
            rec.user_id,
            time_to_text(rec.expires_at),
            time_to_text(rec.created_at),
            time_to_text(rec.used_at) if rec.used_at else None,
        ),
    )


def get_password_reset_token(st: Store, token_hash: str) -> PasswordResetToken:
    """Get password reset token."""
    row = st.fetchone(
        """
        SELECT token_hash, user_id, expires_at, created_at, used_at
        FROM password_reset_tokens WHERE token_hash = ?
        """,
        (token_hash,),
    )
    if row is None:
        raise NotFoundError()
    if hasattr(row, "keys"):
        return PasswordResetToken(
            token_hash=row["token_hash"],
            user_id=row["user_id"],
            expires_at=text_to_time(row["expires_at"]),
            created_at=text_to_time(row["created_at"]),
            used_at=text_to_null_time(row["used_at"]),
        )
    return PasswordResetToken(
        token_hash=row[0],
        user_id=row[1],
        expires_at=text_to_time(row[2]),
        created_at=text_to_time(row[3]),
        used_at=text_to_null_time(row[4]),
    )


def mark_password_reset_used(st: Store, token_hash: str, used_at: datetime) -> None:
    """Mark password reset used."""
    st.execute(
        "UPDATE password_reset_tokens SET used_at = ? WHERE token_hash = ?",
        (time_to_text(used_at), token_hash),
    )
