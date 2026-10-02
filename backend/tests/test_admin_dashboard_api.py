"""Admin dashboard API: staff order access, attendees admission flags, ticket PDF auth."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def _signup(client: TestClient, email: str, password: str = "longpassword1") -> dict[str, str]:
    r = client.post("/api/auth/signup", json={"email": email, "password": password, "name": "Admin API"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _event_with_paid_ticket(client: TestClient, demo_store) -> tuple[str, str, str, dict[str, str]]:
    _store, _cfg, _services, _app = demo_store
    suffix = uuid.uuid4().hex[:8]
    h = _signup(client, f"adm-{suffix}@example.com")
    org = client.post(
        "/api/orgs",
        json={"name": f"Org {suffix}", "slug": f"org-{suffix}"},
        headers=h,
    )
    assert org.status_code == 201
    org_id = org.json()["org"]["id"]
    from datetime import datetime, timedelta, timezone
    from store.timeutil import time_to_text

    now = datetime.now(timezone.utc)
    ev = client.post(
        "/api/events",
        json={
            "org_id": org_id,
            "slug": f"ev-{suffix}",
            "title": "Admin Event",
            "starts_at": time_to_text(now),
            "ends_at": time_to_text(now + timedelta(hours=4)),
        },
        headers=h,
    )
    assert ev.status_code == 201
    event_id = ev.json()["event"]["id"]
    client.post(f"/api/events/{event_id}/publish", headers=h)
    tt = client.post(
        f"/api/events/{event_id}/ticket-types",
        json={"name": "GA", "price_minor": 1000, "quantity_total": 5, "max_per_order": 2},
        headers=h,
    )
    assert tt.status_code == 201
    tt_id = tt.json()["ticket_type"]["id"]
    client.cookies.clear()
    order = client.post(
        "/api/orders",
        json={
            "event_id": event_id,
            "items": [{"ticket_type_id": tt_id, "quantity": 1}],
            "buyer": {"email": f"buyer-{suffix}@example.com", "name": "Buyer"},
            "provider": "manual",
        },
    )
    assert order.status_code == 201
    order_id = order.json()["order"]["id"]
    mark = client.post(f"/api/orders/{order_id}/mark-paid", headers=h)
    assert mark.status_code == 200
    ticket_id = mark.json()["tickets"][0]["id"]
    return event_id, order_id, ticket_id, h


def test_staff_can_get_order_with_tickets(client: TestClient, demo_store):
    event_id, order_id, ticket_id, admin_h = _event_with_paid_ticket(client, demo_store)
    outsider = _signup(client, f"out-{uuid.uuid4().hex[:8]}@example.com")
    denied = client.get(f"/api/orders/{order_id}", headers=outsider)
    assert denied.status_code == 404
    ok = client.get(f"/api/orders/{order_id}", headers=admin_h)
    assert ok.status_code == 200
    body = ok.json()["order"]
    assert body["id"] == order_id
    assert body["event_id"] == event_id
    assert "tickets" in body
    assert any(t["id"] == ticket_id for t in body["tickets"])


def test_attendees_include_admitted_flag(client: TestClient, demo_store):
    event_id, order_id, ticket_id, admin_h = _event_with_paid_ticket(client, demo_store)
    r = client.get(f"/api/events/{event_id}/attendees", headers=admin_h)
    assert r.status_code == 200
    rows = r.json()["attendees"]
    assert len(rows) == 1
    assert rows[0]["ticket_id"] == ticket_id
    assert rows[0]["admitted"] is False


def test_ticket_pdf_requires_auth(client: TestClient, demo_store):
    _event_id, _order_id, ticket_id, admin_h = _event_with_paid_ticket(client, demo_store)
    anon = client.get(f"/api/tickets/{ticket_id}/pdf")
    assert anon.status_code == 401
    pdf = client.get(f"/api/tickets/{ticket_id}/pdf", headers=admin_h)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content[:4] == b"%PDF"


def test_ticket_resend_queues_email(client: TestClient, demo_store):
    _event_id, _order_id, ticket_id, admin_h = _event_with_paid_ticket(client, demo_store)
    r = client.post(f"/api/tickets/{ticket_id}/resend", headers=admin_h)
    assert r.status_code == 200
    assert r.json().get("ok") is True
