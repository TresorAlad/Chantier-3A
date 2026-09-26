"""Load server configuration from environment variables and CLI overrides."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

_BACKEND_ROOT = Path(__file__).resolve().parent
_ENV_LOADED = False

HostScope = Literal["own", "single"]

ENV_ADDR = "CHANTIER3A_ADDR"
ENV_DATA_DIR = "CHANTIER3A_DATA_DIR"
ENV_DATABASE_URL = "CHANTIER3A_DATABASE_URL"
ENV_BASE_URL = "CHANTIER3A_BASE_URL"
ENV_SESSION_SECRET = "CHANTIER3A_SESSION_SECRET"
ENV_MEDIA_DIR = "CHANTIER3A_MEDIA_DIR"
ENV_HOST_SCOPE = "CHANTIER3A_HOST_SCOPE"
ENV_HOST_ORG = "CHANTIER3A_HOST_ORG"
ENV_HOST_NAME = "CHANTIER3A_HOST_NAME"
ENV_COMMUNITY_MODE = "CHANTIER3A_COMMUNITY_MODE"
ENV_SMTP_HOST = "CHANTIER3A_SMTP_HOST"
ENV_SMTP_PORT = "CHANTIER3A_SMTP_PORT"
ENV_SMTP_FROM = "CHANTIER3A_SMTP_FROM"
ENV_SMTP_USER = "CHANTIER3A_SMTP_USER"
ENV_SMTP_PASSWORD = "CHANTIER3A_SMTP_PASSWORD"
ENV_PAYMENT_PROVIDERS = "CHANTIER3A_PAYMENT_PROVIDERS"
ENV_PAYMENT_SERVICE_URL = "CHANTIER3A_PAYMENT_SERVICE_URL"
ENV_PAYMENT_SERVICE_API_KEY = "CHANTIER3A_PAYMENT_SERVICE_API_KEY"
ENV_PAYMENT_WEBHOOK_SECRET = "CHANTIER3A_PAYMENT_WEBHOOK_SECRET"
ENV_PAYMENT_PROVIDER_NAME = "CHANTIER3A_PAYMENT_PROVIDER_NAME"
ENV_PAYMENT_SERVICE_TIMEOUT = "CHANTIER3A_PAYMENT_SERVICE_TIMEOUT"
ENV_KEY_PASSPHRASE = "CHANTIER3A_KEY_PASSPHRASE"
ENV_PUBLIC_SIGNUP = "CHANTIER3A_PUBLIC_SIGNUP"

DEFAULT_ADDR = ":8080"
DEFAULT_DATA_DIR = "./data"
DEFAULT_BASE_URL = "http://localhost:8080"


@dataclass
class Config:
    """Config."""
    addr: str
    data_dir: str
    database_url: str
    base_url: str
    session_secret: str
    media_dir: str
    demo: bool
    host_scope: HostScope
    host_org: str
    host_name: str
    community_mode: bool
    smtp_host: str
    smtp_port: int
    smtp_from: str
    smtp_user: str
    smtp_password: str
    key_passphrase: str
    payment_service_url: str
    payment_service_api_key: str
    payment_webhook_secret: str
    payment_provider_name: str
    payment_service_timeout: int
    public_signup: bool


def load_env_file() -> Path | None:
    """Load ``backend-python/.env`` into os.environ (once). Returns path if found."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return _BACKEND_ROOT / ".env" if (_BACKEND_ROOT / ".env").is_file() else None
    _ENV_LOADED = True
    env_path = _BACKEND_ROOT / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)
        return env_path
    return None


def _env(key: str, default: str = "") -> str:
    """Internal: env."""
    return os.environ.get(key, default).strip()


def _truthy(key: str) -> bool:
    """Internal: truthy."""
    v = os.environ.get(key, "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _session_secret(data_dir: str) -> str:
    """Internal: session secret."""
    explicit = _env(ENV_SESSION_SECRET)
    if explicit:
        return explicit
    base = Path(data_dir).resolve()
    secret_path = base / ".chantier3a_session_secret"
    if secret_path.is_file():
        return secret_path.read_text(encoding="utf-8").strip()
    material = secrets.token_hex(32)
    base.mkdir(parents=True, exist_ok=True)
    secret_path.write_text(material, encoding="utf-8")
    os.chmod(secret_path, 0o600)
    return material


def load_config(
    *,
    addr: str = "",
    data_dir: str = "",
    database_url: str = "",
    base_url: str = "",
    media_dir: str = "",
    demo: bool = False,
) -> Config:
    """Build a ``Config`` from environment variables with optional CLI overrides."""
    load_env_file()
    resolved_addr = addr or _env(ENV_ADDR, DEFAULT_ADDR)
    resolved_data = data_dir or _env(ENV_DATA_DIR, DEFAULT_DATA_DIR)
    resolved_base = base_url or _env(ENV_BASE_URL, DEFAULT_BASE_URL)
    resolved_db_url = database_url or _env(ENV_DATABASE_URL)

    scope = _env(ENV_HOST_SCOPE, "own") or "own"
    if scope not in ("own", "single"):
        scope = "own"

    smtp_port = 587
    if p := _env(ENV_SMTP_PORT):
        try:
            smtp_port = int(p)
        except ValueError:
            smtp_port = 587

    md = media_dir or _env(ENV_MEDIA_DIR)
    if not md:
        md = os.path.join(resolved_data, "media")

    pay_timeout = 30
    if pt := _env(ENV_PAYMENT_SERVICE_TIMEOUT):
        try:
            pay_timeout = int(pt)
        except ValueError:
            pay_timeout = 30

    return Config(
        addr=resolved_addr,
        data_dir=resolved_data,
        database_url=resolved_db_url,
        base_url=resolved_base,
        session_secret=_session_secret(resolved_data),
        media_dir=md,
        demo=demo,
        host_scope=scope,  # type: ignore[arg-type]
        host_org=_env(ENV_HOST_ORG),
        host_name=_env(ENV_HOST_NAME),
        community_mode=_truthy(ENV_COMMUNITY_MODE),
        smtp_host=_env(ENV_SMTP_HOST),
        smtp_port=smtp_port,
        smtp_from=_env(ENV_SMTP_FROM),
        smtp_user=_env(ENV_SMTP_USER),
        smtp_password=_env(ENV_SMTP_PASSWORD),
        key_passphrase=_env(ENV_KEY_PASSPHRASE),
        payment_service_url=_env(ENV_PAYMENT_SERVICE_URL),
        payment_service_api_key=_env(ENV_PAYMENT_SERVICE_API_KEY),
        payment_webhook_secret=_env(ENV_PAYMENT_WEBHOOK_SECRET),
        payment_provider_name=_env(ENV_PAYMENT_PROVIDER_NAME) or "community-pay",
        payment_service_timeout=pay_timeout,
        public_signup=demo or _truthy(ENV_PUBLIC_SIGNUP),
    )
