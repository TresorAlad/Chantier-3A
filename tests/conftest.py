"""Pytest fixtures: in-memory demo store, app, and seeded published events."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from bootstrap import build_services
from config import load_config
from http_layer.app import create_app
from store import event_keys as event_keys_repo
from store.store import new_ulid, open_sqlite
from store.timeutil import time_to_text


@pytest.fixture()
def demo_store(tmp_path):
    """Pytest fixture yielding store, config, services, and FastAPI app (demo mode)."""
    db_path = str(tmp_path / "test.db")
    store = open_sqlite(db_path)
    cfg = load_config(db=db_path, demo=True)
    services = build_services(store, cfg)
    app = create_app(store, cfg, services)
    yield store, cfg, services, app
    store.close()


@pytest.fixture()
def client(demo_store):
    """FastAPI test client bound to the in-memory demo app."""
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
