"""User signup, login, sessions, and password reset orchestration."""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from auth.password import hash_password, verify_password
from store import NotFoundError, Store
from store import password_reset_tokens as reset_store
from store import sessions as session_store
from store import users as user_store
from store.users import User

MIN_PASSWORD_LENGTH = 8
SESSION_TTL = timedelta(days=30)
PASSWORD_RESET_TTL = timedelta(hours=24)


class AuthError(Exception):
    """Base class for authentication and session failures."""

    pass


class EmailTaken(AuthError):
    """Signup rejected because the email is already registered."""

    pass


class InvalidEmail(AuthError):
    """Signup or login rejected because the email format is invalid."""

    pass


class WeakPassword(AuthError):
    """Password rejected because it does not meet minimum length."""

    pass


class InvalidCredentials(AuthError):
    """Login failed due to unknown user or wrong password."""

    pass


class SessionInvalid(AuthError):
    """Session token is missing, expired, or unknown."""

    pass


class ResetTokenInvalid(AuthError):
    """Password reset token is unknown, expired, or already used."""

    pass


class NoSuchUser(AuthError):
    """Password reset requested for an email that is not registered."""

    pass


class InvalidInvite(AuthError):
    """Org invite token is invalid, expired, or already used."""

    pass


def _normalize_email(email: str) -> str:
    """Internal: normalize email."""
    e = email.strip().lower()
    if not e or "@" not in e or e.startswith("@") or e.endswith("@"):
        raise InvalidEmail()
    return e


def _new_token() -> tuple[str, str]:
    """Internal: new token."""
    raw = secrets.token_bytes(32)
    plaintext = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    digest = hashlib.sha256(plaintext.encode("ascii")).hexdigest()
    return plaintext, digest


def signup(st: Store, email: str, password: str, name: str) -> User:
    """Register a new user; raises if email is taken or password is weak."""
    norm = _normalize_email(email)
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPassword()
    try:
        user_store.get_user_by_email(st, norm)
        raise EmailTaken()
    except NotFoundError:
        pass
    ph = hash_password(password)
    return user_store.create_user(st, norm, ph, name.strip())


def signup_with_invite(st: Store, invite_token: str, password: str, name: str) -> tuple[User, str]:
    """Register using an org invite token and join the organisation."""
    from store import orgs as orgs_repo

    token = invite_token.strip()
    if not token:
        raise InvalidInvite()
    token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
    try:
        inv = orgs_repo.get_org_invite_by_token_hash(st, token_hash)
    except NotFoundError as err:
        raise InvalidInvite() from err
    now = datetime.now(timezone.utc)
    if inv.accepted_at is not None or inv.expires_at <= now:
        raise InvalidInvite()
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPassword()
    try:
        user_store.get_user_by_email(st, inv.email)
        raise EmailTaken()
    except NotFoundError:
        pass
    ph = hash_password(password)
    display = name.strip() or inv.email.split("@")[0]
    user = user_store.create_user(st, inv.email, ph, display)
    orgs_repo.add_org_member(st, inv.org_id, user.id, inv.role, now)
    orgs_repo.mark_invite_accepted(st, inv.id, now)
    return user, inv.org_id


def login(st: Store, email: str, password: str) -> User:
    """Authenticate by email and password; raises on invalid credentials."""
    norm = _normalize_email(email)
    try:
        user = user_store.get_user_by_email(st, norm)
    except NotFoundError as err:
        raise InvalidCredentials() from err
    if not verify_password(user.password_hash, password):
        raise InvalidCredentials()
    return user


def create_session(st: Store, user_id: str) -> tuple[str, datetime]:
    """Persist a new session and return the bearer token and expiry."""
    token, token_hash = _new_token()
    now = datetime.now(timezone.utc)
    expires = now + SESSION_TTL
    session_store.create_session(st, token_hash, user_id, expires, now)
    return token, expires


def validate_session(st: Store, token: str) -> User:
    """Load the user for a session token or raise ``SessionInvalid``."""
    token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
    try:
        sess = session_store.get_session_by_token_hash(st, token_hash)
    except NotFoundError as err:
        raise SessionInvalid() from err
    if sess.expires_at <= datetime.now(timezone.utc):
        raise SessionInvalid()
    return user_store.get_user_by_id(st, sess.user_id)


def request_password_reset(st: Store, email: str) -> None:
    """Mint a reset token when the user exists (no-op if unknown email)."""
    try:
        mint_password_reset_token(st, email)
    except (NoSuchUser, InvalidEmail):
        return


def mint_password_reset_token(st: Store, email: str) -> tuple[str, datetime]:
    """Create a password reset token for the normalized email."""
    norm = _normalize_email(email)
    try:
        user = user_store.get_user_by_email(st, norm)
    except NotFoundError as err:
        raise NoSuchUser() from err
    token, token_hash = _new_token()
    now = datetime.now(timezone.utc)
    expires = now + PASSWORD_RESET_TTL
    reset_store.create_password_reset_token(
        st,
        reset_store.PasswordResetToken(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=expires,
            created_at=now,
            used_at=None,
        ),
    )
    return token, expires


def reset_password(st: Store, token: str, password: str) -> None:
    """Consume a reset token and set a new password, invalidating sessions."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPassword()
    token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
    try:
        rec = reset_store.get_password_reset_token(st, token_hash)
    except NotFoundError as err:
        raise ResetTokenInvalid() from err
    now = datetime.now(timezone.utc)
    if rec.used_at is not None or rec.expires_at <= now:
        raise ResetTokenInvalid()
    ph = hash_password(password)
    user_store.update_password_hash(st, rec.user_id, ph)
    reset_store.mark_password_reset_used(st, token_hash, now)
    session_store.delete_sessions_for_user(st, rec.user_id)


def logout(st: Store, token: str) -> None:
    """Delete the session row for the given bearer token."""
    if not token:
        return
    token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
    session_store.delete_session(st, token_hash)
