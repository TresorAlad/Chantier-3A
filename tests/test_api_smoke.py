"""Smoke-test public API routes reachable without full domain setup."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from conftest import seed_published_event
from store.timeutil import time_to_text


def _auth_headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    r = client.post("/api/auth/signup", json={"email": email, "password": password, "name": "Smoke User"})
    assert r.status_code == 200, r.text
    data = r.json()
    return {"Authorization": f"Bearer {data['token']}"}


@pytest.fixture()
def client(demo_store):
    _store, _cfg, _services, app = demo_store
    return TestClient(app)


def test_meta_and_public(client):
    assert client.get("/healthz").status_code == 200
    assert client.get("/api/public/site-config").status_code == 200
    assert client.get("/api/categories").status_code == 200
    assert client.get("/api/currencies").status_code == 200
    assert client.get("/api/events/").status_code == 200


def test_auth_flow(client):
    r = client.post(
        "/api/auth/signup",
        json={"email": "smoke1@example.com", "password": "longpassword1", "name": "A"},
    )
    assert r.status_code == 200
    token = r.json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/auth/me", headers=h).status_code == 200
    assert client.post("/api/auth/logout", headers=h).status_code == 204
    assert client.get("/api/auth/me", headers=h).status_code == 401
    assert client.get("/api/auth/providers").status_code == 200
    assert client.post("/api/auth/password-reset", json={"email": "smoke1@example.com"}).status_code == 200


def test_organizer_event_and_order_flow(client, demo_store):
    store, _cfg, _services, _app = demo_store
    h = _auth_headers(client, "org@example.com", "longpassword1")
    org = client.post("/api/orgs", json={"name": "Smoke Org", "slug": "smoke-org"}, headers=h)
    assert org.status_code == 201, org.text
    org_id = org.json()["org"]["id"]

    now = datetime.now(timezone.utc)
    ev_body = {
        "org_id": org_id,
        "slug": "smoke-ev",
        "title": "Smoke Event",
        "starts_at": time_to_text(now + timedelta(days=10)),
        "ends_at": time_to_text(now + timedelta(days=10, hours=3)),
    }
    ev = client.post("/api/events", json=ev_body, headers=h)
    assert ev.status_code == 201, ev.text
    event_id = ev.json()["event"]["id"]

    pub = client.post(f"/api/events/{event_id}/publish", headers=h)
    assert pub.status_code == 200, pub.text

    tt = client.post(
        f"/api/events/{event_id}/ticket-types",
        json={"name": "GA", "price_minor": 1000, "quantity_total": 10, "max_per_order": 4},
        headers=h,
    )
    assert tt.status_code == 201, tt.text
    tt_id = tt.json()["ticket_type"]["id"]

    assert client.get(f"/api/events/{event_id}", headers=h).status_code == 200
    assert client.get(f"/api/orgs/{org_id}/events", headers=h).status_code == 200
    assert client.get(f"/api/events/{event_id}/stats", headers=h).status_code == 200
    assert client.get(f"/api/events/{event_id}/ticket-types", headers=h).status_code == 200
    assert client.get(f"/api/events/{event_id}/admission-conflicts", headers=h).status_code == 200

    # Guest checkout: clear session cookies so CSRF is not required (cookie auth only).
    client.cookies.clear()
    order = client.post(
        "/api/orders",
        json={
            "event_id": event_id,
            "items": [{"ticket_type_id": tt_id, "quantity": 1}],
            "buyer": {"email": "buyer@example.com", "name": "Buyer"},
            "provider": "manual",
        },
    )
    assert order.status_code == 201, order.text
    order_id = order.json()["order"]["id"]

    mark = client.post(f"/api/orders/{order_id}/mark-paid", headers=h)
    assert mark.status_code == 200, mark.text

    buyer_h = _auth_headers(client, "buyer@example.com", "longpassword2")
    assert client.get("/api/orders", headers=buyer_h).status_code == 200
    assert client.get("/api/tickets", headers=buyer_h).status_code == 200


def test_seeded_public_list(client, demo_store):
    store, *_ = demo_store
    seed_published_event(store)
    r = client.get("/api/events/")
    assert r.status_code == 200
    assert len(r.json().get("events", [])) >= 1
