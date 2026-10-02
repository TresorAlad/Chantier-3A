"""POST /api/checkin/scan on a real PostgreSQL (TDEV-54)."""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta

import psycopg
import pytest
from checkin_fixtures import applied_schema, checkin_rt, clock, commit_3a, db  # noqa: F401  (fixtures)
from checkin_helpers import add_rule, make_world, run_parallel, scan_body

URL = "/api/checkin/scan"


def post(client, world, ticket, terminal, station="EVENT_ENTRY", headers=None, **extra):
    return client.post(
        URL, json=scan_body(world, ticket, terminal, station, **extra), headers=headers or world.scanner
    )


@pytest.fixture()
def world(client, db, checkin_rt, commit_3a):
    return make_world(client, db, commit_3a)


def rows(db, sql, *args):
    return db.execute(sql, args).fetchall()


# ── Nominal flows ───────────────────────────────────────────────────────────


def test_first_scan_is_admitted_and_journaled(client, db, world):
    t, term = world.tickets[0], world.terminal()
    r = post(client, world, t, term)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "accepted"
    assert body["server_decision"] == "valid"
    assert body["ticket_id"] == t["id"] and body["serial"] == t["serial"]
    assert body["station"] == "EVENT_ENTRY" and body["use_index"] == 0

    logs = rows(db, "SELECT * FROM scan_logs")
    assert len(logs) == 1
    log = logs[0]
    assert log["is_claim"] is True and log["server_decision"] == "valid"
    assert log["connection_status"] == "online" and log["reported_decision"] is None
    assert log["capability_verified"] is True and log["clock_offset_ms"] == 0
    assert str(log["terminal_id"]) == term and log["ticket_id"] == t["id"]
    cons = rows(db, "SELECT * FROM station_consumptions")
    assert len(cons) == 1 and cons[0]["use_index"] == 0 and cons[0]["winning_log_id"] == log["log_id"]
    assert rows(db, "SELECT 1 FROM scan_conflicts") == []
    term_row = rows(db, "SELECT * FROM checkin_terminals")[0]
    assert str(term_row["terminal_id"]) == term and term_row["event_id"] == world.event_id


def test_second_scan_same_station_is_already_scanned(client, db, world):
    t = world.tickets[0]
    first = post(client, world, t, world.terminal()).json()
    second = post(client, world, t, world.terminal())
    assert second.status_code == 200
    body = second.json()
    assert body["server_decision"] == "already_scanned"
    assert body["status"] == "accepted"  # refusing a duplicate is the nominal outcome, not a conflict
    assert body["use_index"] is None and body["first_scanned_at"] is not None
    assert first["server_decision"] == "valid"
    logs = rows(db, "SELECT is_claim, server_decision FROM scan_logs ORDER BY log_id")
    assert [(r["is_claim"], r["server_decision"]) for r in logs] == [(True, "valid"), (False, "already_scanned")]
    assert len(rows(db, "SELECT 1 FROM station_consumptions")) == 1
    assert rows(db, "SELECT 1 FROM scan_conflicts") == []


def test_second_station_is_allowed_when_a_rule_exists(client, db, world):
    add_rule(db, world, "GA", "FOOD_ACCESS", 1)
    t, term = world.tickets[0], world.terminal()
    assert post(client, world, t, term, "EVENT_ENTRY").json()["server_decision"] == "valid"
    assert post(client, world, t, term, "FOOD_ACCESS").json()["server_decision"] == "valid"
    assert post(client, world, t, term, "FOOD_ACCESS").json()["server_decision"] == "already_scanned"
    cons = rows(db, "SELECT station FROM station_consumptions ORDER BY station")
    assert [c["station"] for c in cons] == ["EVENT_ENTRY", "FOOD_ACCESS"]


def test_camel_case_station_from_the_3b_app_is_accepted(client, db, world):
    r = post(client, world, world.tickets[0], world.terminal(), "eventEntry")
    assert r.status_code == 200 and r.json()["station"] == "EVENT_ENTRY"


def test_max_uses_two_allows_a_second_entry(client, db, world):
    add_rule(db, world, "GA", "EVENT_ENTRY", 2)
    t = world.tickets[0]
    decisions = [post(client, world, t, world.terminal()).json()["server_decision"] for _ in range(3)]
    assert decisions == ["valid", "valid", "already_scanned"]
    assert [c["use_index"] for c in rows(db, "SELECT use_index FROM station_consumptions ORDER BY use_index")] == [0, 1]


# ── Refusals ────────────────────────────────────────────────────────────────


def test_station_without_rule_is_not_authorized(client, db, world):
    r = post(client, world, world.tickets[0], world.terminal(), "FOOD_ACCESS")
    assert r.status_code == 200
    assert r.json()["server_decision"] == "not_authorized" and r.json()["reason"] == "station_not_allowed"
    assert rows(db, "SELECT 1 FROM station_consumptions") == []
    log = rows(db, "SELECT is_claim, server_decision FROM scan_logs")[0]
    assert log["is_claim"] is False and log["server_decision"] == "not_authorized"


def test_explicit_deny_on_entry(client, db, world):
    add_rule(db, world, "GA", "EVENT_ENTRY", 0)
    assert post(client, world, world.tickets[0], world.terminal()).json()["server_decision"] == "not_authorized"


def test_revoked_ticket_is_refused(client, db, world):
    t = world.tickets[0]
    db.execute("UPDATE tickets SET status = 'void', voided_at = '2020-01-01T00:00:00Z' WHERE id = %s", (t["id"],))
    body = post(client, world, t, world.terminal()).json()
    assert body["server_decision"] == "revoked"
    assert rows(db, "SELECT 1 FROM station_consumptions") == []


def test_wrong_event(client, db, world, commit_3a):
    other = client.post(
        "/api/events",
        json={
            "org_id": world.org_id,
            "slug": f"other-{uuid.uuid4().hex[:6]}",
            "title": "Other",
            "starts_at": "2026-01-01T00:00:00Z",
            "ends_at": "2036-01-01T00:00:00Z",
        },
        headers=world.admin,
    )
    assert other.status_code == 201, other.text
    commit_3a()
    other_id = other.json()["event"]["id"]
    body = {**scan_body(world, world.tickets[0], world.terminal()), "event_id": other_id}
    r = client.post(URL, json=body, headers=world.scanner)
    assert r.status_code == 200
    assert r.json()["server_decision"] == "wrong_event"
    assert rows(db, "SELECT 1 FROM station_consumptions") == []


def test_expired_capability(client, db, world, clock):
    clock.shift = timedelta(hours=10)  # the event ends 8 h from now
    r = post(client, world, world.tickets[0], world.terminal())
    assert r.json()["server_decision"] == "expired"
    log = rows(db, "SELECT ticket_id, capability_verified FROM scan_logs")[0]
    assert log["capability_verified"] is True and log["ticket_id"] == world.tickets[0]["id"]


def test_not_yet_valid_capability(client, db, world, clock):
    clock.shift = -timedelta(hours=3)
    assert post(client, world, world.tickets[0], world.terminal()).json()["server_decision"] == "not_yet_valid"


def test_forged_signature_is_invalid_and_not_attributed_to_a_ticket(client, db, world):
    t = dict(world.tickets[0])
    head, payload, sig = t["capability"].split(".")
    t["capability"] = ".".join([head, payload, ("A" if sig[0] != "A" else "B") + sig[1:]])
    body = post(client, world, t, world.terminal()).json()
    assert body["server_decision"] == "invalid" and body["reason"] == "bad_signature"
    log = rows(db, "SELECT ticket_id, capability_verified, is_claim FROM scan_logs")[0]
    assert log["ticket_id"] is None and log["capability_verified"] is False and log["is_claim"] is False


def test_tampered_payload_is_invalid(client, db, world):
    t = dict(world.tickets[0])
    head, payload, sig = t["capability"].split(".")
    t["capability"] = ".".join([head, payload[:-2] + ("AA" if payload[-2:] != "AA" else "BB"), sig])
    body = post(client, world, t, world.terminal()).json()
    assert body["server_decision"] == "invalid"


@pytest.mark.parametrize("garbage", ["garbage", "chantier3a.a.b", "chantier3a.e30.e30"])
def test_garbage_capability_is_invalid(client, db, world, garbage):
    t = {**world.tickets[0], "capability": garbage}
    body = post(client, world, t, world.terminal()).json()
    assert body["server_decision"] == "invalid"
    assert rows(db, "SELECT 1 FROM station_consumptions") == []


# ── Idempotency ─────────────────────────────────────────────────────────────


def test_replay_with_same_operation_id_changes_nothing(client, db, world):
    t, term, op = world.tickets[0], world.terminal(), str(uuid.uuid4())
    a = post(client, world, t, term, operation_id=op).json()
    b = post(client, world, t, term, operation_id=op).json()
    assert a["server_decision"] == "valid" and a["status"] == "accepted"
    assert b["status"] == "already_processed" and b["server_decision"] == "valid"
    assert b["operation_id"] == op
    assert len(rows(db, "SELECT 1 FROM scan_logs")) == 1
    assert len(rows(db, "SELECT 1 FROM station_consumptions")) == 1


def test_reusing_an_operation_id_for_another_scan_is_rejected(client, db, world):
    add_rule(db, world, "GA", "FOOD_ACCESS", 1)
    t, term, op = world.tickets[0], world.terminal(), str(uuid.uuid4())
    assert post(client, world, t, term, "EVENT_ENTRY", operation_id=op).status_code == 200
    r = post(client, world, t, term, "FOOD_ACCESS", operation_id=op)
    assert r.status_code == 409 and r.json()["error"]["code"] == "operation_id_reuse"
    assert len(rows(db, "SELECT 1 FROM scan_logs")) == 1


# ── Validation, authentication, terminals ───────────────────────────────────


def test_unknown_station_is_rejected(client, db, world):
    for bad in ("GHOST_STATION", "not a station!"):
        r = post(client, world, world.tickets[0], world.terminal(), bad)
        assert r.status_code == 400 and r.json()["error"]["code"] == "unknown_station", bad
    assert rows(db, "SELECT 1 FROM scan_logs") == []


def test_invalid_body_uses_the_stable_error_envelope(client, world):
    r = client.post(URL, json={"event_id": world.event_id, "terminal_id": "not-a-uuid"}, headers=world.scanner)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_request"
    assert "not-a-uuid" not in r.text  # the submitted value is never echoed


def test_authentication_and_roles(client, db, world):
    t, term = world.tickets[0], world.terminal()
    assert client.post(URL, json=scan_body(world, t, term)).status_code == 401
    r = post(client, world, t, term, headers=world.outsider)
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"
    assert post(client, world, t, term, headers=world.admin).status_code == 200  # admin >= scanner
    bad = client.post(URL, json=scan_body(world, t, term), headers={"Authorization": "Bearer nope"})
    assert bad.status_code == 401


def test_revoked_terminal_is_refused_and_old_scans_are_kept(client, db, world):
    add_rule(db, world, "GA", "FOOD_ACCESS", 1)
    t, term = world.tickets[0], world.terminal()
    assert post(client, world, t, term).status_code == 200
    db.execute("UPDATE checkin_terminals SET revoked_at = now() WHERE terminal_id = %s", (term,))
    r = post(client, world, t, term, "FOOD_ACCESS")
    assert r.status_code == 403 and r.json()["error"]["code"] == "terminal_revoked"
    assert len(rows(db, "SELECT 1 FROM scan_logs")) == 1  # the earlier scan is still journaled


def test_terminal_bound_to_another_event_is_refused(client, db, world, commit_3a):
    term = world.terminal()
    assert post(client, world, world.tickets[0], term).status_code == 200
    other = client.post(
        "/api/events",
        json={
            "org_id": world.org_id,
            "slug": f"e2-{uuid.uuid4().hex[:6]}",
            "title": "E2",
            "starts_at": "2026-01-01T00:00:00Z",
            "ends_at": "2036-01-01T00:00:00Z",
        },
        headers=world.admin,
    ).json()["event"]["id"]
    commit_3a()
    r = client.post(URL, json={**scan_body(world, world.tickets[0], term), "event_id": other}, headers=world.scanner)
    assert r.status_code == 403 and r.json()["error"]["code"] == "terminal_event_mismatch"


def test_rate_limit_per_terminal(client, db, world, checkin_rt):
    checkin_rt.limiter._max = 2
    t, term = world.tickets[0], world.terminal()
    codes = [post(client, world, t, term).status_code for _ in range(4)]
    assert codes[:2] == [200, 200] and codes[2:] == [429, 429]
    assert post(client, world, t, world.terminal()).status_code == 200  # another terminal is unaffected


# ── Invariants ──────────────────────────────────────────────────────────────


def test_the_journal_is_append_only(client, db, world):
    post(client, world, world.tickets[0], world.terminal())
    with pytest.raises(psycopg.errors.RaiseException):
        db.execute("UPDATE scan_logs SET server_reason = 'tampered'")
    with pytest.raises(psycopg.errors.RaiseException):
        db.execute("DELETE FROM scan_logs")
    assert len(rows(db, "SELECT 1 FROM scan_logs")) == 1


def test_the_raw_qr_is_never_stored_nor_logged(client, db, world, caplog):
    t = world.tickets[0]
    caplog.set_level(logging.DEBUG)
    post(client, world, t, world.terminal())
    post(client, world, {**t, "capability": t["capability"][:-3] + "AAA"}, world.terminal())
    fragment = t["capability"].split(".")[1][:24]  # a slice of the signed payload
    dump = "".join(
        r["j"] for r in rows(db, "SELECT row_to_json(l)::text AS j FROM scan_logs l")
    ) + "".join(r["j"] for r in rows(db, "SELECT row_to_json(c)::text AS j FROM scan_conflicts c"))
    assert fragment not in dump and t["capability"] not in dump
    assert fragment not in caplog.text


def test_concurrent_scans_of_the_same_ticket_admit_exactly_one(client, db, world):
    t = world.tickets[0]
    terminals = [world.terminal() for _ in range(8)]
    results = run_parallel(8, lambda i: post(client, world, t, terminals[i]))
    assert [r.status_code for r in results] == [200] * 8
    decisions = sorted(r.json()["server_decision"] for r in results)
    assert decisions == ["already_scanned"] * 7 + ["valid"]
    assert len(rows(db, "SELECT 1 FROM station_consumptions")) == 1
    assert len(rows(db, "SELECT 1 FROM scan_logs")) == 8
    assert len(rows(db, "SELECT 1 FROM scan_logs WHERE is_claim")) == 1


def test_a_database_error_does_not_poison_later_requests(client, db, world):
    """Regression guard for 3A bug 2: after a duplicate the module keeps serving."""
    t, term = world.tickets[0], world.terminal()
    for _ in range(5):
        assert post(client, world, t, term).status_code == 200
    assert client.get("/api/checkin/health").json()["status"] == "ok"
