"""E2E: emission billet TDEV, verification capability, scan en ligne."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from events import issue as issue_mod
from store import events_repo
from store.timeutil import time_to_text
from tickets import capability as cap

TDEV_RE = re.compile(r"^TDEV-\d{4}-\d{4}$")


def _auth_headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    r = client.post(
        "/api/auth/signup",
        json={"email": email, "password": password, "name": "Scan E2E"},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _paid_ticket_flow(client: TestClient, demo_store) -> tuple[str, str, str, str, dict]:
    """Return event_id, ticket_id, capability, serial, organizer headers."""
    _store, _cfg, _services, _app = demo_store
    suffix = uuid.uuid4().hex[:8]
    h = _auth_headers(client, f"scan-org-{suffix}@example.com", "longpassword1")
    org = client.post(
        "/api/orgs",
        json={"name": f"Scan Org {suffix}", "slug": f"scan-org-{suffix}"},
        headers=h,
    )
    assert org.status_code == 201, org.text
    org_id = org.json()["org"]["id"]

    now = datetime.now(timezone.utc)
    ev_body = {
        "org_id": org_id,
        "slug": f"scan-ev-{suffix}",
        "title": "Scan Event",
        "starts_at": time_to_text(now - timedelta(hours=1)),
        "ends_at": time_to_text(now + timedelta(hours=5)),
    }
    ev = client.post("/api/events", json=ev_body, headers=h)
    assert ev.status_code == 201, ev.text
    event_id = ev.json()["event"]["id"]

    pub = client.post(f"/api/events/{event_id}/publish", headers=h)
    assert pub.status_code == 200, pub.text

    tt = client.post(
        f"/api/events/{event_id}/ticket-types",
        json={
            "name": "GA",
            "price_minor": 500,
            "quantity_total": 20,
            "max_per_order": 4,
            "access_event": True,
            "access_food": True,
            "access_merch": True,
            "access_after": True,
        },
        headers=h,
    )
    assert tt.status_code == 201, tt.text
    tt_id = tt.json()["ticket_type"]["id"]

    client.cookies.clear()
    order = client.post(
        "/api/orders",
        json={
            "event_id": event_id,
            "items": [{"ticket_type_id": tt_id, "quantity": 1}],
            "buyer": {"email": f"scan-buyer-{suffix}@example.com", "name": "Buyer"},
            "provider": "manual",
        },
    )
    assert order.status_code == 201, order.text
    order_id = order.json()["order"]["id"]

    mark = client.post(f"/api/orders/{order_id}/mark-paid", headers=h)
    assert mark.status_code == 200, mark.text
    tickets = mark.json()["tickets"]
    assert len(tickets) == 1
    ticket = tickets[0]
    return event_id, ticket["id"], ticket["capability"], ticket["serial"], h


def test_pass_tiers_meta(client: TestClient):
    r = client.get("/api/pass-tiers")
    assert r.status_code == 200
    assert "pass_tiers" in r.json()


def test_scan_events_lists_only_events_available_to_staff(
    client: TestClient, demo_store
):
    event_id, _ticket_id, _capability, _serial, headers = _paid_ticket_flow(
        client, demo_store
    )

    response = client.get("/api/scan/events", headers=headers)

    assert response.status_code == 200, response.text
    event = next(item for item in response.json()["events"] if item["id"] == event_id)
    assert event["title"] == "Scan Event"
    assert event["status"] == "published"
    assert event["scan_role"] == "owner"

    anonymous = client.get("/api/scan/events")
    assert anonymous.status_code == 401


def test_ticket_tdev_and_capability_window(client: TestClient, demo_store):
    store, *_ = demo_store
    event_id, _tid, capability, serial, _h = _paid_ticket_flow(client, demo_store)
    assert TDEV_RE.match(serial)
    assert capability.startswith("chantier3a.")

    ev = events_repo.get_event_by_id(store, event_id)
    ring = issue_mod.issuer_public_keys(store, event_id)
    now = datetime.now(timezone.utc)
    payload = cap.verify_with_ring(capability, ring, now)
    assert payload.eid == event_id
    assert payload.nbf == payload.iat  # valid from purchase (orders/service.py), not from starts_at
    assert payload.exp == int(ev.ends_at.timestamp())
    assert payload.ref == serial


def test_scan_admit_duplicate_and_wrong_event(client: TestClient, demo_store):
    event_id, ticket_id, capability, _serial, h = _paid_ticket_flow(client, demo_store)

    body = {
        "event_id": event_id,
        "capability": capability,
        "device_id": "dev-1",
        "gate_id": "gate-a",
    }
    first = client.post("/api/scan", json=body, headers=h)
    assert first.status_code == 200, first.text
    assert first.json()["result"] == "admitted"
    assert first.json()["ticket_id"] == ticket_id

    second = client.post("/api/scan", json=body, headers=h)
    assert second.status_code == 200
    assert second.json()["result"] == "duplicate"

    store, *_rest = demo_store
    now = datetime.now(timezone.utc)
    ev_row = store.fetchone("SELECT org_id FROM events WHERE id = ?", (event_id,))
    org_id = ev_row["org_id"] if hasattr(ev_row, "keys") else ev_row[0]
    other = client.post(
        "/api/events",
        json={
            "org_id": org_id,
            "slug": f"other-ev-{uuid.uuid4().hex[:6]}",
            "title": "Other",
            "starts_at": time_to_text(now - timedelta(hours=1)),
            "ends_at": time_to_text(now + timedelta(hours=5)),
        },
        headers=h,
    )
    assert other.status_code == 201, other.text
    other_event_id = other.json()["event"]["id"]

    wrong_ev = client.post(
        "/api/scan",
        json={**body, "event_id": other_event_id},
        headers=h,
    )
    assert wrong_ev.status_code == 200
    assert wrong_ev.json()["result"] == "wrong_event"

    bad = client.post(
        "/api/scan",
        json={**body, "capability": "chantier3a.not-a-token"},
        headers=h,
    )
    assert bad.status_code == 200
    assert bad.json()["result"] == "invalid"


def test_scan_expired_capability(client: TestClient, demo_store):
    store, _cfg, _services, _app = demo_store
    event_id, _tid, capability, _serial, h = _paid_ticket_flow(client, demo_store)
    ev = events_repo.get_event_by_id(store, event_id)
    after_end = ev.ends_at + timedelta(seconds=10)
    body = {
        "event_id": event_id,
        "capability": capability,
        "scanned_at": after_end.isoformat().replace("+00:00", "Z"),
    }
    r = client.post("/api/scan", json=body, headers=h)
    assert r.status_code == 200
    assert r.json()["result"] == "invalid"


def test_attendees_after_scan(client: TestClient, demo_store):
    event_id, ticket_id, capability, _serial, h = _paid_ticket_flow(client, demo_store)
    client.post(
        "/api/scan",
        json={"event_id": event_id, "capability": capability},
        headers=h,
    )
    att = client.get(f"/api/events/{event_id}/attendees", headers=h)
    assert att.status_code == 200
    ids = [a["ticket_id"] for a in att.json()["attendees"]]
    assert ticket_id in ids


def test_void_ticket_rejected_at_scan(client: TestClient, demo_store):
    store, *_ = demo_store
    event_id, ticket_id, capability, _serial, h = _paid_ticket_flow(client, demo_store)
    store.execute(
        "UPDATE tickets SET status = 'void', voided_at = ? WHERE id = ?",
        (time_to_text(datetime.now(timezone.utc)), ticket_id),
    )
    r = client.post(
        "/api/scan",
        json={"event_id": event_id, "capability": capability},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["result"] == "invalid"
    assert "revoked" in r.json()["reason"].lower() or "not valid" in r.json()["reason"].lower()


def test_sectorized_controls_have_independent_deduplication(client: TestClient, demo_store):
    event_id, ticket_id, capability, _serial, headers = _paid_ticket_flow(client, demo_store)
    base = {"event_id": event_id, "capability": capability, "device_id": "terminal-a"}

    entrance = client.post(
        "/api/scan", json={**base, "control_type": "event_entry"}, headers=headers
    )
    meal = client.post(
        "/api/scan", json={**base, "control_type": "food_access"}, headers=headers
    )
    entrance_again = client.post(
        "/api/scan", json={**base, "control_type": "event_entry"}, headers=headers
    )

    assert entrance.json()["result"] == "admitted"
    assert meal.json()["result"] == "admitted"
    assert entrance_again.json()["result"] == "duplicate"
    assert entrance_again.json()["ticket_id"] == ticket_id
    assert entrance_again.json()["first_scan"]["device_id"] == "terminal-a"

    stats = client.get(f"/api/events/{event_id}/stats", headers=headers)
    assert stats.status_code == 200, stats.text
    assert stats.json()["stats"]["admitted"] == 1
    assert stats.json()["stats"]["admitted_by_control"]["event_entry"] == 1
    assert stats.json()["stats"]["admitted_by_control"]["food_access"] == 1


def test_scan_bundle_exposes_signed_tickets_and_explicit_rights(client: TestClient, demo_store):
    event_id, ticket_id, capability, _serial, headers = _paid_ticket_flow(client, demo_store)

    response = client.get(f"/api/events/{event_id}/scan-bundle", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["event_id"] == event_id
    assert body["issuer_keys"]["keys"]
    ticket = next(item for item in body["tickets"] if item["ticket_id"] == ticket_id)
    assert ticket["capability"] == capability
    assert ticket["scan_rights"] == {
        "event_entry": True,
        "food_access": True,
        "merch_pickup": True,
        "after_entry": True,
    }


def test_control_without_explicit_right_is_rejected(client: TestClient, demo_store):
    store, *_ = demo_store
    event_id, ticket_id, capability, _serial, headers = _paid_ticket_flow(client, demo_store)
    ticket = store.fetchone("SELECT ticket_type_id FROM tickets WHERE id = ?", (ticket_id,))
    store.execute(
        "UPDATE ticket_types SET access_food = FALSE WHERE id = ?",
        (ticket["ticket_type_id"],),
    )

    response = client.post(
        "/api/scan",
        json={
            "event_id": event_id,
            "capability": capability,
            "control_type": "food_access",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["result"] == "not_authorized"
    admitted = store.fetchone(
        "SELECT 1 FROM admissions WHERE ticket_id = ? AND control_type = 'food_access'",
        (ticket_id,),
    )
    assert admitted is None


def test_offline_sync_is_idempotent_and_surfaces_cross_device_conflict(
    client: TestClient, demo_store
):
    event_id, ticket_id, capability, _serial, headers = _paid_ticket_flow(client, demo_store)
    scanned_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def operation(operation_id: str, device_id: str) -> dict:
        return {
            "operation_id": operation_id,
            "capability": capability,
            "device_id": device_id,
            "gate_id": device_id,
            "scanned_at": scanned_at,
            "reported_result": "admitted",
            "control_type": "event_entry",
        }

    first_body = {"event_id": event_id, "operations": [operation("op-a", "terminal-a")]}
    first = client.post("/api/scan/sync", json=first_body, headers=headers)
    replay = client.post("/api/scan/sync", json=first_body, headers=headers)
    second = client.post(
        "/api/scan/sync",
        json={"event_id": event_id, "operations": [operation("op-b", "terminal-b")]},
        headers=headers,
    )

    assert first.status_code == 200, first.text
    assert first.json()["results"][0]["result"] == "admitted"
    assert replay.json()["results"][0]["replayed"] is True
    assert second.json()["results"][0]["result"] == "duplicate"
    assert second.json()["results"][0]["reported_result"] == "admitted"

    conflicts = client.get(f"/api/events/{event_id}/admission-conflicts", headers=headers)
    assert conflicts.status_code == 200
    conflict = conflicts.json()["conflicts"][0]
    assert conflict["ticket_id"] == ticket_id
    assert conflict["control_type"] == "event_entry"
    assert conflict["device_count"] == 2

    tampered = capability[:-1] + ("A" if capability[-1] != "A" else "B")
    rejected = client.post(
        "/api/scan/sync",
        json={
            "event_id": event_id,
            "operations": [
                {**operation("op-tampered", "terminal-c"), "capability": tampered}
            ],
        },
        headers=headers,
    )
    assert rejected.json()["results"][0]["result"] == "invalid"
    stored = demo_store[0].fetchone(
        "SELECT COUNT(*) AS n FROM admissions WHERE operation_id = ?",
        ("op-tampered",),
    )
    assert stored["n"] == 0
