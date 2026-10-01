"""GET /api/checkin/snapshot, /logs and /health (TDEV-54)."""

from __future__ import annotations

import gzip
import json

import pytest
from checkin_fixtures import applied_schema, checkin_rt, clock, commit_3a, db  # noqa: F401  (fixtures)
from checkin_helpers import add_rule, make_world, scan_body

SNAP = "/api/checkin/snapshot"
LOGS = "/api/checkin/logs"


@pytest.fixture()
def world(client, db, checkin_rt, commit_3a):
    return make_world(client, db, commit_3a, type_names=("GA", "VIP"), per_type=2)  # 2 + 2 tickets


def snap(client, world, headers=None, **params):
    return client.get(SNAP, params={"event_id": world.event_id, **params}, headers=headers or world.scanner)


def by_id(body):
    return {e["ticket_id"]: e for e in body["entitlements"]}


# ── Snapshot ────────────────────────────────────────────────────────────────


def test_full_snapshot(client, world):
    r = snap(client, world)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["event_id"] == world.event_id and body["schema_version"] == 1
    assert body["snapshot_version"] > 0 and body["has_more"] is False and body["next_cursor"] is None
    ents = by_id(body)
    assert set(ents) == {t["id"] for t in world.tickets}
    for t in world.tickets:
        e = ents[t["id"]]
        assert e["serial"] == t["serial"] and e["status"] == "valid"
        assert e["stations"] == ["EVENT_ENTRY"]  # the cautious default
        assert e["uses"] == {} and e["ticket_type_id"] == t["ticket_type_id"]
    assert body["issuer_keys"] and all(k.startswith("k_") for k in body["issuer_keys"])
    assert r.headers["ETag"].startswith('"')


def test_snapshot_contains_no_personal_data(client, world):
    text = snap(client, world).text
    assert "@example.com" not in text and "Buyer" not in text
    for t in world.tickets:
        assert t["capability"] not in text


def test_rules_change_the_stations_and_delta_returns_only_changed_rows(client, db, world):
    v1 = snap(client, world).json()["snapshot_version"]
    add_rule(db, world, "VIP", "FOOD_ACCESS", 1)
    add_rule(db, world, "VIP", "AFTER_ENTRY", 1)
    delta = snap(client, world, since_version=v1).json()
    vip = {t["id"] for t in world.tickets if t["type_name"] == "VIP"}
    assert set(by_id(delta)) == vip
    for e in delta["entitlements"]:
        assert e["stations"] == ["AFTER_ENTRY", "EVENT_ENTRY", "FOOD_ACCESS"]
    assert delta["snapshot_version"] > v1 and delta["since_version"] == v1


def test_explicit_rule_can_remove_the_default_entry(client, db, world):
    add_rule(db, world, "GA", "EVENT_ENTRY", 0)
    ga = [t for t in world.tickets if t["type_name"] == "GA"][0]
    assert by_id(snap(client, world).json())[ga["id"]]["stations"] == []


def test_consumptions_appear_in_the_delta(client, db, world):
    v1 = snap(client, world).json()["snapshot_version"]
    ticket = world.tickets[0]
    r = client.post("/api/checkin/scan", json=scan_body(world, ticket, world.terminal()), headers=world.scanner)
    assert r.json()["server_decision"] == "valid"
    delta = snap(client, world, since_version=v1).json()
    assert list(by_id(delta)) == [ticket["id"]]
    assert delta["entitlements"][0]["uses"] == {"EVENT_ENTRY": 1}
    nothing = snap(client, world, since_version=delta["snapshot_version"]).json()
    assert nothing["entitlements"] == []


def test_revoked_ticket_has_no_station(client, db, world):
    t = world.tickets[0]
    db.execute("UPDATE tickets SET status = 'void', voided_at = '2020-01-01T00:00:00Z' WHERE id = %s", (t["id"],))
    e = by_id(snap(client, world).json())[t["id"]]
    assert e["status"] == "void" and e["stations"] == []


def test_etag_and_not_modified(client, world):
    first = snap(client, world)
    etag = first.headers["ETag"]
    again = client.get(
        SNAP, params={"event_id": world.event_id}, headers={**world.scanner, "If-None-Match": etag}
    )
    assert again.status_code == 304 and again.content == b""


def test_gzip_is_served_and_identical_to_plain(client, world):
    plain = snap(client, world, headers={**world.scanner, "Accept-Encoding": "identity"})
    zipped = snap(client, world, headers={**world.scanner, "Accept-Encoding": "gzip"})
    assert plain.headers.get("content-encoding") is None
    assert zipped.headers["content-encoding"] == "gzip"
    assert zipped.json()["entitlements"] == plain.json()["entitlements"]


def test_cached_gzip_bytes_decompress_to_the_plain_body(world, checkin_rt):
    from checkin import service

    with checkin_rt.pool.connection() as conn:
        _etag, raw, packed = service.snapshot(
            checkin_rt, conn, event_id=world.event_id, since_version=0, cursor=None, limit=None
        )
    assert packed[:2] == b"\x1f\x8b" and gzip.decompress(packed) == raw
    assert len(packed) < len(raw)


def test_cursor_pagination_pins_the_version_and_loses_nothing(client, world):
    seen, cursor, pages, pin = [], None, 0, None
    while True:
        params = {"limit": 3}
        if cursor:
            params["cursor"] = cursor
        body = snap(client, world, **params).json()
        pages += 1
        pin = pin or body["snapshot_version"]
        assert body["snapshot_version"] == pin
        seen += [e["ticket_id"] for e in body["entitlements"]]
        cursor = body["next_cursor"]
        if not body["has_more"]:
            break
        assert cursor
    assert pages == 2 and len(seen) == len(set(seen)) == 4


def test_invalid_cursor_and_params(client, world):
    assert snap(client, world, cursor="%%%").status_code == 400
    assert snap(client, world, since_version=-1).status_code == 400
    assert client.get(SNAP, headers=world.scanner).status_code == 400  # event_id is required


def test_snapshot_requires_a_scanner_role(client, world):
    assert client.get(SNAP, params={"event_id": world.event_id}).status_code == 401
    assert snap(client, world, headers=world.outsider).status_code == 403
    assert snap(client, world, headers=world.admin).status_code == 200


# ── Logs ────────────────────────────────────────────────────────────────────


def seed_scans(client, world, n=3):
    term = world.terminal()
    for t in world.tickets[:n]:
        assert client.post(
            "/api/checkin/scan", json=scan_body(world, t, term), headers=world.scanner
        ).status_code == 200
    return term


def test_logs_are_for_supervisors_only(client, world):
    seed_scans(client, world)
    assert client.get(LOGS, params={"event_id": world.event_id}).status_code == 401
    assert client.get(LOGS, params={"event_id": world.event_id}, headers=world.scanner).status_code == 403
    assert client.get(LOGS, params={"event_id": world.event_id}, headers=world.outsider).status_code == 403
    assert client.get(LOGS, params={"event_id": world.event_id}, headers=world.admin).status_code == 200


def test_logs_listing_filters_and_no_qr(client, world):
    term = seed_scans(client, world, 3)
    r = client.get(LOGS, params={"event_id": world.event_id}, headers=world.admin).json()
    assert len(r["logs"]) == 3 and r["next_cursor"] is None
    for log in r["logs"]:
        assert "capability" not in log and "payload_hash" not in log
        assert log["station"] == "EVENT_ENTRY" and log["server_decision"] == "valid"
    assert all(t["capability"] not in json.dumps(r) for t in world.tickets)
    f = lambda **p: client.get(LOGS, params={"event_id": world.event_id, **p}, headers=world.admin).json()["logs"]
    assert len(f(terminal_id=term)) == 3
    assert f(terminal_id=world.terminal()) == []
    assert len(f(ticket_id=world.tickets[0]["id"])) == 1
    assert f(station="FOOD_ACCESS") == [] and len(f(station="eventEntry")) == 3
    assert client.get(LOGS, params={"event_id": world.event_id, "station": "!!"}, headers=world.admin).status_code == 400


def test_logs_cursor_pagination(client, world):
    seed_scans(client, world, 3)
    page1 = client.get(LOGS, params={"event_id": world.event_id, "limit": 2}, headers=world.admin).json()
    assert len(page1["logs"]) == 2 and page1["next_cursor"] is not None
    page2 = client.get(
        LOGS, params={"event_id": world.event_id, "limit": 2, "cursor": page1["next_cursor"]}, headers=world.admin
    ).json()
    assert len(page2["logs"]) == 1 and page2["next_cursor"] is None
    ids = [l["log_id"] for l in page1["logs"] + page2["logs"]]
    assert ids == sorted(ids) and len(set(ids)) == 3


def test_logs_are_scoped_to_the_event(client, db, world, commit_3a):
    seed_scans(client, world, 2)
    other = make_world(client, db, commit_3a)
    assert client.get(LOGS, params={"event_id": other.event_id}, headers=other.admin).json()["logs"] == []
    assert client.get(LOGS, params={"event_id": other.event_id}, headers=world.admin).status_code == 403


# ── Health ──────────────────────────────────────────────────────────────────


def test_health(client, checkin_rt):
    r = client.get("/api/checkin/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["db"] == "ok"
    assert set(body["pool"]) == {"size", "available", "waiting"}
