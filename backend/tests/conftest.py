"""Pytest fixtures: PostgreSQL store, app, and seeded published events."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from bootstrap import build_services
from config import load_config
from http_layer.app import create_app
from store import event_keys as event_keys_repo
from store.store import Store, new_ulid, open_postgres
from store.timeutil import time_to_text

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://chantier3a:chantier3a@127.0.0.1:5432/chantier3a?sslmode=disable",
)


def _truncate_public_tables(store: Store) -> None:
    """Clear application data between tests (keep schema_migrations)."""
    rows = store.fetchall(
        """
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public' AND tablename != 'schema_migrations'
        """
    )
    if not rows:
        return
    names = [r["tablename"] if hasattr(r, "keys") else r[0] for r in rows]
    quoted = ", ".join(f'"{n}"' for n in names)
    store.execute(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE")


@pytest.fixture()
def demo_store():
    """Pytest fixture yielding store, config, services, and FastAPI app (demo mode)."""
    try:
        store = open_postgres(TEST_DATABASE_URL)
    except Exception as exc:
        pytest.skip(f"PostgreSQL requis pour les tests ({TEST_DATABASE_URL}): {exc}")
    _truncate_public_tables(store)
    cfg = load_config(database_url=TEST_DATABASE_URL, demo=True)
    services = build_services(store, cfg)
    app = create_app(store, cfg, services)
    yield store, cfg, services, app
    store.close()


@pytest.fixture()
def client(demo_store):
    """FastAPI test client bound to the demo app."""
    _store, _cfg, _services, app = demo_store
    return TestClient(app)


def seed_published_event(store, *, price_minor: int = 15000) -> dict:
    """Insert a minimal org, published event, and ticket type for tests."""
    org_id = new_ulid()
    now = datetime.now(timezone.utc)
    store.execute(
        """
        INSERT INTO orgs (id, name, slug, default_currency, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (org_id, "Test Org", "test-org", "EUR", time_to_text(now)),
    )
    event_id = new_ulid()
    starts = now + timedelta(days=30)
    ends = starts + timedelta(hours=4)
    pub, priv = event_keys_repo.generate_ed25519_keypair()
    event_keys_repo.create_event_with_key(
        store,
        {
            "id": event_id,
            "org_id": org_id,
            "slug": "test-event",
            "title": "Test Event",
            "starts_at": time_to_text(starts),
            "ends_at": time_to_text(ends),
            "currency": "EUR",
            "status": "published",
        },
        pub,
        priv,
    )
    tt_id = new_ulid()
    store.execute(
        """
        INSERT INTO ticket_types (
            id, event_id, name, description, price_minor, quantity_total, quantity_sold,
            sales_start, sales_end, max_per_order, status, sort_order, product_kind
        ) VALUES (?, ?, ?, '', ?, ?, 0, NULL, NULL, ?, 'active', 0, 'ticket')
        """,
        (tt_id, event_id, "General", price_minor, 50, 5),
    )
    return {"org_id": org_id, "event_id": event_id, "ticket_type_id": tt_id}
