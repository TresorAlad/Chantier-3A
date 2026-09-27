"""Apply SQL schema migrations for PostgreSQL."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import psycopg

from store.paths import MIGRATIONS_DIR

_VERSION_RE = re.compile(r"^(\d+)_")


def _version_from_name(name: str) -> int:
    """Internal: version from name."""
    m = _VERSION_RE.match(name)
    if not m:
        raise ValueError(f"migration filename has no version prefix: {name}")
    return int(m.group(1))


def _migration_files(directory: Path) -> list[str]:
    """Internal: migration files."""
    if not directory.is_dir():
        raise FileNotFoundError(f"migrations directory missing: {directory}")
    names = sorted(p.name for p in directory.glob("*.sql"))
    return names


def _ensure_schema_migrations_postgres(conn: psycopg.Connection) -> None:
    """Internal: ensure schema migrations postgres."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    INTEGER PRIMARY KEY,
            name       TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def _applied_at() -> str:
    """Internal: applied at."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def migrate_postgres(database_url: str) -> list[int]:
    """Apply pending SQL migrations to PostgreSQL."""
    conn = psycopg.connect(database_url)
    try:
        _ensure_schema_migrations_postgres(conn)
        for name in _migration_files(MIGRATIONS_DIR):
            version = _version_from_name(name)
            row = conn.execute(
                "SELECT COUNT(*) FROM schema_migrations WHERE version = %s",
                (version,),
            ).fetchone()
            if row and row[0] > 0:
                continue
            sql = (MIGRATIONS_DIR / name).read_text(encoding="utf-8")
            with conn.transaction():
                conn.execute(sql)
                conn.execute(
                    "INSERT INTO schema_migrations (version, name, applied_at) VALUES (%s, %s, %s)",
                    (version, name, _applied_at()),
                )
        cur = conn.execute("SELECT version FROM schema_migrations ORDER BY version")
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def migrate_store(*, database_url: str) -> list[int]:
    """Apply all pending SQL migrations (PostgreSQL only)."""
    url = (database_url or "").strip()
    if not url:
        raise ValueError("CHANTIER3A_DATABASE_URL is required (PostgreSQL only)")
    return migrate_postgres(url)
