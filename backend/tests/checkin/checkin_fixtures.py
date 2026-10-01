"""Fixtures of the check-in tests (imported by the test modules: no conftest.py here, see below): real PostgreSQL, explicit migrations, a paid-tickets world.

Safety: ``tests/conftest.py`` TRUNCATEs every public table of ``TEST_DATABASE_URL``. These tests
therefore refuse to run unless the database name ends with ``_test``.

This file is deliberately not a ``conftest.py``: the existing 3A tests do ``from conftest import ...``
and a second ``conftest`` module would shadow the first one.
"""

from __future__ import annotations

import dataclasses
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import psycopg
import psycopg.rows
import pytest

from checkin.config import CheckinConfig
from checkin.runtime import build_runtime
from checkin_helpers import ShiftClock
# The 3A suite runs on SQLite unless TEST_DATABASE_URL points to a PostgreSQL *_test database.
# The check-in module needs PostgreSQL (advisory locks, unnest): without it these tests are SKIPPED
# (never a failure, and never an abort of the whole suite).
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "").strip()

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


def _db_name(url: str) -> str:
    return urlparse(url).path.lstrip("/")


@pytest.fixture(scope="session", autouse=True)
def applied_schema():
    """Apply every migration with explicit commits (independent of ``store/migrate.py``)."""
    if not TEST_DATABASE_URL:
        pytest.skip("check-in tests need PostgreSQL: set TEST_DATABASE_URL to a database named *_test (SQLite default)")
    name = _db_name(TEST_DATABASE_URL)
    if not name.endswith("_test"):
        pytest.exit(
            f"refusing to run check-in tests on database '{name}': its name must end with '_test' "
            "(the shared conftest TRUNCATEs all tables). Set TEST_DATABASE_URL to a disposable database.",
            returncode=2,
        )
    try:
        conn = psycopg.connect(TEST_DATABASE_URL, autocommit=True, connect_timeout=3)
    except Exception as exc:  # pragma: no cover - environment problem
        pytest.exit(f"PostgreSQL required for check-in tests ({name}): {type(exc).__name__}", returncode=2)
    with conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)"
        )
        for path in sorted(MIGRATIONS.glob("*.sql")):
            version = int(re.match(r"(\d+)_", path.name).group(1))
            if conn.execute("SELECT 1 FROM schema_migrations WHERE version = %s", (version,)).fetchone():
                continue
            with conn.transaction():
                conn.execute(path.read_text(encoding="utf-8"))
                conn.execute(
                    "INSERT INTO schema_migrations VALUES (%s, %s, %s)", (version, path.name, "test")
                )


@pytest.fixture()
def clock() -> ShiftClock:
    """Injectable clock of the check-in runtime."""
    return ShiftClock()


@pytest.fixture()
def checkin_rt(demo_store, clock):
    """Runtime attached to the mounted app: no snapshot TTL, no rate limit, pool of 10."""
    _store, cfg3a, _services, app = demo_store
    cfg = dataclasses.replace(
        CheckinConfig.from_env(TEST_DATABASE_URL),
        snapshot_ttl_seconds=0,
        rate_limit_per_terminal=0,
        pool_min=1,
        pool_max=10,
    )
    rt = build_runtime(cfg=cfg, session_secret=cfg3a.session_secret, config3a=cfg3a, clock=clock)
    app.state.checkin = rt
    yield rt
    rt.close()


@pytest.fixture()
def commit_3a(demo_store):
    """Validate the 3A single connection (it leaves work pending; see BUGS_3A.md bug 3)."""
    return lambda: demo_store[0]._pg.commit()


@pytest.fixture()
def db(demo_store):
    """Autocommit side connection for assertions (never the module's own pool)."""
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True, row_factory=psycopg.rows.dict_row) as conn:
        yield conn
