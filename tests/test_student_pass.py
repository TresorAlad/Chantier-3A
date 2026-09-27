"""Free student pass tier and checkout."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from conftest import seed_published_event
from events import service as events_svc
from events.passes import (
    PASS_TIER_PRICE_MINOR,
    STANDARD_PASS_TICKET_TYPE_BODY,
    STUDENT_PASS_TICKET_TYPE_BODY,
    VIP_PASS_TICKET_TYPE_BODY,
)


def test_pass_tier_catalog(client: TestClient):
    """Student, standard and VIP passes are listed with catalog prices."""
    resp = client.get("/api/pass-tiers")
    assert resp.status_code == 200
    tiers = resp.json()["pass_tiers"]
    assert len(tiers) == 3
    by_id = {t["id"]: t for t in tiers}
    assert by_id["student"]["price_minor"] == 0
    assert by_id["standard"]["price_minor"] == PASS_TIER_PRICE_MINOR["standard"]
    assert by_id["vip"]["price_minor"] == PASS_TIER_PRICE_MINOR["vip"]


def test_standard_and_vip_pass_can_be_created(demo_store):
    store, _cfg, _services, _app = demo_store
    fx = seed_published_event(store)
    std = events_svc.create_ticket_type(store, fx["event_id"], STANDARD_PASS_TICKET_TYPE_BODY)
    vip = events_svc.create_ticket_type(store, fx["event_id"], VIP_PASS_TICKET_TYPE_BODY)
    assert std["pass_tier"] == "standard"
    assert std["price_minor"] == 2000
    assert vip["pass_tier"] == "vip"
    assert vip["price_minor"] == 5000


def test_student_pass_requires_registration(client: TestClient, demo_store):
    """Student pass checkout rejects incomplete registration."""
    store, _cfg, _services, _app = demo_store
    fx = seed_published_event(store)
    tt = events_svc.create_ticket_type(store, fx["event_id"], STUDENT_PASS_TICKET_TYPE_BODY)
    resp = client.post(
        "/api/orders",
        json={
            "event_id": fx["event_id"],
            "items": [{"ticket_type_id": tt["id"], "quantity": 1}],
            "buyer": {"email": "incomplete@school.edu"},
        },
    )
    assert resp.status_code == 400


def test_free_student_pass_checkout(client: TestClient, demo_store):
    """Buyers obtain a student pass without a payment step."""
    store, _cfg, _services, _app = demo_store
    fx = seed_published_event(store)
    tt = events_svc.create_ticket_type(store, fx["event_id"], STUDENT_PASS_TICKET_TYPE_BODY)
    assert tt["pass_tier"] == "student"
    assert tt["price_minor"] == 0

    order = client.post(
        "/api/orders",
        json={
            "event_id": fx["event_id"],
            "items": [{"ticket_type_id": tt["id"], "quantity": 1}],
            "buyer": {
                "email": "student@school.edu",
                "first_name": "Awa",
                "last_name": "Diallo",
                "school_name": "Universite Cheikh Anta Diop",
                "motivation": "Suivre les masterclasses et rencontrer les mentors.",
                "wish": "Mieux comprendre l'entrepreneuriat tech.",
            },
        },
    )
    assert order.status_code == 201, order.text
    body = order.json()
    assert body["order"]["total_minor"] == 0
    assert body["order"]["provider"] == "free"

    verify = client.post("/api/payments/verify", json={"reference": body["order"]["id"]})
    assert verify.status_code == 200, verify.text
    assert verify.json()["order"]["status"] == "paid"
    tickets = verify.json()["tickets"]
    assert len(tickets) == 1
    assert tickets[0]["serial"].startswith("TDEV-")
    reg = verify.json()["order"]["registration"]
    assert reg["school_name"] == "Universite Cheikh Anta Diop"
    assert reg["motivation"]
    assert reg["wish"]
