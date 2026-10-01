"""POST /api/checkin/sync: idempotence, convergence, conflict types, partial batches (TDEV-55)."""

from __future__ import annotations

import dataclasses
import itertools
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from checkin_fixtures import applied_schema, checkin_rt, clock, commit_3a, db  # noqa: F401  (fixtures)
from checkin_helpers import add_rule, iso, make_world, op, run_parallel, scan_body, sync_body

SYNC = "/api/checkin/sync"
S = timedelta(seconds=1)


@pytest.fixture()
def now(checkin_rt):
    """Frozen clock: with ``device_sent_at == now`` the batch offset is exactly 0."""
    frozen = datetime.now(timezone.utc)
    checkin_rt.clock = lambda: frozen
    return frozen


@pytest.fixture()
def world(client, db, checkin_rt, commit_3a):
    return make_world(client, db, commit_3a, per_type=8)  # 8 tickets


def sync(client, world, terminal, ops, *, sent, headers=None, **extra):
    return client.post(SYNC, json=sync_body(world, terminal, ops, sent_at=sent, **extra), headers=headers or world.scanner)


def rows(db, sql, *args):
    return db.execute(sql, args).fetchall()


def winner_terminal(db, ticket, station="EVENT_ENTRY", use_index=0):
    r = rows(
        db,
        "SELECT l.terminal_id FROM station_consumptions c JOIN scan_logs l ON l.log_id = c.winning_log_id "
        "WHERE c.ticket_id = %s AND c.station = %s AND c.use_index = %s",
        ticket["id"],
        station,
        use_index,
    )
    return str(r[0]["terminal_id"]) if r else None


def conflicts_of(db, ticket):
    return rows(db, "SELECT * FROM scan_conflicts WHERE ticket_id = %s ORDER BY conflict_id", ticket["id"])


# ── Nominal ─────────────────────────────────────────────────────────────────


def test_a_valid_offline_scan_is_accepted_and_journaled(client, db, world, now):
    t, term = world.tickets[0], world.terminal()
    r = sync(client, world, term, [op(t, at=now - 30 * S, decision="valid")], sent=now, pending_count=4)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"] == {"accepted": 1, "already_processed": 0, "conflict": 0, "rejected": 0}
    assert body["results"][0]["status"] == "accepted" and body["results"][0]["server_decision"] == "valid"
    assert body["clock_offset_ms"] == 0
    log = rows(db, "SELECT * FROM scan_logs")[0]
    assert log["connection_status"] == "offline_synced" and log["is_claim"] is True
    assert log["reported_decision"] == "valid" and log["server_decision"] == "valid"
    assert log["corrected_evaluated_at"] == now - 30 * S and log["clock_offset_ms"] == 0
    assert winner_terminal(db, t) == term
    term_row = rows(db, "SELECT * FROM checkin_terminals")[0]
    assert term_row["pending_count"] == 4 and term_row["last_batch_at"] == now


def test_camel_case_values_from_the_3b_app(client, db, world, now):
    t = world.tickets[0]
    r = sync(client, world, world.terminal(), [op(t, at=now - 5 * S, station="eventEntry", decision="valid")], sent=now)
    assert r.json()["results"][0]["status"] == "accepted"
    assert rows(db, "SELECT station FROM scan_logs")[0]["station"] == "EVENT_ENTRY"


def test_the_server_never_trusts_the_terminal_decision(client, db, world, now):
    revoked, plain = world.tickets[0], world.tickets[1]
    db.execute("UPDATE tickets SET status = 'void', voided_at = %s WHERE id = %s", (iso(now - 600 * S), revoked["id"]))
    r = sync(
        client,
        world,
        world.terminal(),
        [
            op(revoked, at=now - 30 * S, decision="valid"),  # terminal says valid, server says revoked
            op(plain, at=now - 20 * S, decision="alreadyScanned"),  # evidence only, nobody was admitted
        ],
        sent=now,
    ).json()["results"]
    assert (r[0]["status"], r[0]["server_decision"]) == ("conflict", "revoked")
    logs = {str(l["ticket_id"]): l for l in rows(db, "SELECT * FROM scan_logs")}
    assert logs[revoked["id"]]["reported_decision"] == "valid" and logs[revoked["id"]]["server_decision"] == "revoked"
    assert logs[plain["id"]]["reported_decision"] == "alreadyScanned"  # stored verbatim
    assert logs[plain["id"]]["is_claim"] is False and logs[plain["id"]]["reported_valid"] is False
    assert winner_terminal(db, revoked) is None and winner_terminal(db, plain) is None
    assert conflicts_of(db, plain) == []  # an "already scanned" report is evidence, not a conflict


# ── Idempotence ─────────────────────────────────────────────────────────────


def test_replaying_the_same_batch_changes_nothing(client, db, world, now):
    t1, t2 = world.tickets[0], world.tickets[1]
    a, b = world.terminal(), world.terminal()
    sync(client, world, a, [op(t1, at=now - 50 * S)], sent=now)
    batch = [op(t1, at=now - 40 * S), op(t2, at=now - 30 * S)]  # the first one loses to terminal A's scan
    body = sync_body(world, b, batch, sent_at=now)
    first = client.post(SYNC, json=body, headers=world.scanner).json()
    snapshot = (
        len(rows(db, "SELECT 1 FROM scan_logs")),
        len(rows(db, "SELECT 1 FROM station_consumptions")),
        len(rows(db, "SELECT 1 FROM scan_conflicts")),
    )
    again = client.post(SYNC, json=body, headers=world.scanner).json()
    assert again["summary"] == {"accepted": 0, "already_processed": 2, "conflict": 0, "rejected": 0}
    for f, g in zip(first["results"], again["results"]):
        assert g["status"] == "already_processed"
        assert g["server_decision"] == f["server_decision"] and g["operation_id"] == f["operation_id"]
    assert again["results"][0]["conflict"]["type"] == "CROSS_TERMINAL_DOUBLE_ADMISSION"  # the original outcome
    assert snapshot == (
        len(rows(db, "SELECT 1 FROM scan_logs")),
        len(rows(db, "SELECT 1 FROM station_consumptions")),
        len(rows(db, "SELECT 1 FROM scan_conflicts")),
    )


def test_a_retried_batch_with_new_operations_only_processes_the_new_ones(client, db, world, now):
    t1, t2 = world.tickets[0], world.tickets[1]
    term = world.terminal()
    a = op(t1, at=now - 50 * S)
    sync(client, world, term, [a], sent=now)
    r = sync(client, world, term, [a, op(t2, at=now - 40 * S)], sent=now + S).json()["results"]
    assert [x["status"] for x in r] == ["already_processed", "accepted"]
    assert len(rows(db, "SELECT 1 FROM scan_logs")) == 2


def test_operation_id_reuse_and_in_batch_duplicates(client, db, world, now):
    t1, t2 = world.tickets[0], world.tickets[1]
    term = world.terminal()
    a = op(t1, at=now - 50 * S)
    same = dict(a)
    other = {**a, "ticket_id": t2["id"]}
    r = sync(client, world, term, [a, same, other], sent=now).json()["results"]
    assert [x["status"] for x in r] == ["accepted", "already_processed", "rejected"]
    assert r[2]["error_code"] == "operation_id_reuse"
    later = sync(client, world, term, [{**a, "ticket_id": t2["id"]}], sent=now).json()["results"][0]
    assert later["status"] == "rejected" and later["error_code"] == "operation_id_reuse"
    assert len(rows(db, "SELECT 1 FROM scan_logs")) == 1


# ── Convergence ─────────────────────────────────────────────────────────────


def test_two_terminals_converge_to_the_same_winner_in_both_arrival_orders(client, db, world, now):
    t_x, t_y = world.tickets[0], world.tickets[1]
    a, b = world.terminal(), world.terminal()
    scan_a = lambda t: op(t, at=now - 60 * S)  # A scanned first
    scan_b = lambda t: op(t, at=now - 30 * S)
    # ticket X: A's batch arrives first ; ticket Y: B's batch arrives first
    sync(client, world, a, [scan_a(t_x)], sent=now)
    sync(client, world, b, [scan_b(t_x)], sent=now)
    sync(client, world, b, [scan_b(t_y)], sent=now)
    sync(client, world, a, [scan_a(t_y)], sent=now)
    assert winner_terminal(db, t_x) == a and winner_terminal(db, t_y) == a
    for t in (t_x, t_y):
        c = conflicts_of(db, t)
        assert [x["type"] for x in c] == ["CROSS_TERMINAL_DOUBLE_ADMISSION"]
        loser = rows(db, "SELECT terminal_id FROM scan_logs WHERE log_id = %s", c[0]["losing_log_id"])[0]
        assert str(loser["terminal_id"]) == b


def test_a_late_but_older_batch_flips_the_winner_and_keeps_the_history(client, db, world, now):
    t = world.tickets[0]
    a, b = world.terminal(), world.terminal()
    r_b = sync(client, world, b, [op(t, at=now - 30 * S)], sent=now).json()["results"][0]
    assert r_b["status"] == "accepted" and winner_terminal(db, t) == b
    r_a = sync(client, world, a, [op(t, at=now - 60 * S)], sent=now + 5 * S).json()["results"][0]
    assert r_a["status"] == "accepted" and r_a["server_decision"] == "valid"
    assert winner_terminal(db, t) == a  # the older scan took the slot
    conf = conflicts_of(db, t)
    assert len(conf) == 1 and conf[0]["type"] == "CROSS_TERMINAL_DOUBLE_ADMISSION"
    losing = rows(db, "SELECT * FROM scan_logs WHERE log_id = %s", conf[0]["losing_log_id"])[0]
    assert str(losing["terminal_id"]) == b
    assert losing["ack_status"] == "accepted" and losing["server_decision"] == "valid"  # what B was told is kept
    assert len(rows(db, "SELECT 1 FROM scan_logs")) == 2  # nothing erased
    assert len(rows(db, "SELECT 1 FROM station_consumptions")) == 1


def test_an_offline_scan_older_than_an_online_admission_makes_it_a_double_admission(client, db, world, now):
    t = world.tickets[0]
    online_terminal, offline_terminal = world.terminal(), world.terminal()
    r = client.post(
        "/api/checkin/scan", json=scan_body(world, t, online_terminal), headers=world.scanner
    ).json()
    assert r["server_decision"] == "valid"
    sync(client, world, offline_terminal, [op(t, at=now - 3600 * S)], sent=now, headers=world.scanner)
    assert winner_terminal(db, t) == offline_terminal
    conf = conflicts_of(db, t)
    assert [c["type"] for c in conf] == ["CROSS_TERMINAL_DOUBLE_ADMISSION"]
    lost = rows(db, "SELECT terminal_id, connection_status FROM scan_logs WHERE log_id = %s", conf[0]["losing_log_id"])[0]
    assert str(lost["terminal_id"]) == online_terminal and lost["connection_status"] == "online"


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_every_arrival_order_of_four_terminals_gives_the_same_outcome(client, db, world, now, seed):
    t = world.tickets[seed]
    terminals = [world.terminal() for _ in range(4)]
    times = [now - 40 * S, now - 70 * S, now - 10 * S, now - 70 * S + timedelta(milliseconds=5)]
    order = list(itertools.permutations(range(4)))[seed * 7 % 24]
    for i in order:
        assert sync(client, world, terminals[i], [op(t, at=times[i])], sent=now).status_code == 200
    assert winner_terminal(db, t) == terminals[1]  # the oldest corrected time
    losers = sorted(
        str(rows(db, "SELECT terminal_id FROM scan_logs WHERE log_id = %s", c["losing_log_id"])[0]["terminal_id"])
        for c in conflicts_of(db, t)
    )
    assert losers == sorted([terminals[0], terminals[2], terminals[3]])
    assert {c["type"] for c in conflicts_of(db, t)} == {"CROSS_TERMINAL_DOUBLE_ADMISSION"}


def test_concurrent_batches_give_exactly_one_winner_per_ticket(client, db, world, now):
    tickets = world.tickets[:5]
    terminals = [world.terminal() for _ in range(8)]
    # terminal k scanned every ticket at now - (100 - k) s : terminal 0 is the oldest everywhere
    results = run_parallel(
        8,
        lambda k: sync(
            client, world, terminals[k], [op(t, at=now - (100 - k) * S) for t in tickets], sent=now
        ),
    )
    assert [r.status_code for r in results] == [200] * 8
    assert len(rows(db, "SELECT 1 FROM station_consumptions")) == 5
    assert len(rows(db, "SELECT 1 FROM scan_logs WHERE is_claim")) == 40
    for t in tickets:
        assert winner_terminal(db, t) == terminals[0]
        assert len(conflicts_of(db, t)) == 7
    assert all(c["use_index"] == 0 for c in rows(db, "SELECT use_index FROM station_consumptions"))


def test_max_uses_two_gives_two_winners_and_one_loser(client, db, world, now):
    add_rule(db, world, "GA", "EVENT_ENTRY", 2)
    t = world.tickets[0]
    term = [world.terminal() for _ in range(3)]
    for i in (2, 0, 1):
        sync(client, world, term[i], [op(t, at=now - (50 - 10 * i) * S)], sent=now)
    assert winner_terminal(db, t, use_index=0) == term[0] and winner_terminal(db, t, use_index=1) == term[1]
    assert winner_terminal(db, t, use_index=2) is None
    assert len(conflicts_of(db, t)) == 1


def test_the_clock_offset_is_per_batch_and_changes_the_ranking(client, db, world, now):
    """B's phone runs 100 s slow: its raw timestamp looks older, but the corrected one is later."""
    t = world.tickets[0]
    a, b = world.terminal(), world.terminal()
    r_a = sync(client, world, a, [op(t, at=now - 50 * S)], sent=now).json()
    r_b = sync(client, world, b, [op(t, at=now - 140 * S)], sent=now - 100 * S).json()
    assert r_b["clock_offset_ms"] == 100_000
    assert r_b["results"][0]["status"] == "conflict"  # corrected to now - 40 s: after A's now - 50 s
    assert winner_terminal(db, t) == a
    log = rows(db, "SELECT * FROM scan_logs WHERE terminal_id = %s", b)[0]
    assert log["clock_offset_ms"] == 100_000 and log["corrected_evaluated_at"] == now - 40 * S
    assert not log["clock_suspect"]  # 100 s is under the 300 s threshold
    assert r_a["results"][0]["status"] == "accepted"


# ── Conflict types ──────────────────────────────────────────────────────────


def test_same_terminal_replay_is_benign(client, db, world, now):
    t, term = world.tickets[0], world.terminal()
    r = sync(client, world, term, [op(t, at=now - 50 * S), op(t, at=now - 20 * S)], sent=now).json()["results"]
    assert [x["status"] for x in r] == ["accepted", "conflict"]
    assert r[1]["conflict"]["type"] == "SAME_TERMINAL_REPLAY"
    assert [c["type"] for c in conflicts_of(db, t)] == ["SAME_TERMINAL_REPLAY"]


def test_revoked_before_the_scan_is_late_revoked_and_never_consumes(client, db, world, now):
    before, after = world.tickets[0], world.tickets[1]
    db.execute("UPDATE tickets SET status = 'void', voided_at = %s WHERE id = %s", (iso(now - 120 * S), before["id"]))
    db.execute("UPDATE tickets SET status = 'void', voided_at = %s WHERE id = %s", (iso(now - 30 * S), after["id"]))
    r = sync(
        client, world, world.terminal(), [op(before, at=now - 60 * S), op(after, at=now - 60 * S)], sent=now
    ).json()["results"]
    assert (r[0]["status"], r[0]["server_decision"]) == ("conflict", "revoked")
    assert r[0]["conflict"]["type"] == "LATE_REVOKED"
    assert (r[1]["status"], r[1]["server_decision"]) == ("accepted", "valid")  # it was valid when scanned
    assert winner_terminal(db, before) is None and winner_terminal(db, after) is not None
    c = conflicts_of(db, before)[0]
    assert c["type"] == "LATE_REVOKED" and c["winning_log_id"] is None


def test_not_authorized_server_side_when_the_terminal_said_valid(client, db, world, now):
    t = world.tickets[0]
    r = sync(client, world, world.terminal(), [op(t, at=now - 5 * S, station="FOOD_ACCESS")], sent=now).json()["results"][0]
    assert (r["status"], r["server_decision"]) == ("conflict", "not_authorized")
    assert r["conflict"]["type"] == "NOT_AUTHORIZED_SERVER_SIDE"
    unknown = sync(client, world, world.terminal(), [op({"id": "NOPE"}, at=now - 5 * S)], sent=now).json()["results"][0]
    assert (unknown["status"], unknown["server_decision"]) == ("conflict", "unknown")
    assert {c["type"] for c in rows(db, "SELECT type FROM scan_conflicts")} == {"NOT_AUTHORIZED_SERVER_SIDE"}


def test_capability_is_reverified_but_never_stored(client, db, world, now):
    good, forged = world.tickets[0], dict(world.tickets[1])
    head, payload, sig = forged["capability"].split(".")
    forged["capability"] = ".".join([head, payload, ("A" if sig[0] != "A" else "B") + sig[1:]])
    r = sync(
        client,
        world,
        world.terminal(),
        [op(good, at=now, capability=good["capability"]), op(forged, at=now, capability=forged["capability"])],
        sent=now,
    ).json()["results"]
    assert (r[0]["status"], r[0]["server_decision"]) == ("accepted", "valid")
    assert (r[1]["status"], r[1]["server_decision"]) == ("conflict", "invalid")
    assert r[1]["conflict"]["type"] == "NOT_AUTHORIZED_SERVER_SIDE"
    by_ticket = {l["ticket_id"]: l for l in rows(db, "SELECT * FROM scan_logs")}
    assert by_ticket[good["id"]]["capability_verified"] is True and by_ticket[forged["id"]]["capability_verified"] is False
    dump = "".join(x["j"] for x in rows(db, "SELECT row_to_json(l)::text AS j FROM scan_logs l"))
    assert good["capability"].split(".")[1][:24] not in dump


def test_an_absurd_clock_is_flagged_and_never_beats_a_plausible_scan(client, db, world, now):
    alone, contested = world.tickets[0], world.tickets[1]
    fraud, honest = world.terminal(), world.terminal()
    # the phone is 2 h off, so the corrected time lands 30 s ago: "earlier" than the honest scan
    far = sync(client, world, fraud, [op(contested, at=now - 2 * 3600 * S - 30 * S)], sent=now - 2 * 3600 * S)
    item = far.json()["results"][0]
    assert item["flags"] == ["clock_suspect"] and item["status"] == "accepted"  # alone: accepted and flagged
    log = rows(db, "SELECT * FROM scan_logs")[0]
    assert log["clock_suspect"] and "offset_too_large" in log["clock_suspect_reason"]
    assert [c["type"] for c in rows(db, "SELECT type FROM scan_conflicts")] == ["CLOCK_SUSPECT"]
    # an honest scan made LATER than the claimed one still wins
    h = sync(client, world, honest, [op(contested, at=now - 10 * S)], sent=now).json()["results"][0]
    assert (h["status"], h["server_decision"]) == ("accepted", "valid")
    assert winner_terminal(db, contested) == honest
    c = conflicts_of(db, contested)
    assert len(c) == 1 and c[0]["type"] == "CROSS_TERMINAL_DOUBLE_ADMISSION" and c[0]["clock_suspect"] is True
    # a timestamp in the future is suspect too
    fut = sync(client, world, world.terminal(), [op(alone, at=now + 3600 * S)], sent=now).json()["results"][0]
    assert fut["flags"] == ["clock_suspect"]
    assert "in_the_future" in rows(db, "SELECT clock_suspect_reason FROM scan_logs WHERE ticket_id = %s", alone["id"])[0]["clock_suspect_reason"]


# ── Partial batches, limits, terminals ──────────────────────────────────────


def test_a_partially_invalid_batch_returns_mixed_results(client, db, world, now):
    t = world.tickets
    term = world.terminal()
    ok = op(t[0], at=now - 10 * S)
    ops = [
        ok,
        op(t[1], at=now - 10 * S, station="GHOST_STATION"),
        op(t[2], at=now - 10 * S, decision="maybe"),
        op(None, at=now - 10 * S, decision="valid"),  # valid without a ticket id
        "not an object",
        {"scan_id": str(uuid.uuid4()), "station": "EVENT_ENTRY"},  # no operation_id
        op(t[3], at=now - 10 * S, qr_version=9),
        {**op(t[4], at=now - 10 * S), "operation_id": "not-a-uuid"},
        op(t[5], at=now - 10 * S, decision="notAuthorized", station="foodAccess"),
    ]
    r = sync(client, world, term, ops, sent=now)
    assert r.status_code == 200, r.text
    res = r.json()["results"]
    assert [x["status"] for x in res] == [
        "accepted", "rejected", "rejected", "rejected", "rejected", "rejected", "rejected", "rejected", "accepted",
    ]
    assert [x.get("error_code") for x in res[1:8]] == [
        "unknown_station", "invalid_decision", "operation_invalid", "operation_invalid",
        "operation_invalid", "unsupported_qr_version", "operation_invalid",
    ]
    assert res[7]["operation_id"] is None  # a garbage id is never echoed
    assert r.json()["summary"] == {"accepted": 2, "already_processed": 0, "conflict": 0, "rejected": 7}
    assert len(rows(db, "SELECT 1 FROM scan_logs")) == 2 and winner_terminal(db, t[0]) == term


def test_batch_limits(client, db, world, now, checkin_rt):
    term = world.terminal()
    empty = sync(client, world, term, [], sent=now)
    assert empty.status_code == 400 and empty.json()["error"]["code"] == "batch_empty"
    checkin_rt.cfg = dataclasses.replace(checkin_rt.cfg, sync_max_batch=2)
    big = sync(client, world, term, [op(t, at=now) for t in world.tickets[:3]], sent=now)
    assert big.status_code == 413 and big.json()["error"]["code"] == "batch_too_large"
    assert rows(db, "SELECT 1 FROM scan_logs") == []


def test_invalid_envelope_is_a_400(client, world, now):
    r = client.post(SYNC, json={"event_id": world.event_id, "operations": []}, headers=world.scanner)
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_request"


def test_revoked_terminal_is_refused_and_its_old_scans_are_kept(client, db, world, now):
    t1, t2 = world.tickets[0], world.tickets[1]
    term = world.terminal()
    assert sync(client, world, term, [op(t1, at=now - 5 * S)], sent=now).status_code == 200
    db.execute("UPDATE checkin_terminals SET revoked_at = now() WHERE terminal_id = %s", (term,))
    r = sync(client, world, term, [op(t2, at=now - 5 * S)], sent=now)
    assert r.status_code == 403 and r.json()["error"]["code"] == "terminal_revoked"
    assert len(rows(db, "SELECT 1 FROM scan_logs")) == 1 and winner_terminal(db, t1) == term


def test_authentication_roles_and_event_binding(client, db, world, now):
    t, term = world.tickets[0], world.terminal()
    body = sync_body(world, term, [op(t, at=now)], sent_at=now)
    assert client.post(SYNC, json=body).status_code == 401
    assert client.post(SYNC, json=body, headers=world.outsider).status_code == 403
    assert client.post(SYNC, json=body, headers=world.scanner).status_code == 200


# ── Conflicts API, stats ────────────────────────────────────────────────────


@pytest.fixture()
def with_conflicts(client, db, world, now):
    """Three double admissions on three tickets."""
    a, b = world.terminal(), world.terminal()
    for t in world.tickets[:3]:
        sync(client, world, a, [op(t, at=now - 60 * S)], sent=now)
        sync(client, world, b, [op(t, at=now - 30 * S)], sent=now)
    return a, b


def test_conflicts_listing_filters_and_pagination(client, world, with_conflicts):
    a, b = with_conflicts
    url = "/api/checkin/conflicts"
    page1 = client.get(url, params={"event_id": world.event_id, "limit": 2}, headers=world.admin).json()
    assert len(page1["conflicts"]) == 2 and page1["next_cursor"]
    page2 = client.get(
        url, params={"event_id": world.event_id, "limit": 2, "cursor": page1["next_cursor"]}, headers=world.admin
    ).json()
    assert len(page2["conflicts"]) == 1 and page2["next_cursor"] is None
    ids = [c["conflict_id"] for c in page1["conflicts"] + page2["conflicts"]]
    assert ids == sorted(ids, reverse=True)
    c = page1["conflicts"][0]
    assert c["type"] == "CROSS_TERMINAL_DOUBLE_ADMISSION" and c["status"] == "open" and c["serial"].startswith("TDEV-")
    assert c["winning"]["terminal_id"] == a and c["losing"]["terminal_id"] == b
    for f in ({"status": "acknowledged"}, {"type": "LATE_REVOKED"}):
        assert client.get(url, params={"event_id": world.event_id, **f}, headers=world.admin).json()["conflicts"] == []
    assert client.get(url, params={"event_id": world.event_id, "type": "NOPE"}, headers=world.admin).status_code == 400
    assert client.get(url, params={"event_id": world.event_id, "status": "x"}, headers=world.admin).status_code == 400


def test_conflicts_are_for_supervisors_only(client, world, with_conflicts):
    url = "/api/checkin/conflicts"
    assert client.get(url, params={"event_id": world.event_id}).status_code == 401
    assert client.get(url, params={"event_id": world.event_id}, headers=world.scanner).status_code == 403
    assert client.get(url, params={"event_id": world.event_id}, headers=world.outsider).status_code == 403


def test_acknowledge_is_idempotent_and_restricted(client, db, world, with_conflicts):
    cid = rows(db, "SELECT conflict_id FROM scan_conflicts ORDER BY conflict_id")[0]["conflict_id"]
    url = f"/api/checkin/conflicts/{cid}/acknowledge"
    assert client.post(url, json={"note": "x"}).status_code == 401
    assert client.post(url, json={"note": "x"}, headers=world.scanner).status_code == 403
    assert client.post(url, json={"note": "x"}, headers=world.outsider).status_code == 403
    first = client.post(url, json={"note": "verified at the gate"}, headers=world.admin)
    assert first.status_code == 200
    c1 = first.json()["conflict"]
    assert c1["status"] == "acknowledged" and c1["note"] == "verified at the gate" and c1["resolved_by"]
    second = client.post(url, json={"note": "another note"}, headers=world.admin).json()["conflict"]
    assert second["note"] == "verified at the gate" and second["resolved_at"] == c1["resolved_at"]
    assert client.post("/api/checkin/conflicts/99999999/acknowledge", json={}, headers=world.admin).status_code == 404
    open_left = client.get(
        "/api/checkin/conflicts", params={"event_id": world.event_id, "status": "open"}, headers=world.admin
    ).json()["conflicts"]
    assert len(open_left) == 2


def test_acknowledging_does_not_leak_across_events(client, db, world, with_conflicts, commit_3a):
    other = make_world(client, db, commit_3a)
    cid = rows(db, "SELECT conflict_id FROM scan_conflicts LIMIT 1")[0]["conflict_id"]
    r = client.post(f"/api/checkin/conflicts/{cid}/acknowledge", json={}, headers=other.admin)
    assert r.status_code == 403  # an admin of another organisation


def test_stats(client, db, world, now, with_conflicts):
    t = world.tickets[5]
    sync(client, world, world.terminal(), [op(t, at=now - 5 * S, station="FOOD_ACCESS")], sent=now, pending_count=7)
    r = client.get("/api/checkin/stats", params={"event_id": world.event_id}, headers=world.scanner)
    assert r.status_code == 200
    body = r.json()
    entry = body["by_station"]["EVENT_ENTRY"]
    assert entry["consumed"] == 3 and entry["decisions"] == {"valid": 3, "already_scanned": 3}
    assert body["by_station"]["FOOD_ACCESS"]["decisions"] == {"not_authorized": 1}
    assert body["conflicts"]["open"] == 4 and body["conflicts"]["acknowledged"] == 0
    assert body["conflicts"]["by_type"] == {"CROSS_TERMINAL_DOUBLE_ADMISSION": 3, "NOT_AUTHORIZED_SERVER_SIDE": 1}
    assert len(body["terminals"]) == 3 and any(x["pending_count"] == 7 for x in body["terminals"])
    assert "capability" not in r.text and "@example.com" not in r.text
    assert client.get("/api/checkin/stats", params={"event_id": world.event_id}).status_code == 401
    assert client.get("/api/checkin/stats", params={"event_id": world.event_id}, headers=world.outsider).status_code == 403
