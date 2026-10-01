"""Behaviour of the TDEV-56 optimisations: fewer writes, TTL caches and their limits."""

from __future__ import annotations

import time
import uuid
from types import SimpleNamespace

import pytest
from checkin_fixtures import applied_schema, checkin_rt, clock, commit_3a, db  # noqa: F401  (fixtures)
from checkin_helpers import make_world, scan_body

from checkin import repository
from checkin.adapters import CachedAuth, CachedKeySource
from checkin.ports import AuthError, Principal


def last_seen(db, terminal):
    return db.execute("SELECT last_seen_at FROM checkin_terminals WHERE terminal_id = %s", (terminal,)).fetchone()[
        "last_seen_at"
    ]


def test_terminal_last_seen_is_written_at_most_every_30_seconds(client, db, checkin_rt, commit_3a):
    world = make_world(client, db, commit_3a)
    term = uuid.uuid4()
    with checkin_rt.pool.connection() as conn:
        repository.register_terminal(conn, term, world.event_id, "u1")
        conn.commit()
        first = last_seen(db, term)
        repository.register_terminal(conn, term, world.event_id, "u1")  # fresh: a SELECT only, no write
        conn.commit()
        assert last_seen(db, term) == first
        db.execute("UPDATE checkin_terminals SET last_seen_at = now() - interval '2 minutes' WHERE terminal_id = %s", (term,))
        stale = last_seen(db, term)
        repository.register_terminal(conn, term, world.event_id, "u1")  # stale: refreshed
        conn.commit()
    assert last_seen(db, term) > stale


def test_a_terminal_of_another_event_is_still_detected_when_fresh(client, db, checkin_rt, commit_3a):
    world = make_world(client, db, commit_3a)
    term = uuid.uuid4()
    with checkin_rt.pool.connection() as conn:
        repository.register_terminal(conn, term, world.event_id, "u1")
        conn.commit()
        row = repository.register_terminal(conn, term, "SOME_OTHER_EVENT", "u1")
        conn.rollback()
    assert row["event_id"] == world.event_id  # the caller compares and refuses (terminal_event_mismatch)


def test_scan_without_operation_id_gets_a_server_generated_one(client, db, checkin_rt, commit_3a):
    world = make_world(client, db, commit_3a)
    body = scan_body(world, world.tickets[0], str(uuid.uuid4()))
    assert "operation_id" not in body
    r = client.post("/api/checkin/scan", json=body, headers=world.scanner)
    assert r.status_code == 200 and uuid.UUID(r.json()["operation_id"])
    assert r.json()["server_decision"] == "valid"


class _CountingKeys:
    def __init__(self):
        self.calls = 0

    def issuer_keys(self, conn, event_id):
        self.calls += 1
        return {"k_test": b"\x01" * 32}


def test_key_cache_serves_from_memory_then_expires():
    inner = _CountingKeys()
    cache = CachedKeySource(inner, ttl=0.15)
    for _ in range(5):
        assert cache.issuer_keys(None, "e1") == {"k_test": b"\x01" * 32}
    assert inner.calls == 1
    cache.issuer_keys(None, "e2")
    assert inner.calls == 2  # another event is a separate entry
    time.sleep(0.2)
    cache.issuer_keys(None, "e1")
    assert inner.calls == 3  # expired: read again (a revoked key stops being accepted after the TTL)


class _FakeAuth:
    def __init__(self, deny_role=False):
        self.auth_calls = 0
        self.role_calls = 0
        self.deny_role = deny_role

    def authenticate(self, conn, request):
        self.auth_calls += 1
        return Principal(user_id="u1")

    def require_role(self, conn, principal, event_id, role):
        self.role_calls += 1
        if self.deny_role:
            raise AuthError(403, "forbidden", "no")


def _req(header=None):
    return SimpleNamespace(headers={"Authorization": header} if header else {})


def test_auth_cache_is_per_token_and_expires():
    inner = _FakeAuth()
    cache = CachedAuth(inner, ttl=0.15)
    for _ in range(3):
        cache.authenticate(None, _req("Bearer aaa"))
    cache.authenticate(None, _req("Bearer bbb"))
    assert inner.auth_calls == 2  # one per distinct token
    time.sleep(0.2)
    cache.authenticate(None, _req("Bearer aaa"))
    assert inner.auth_calls == 3


def test_auth_cache_never_caches_cookie_sessions_or_failures():
    inner = _FakeAuth()
    cache = CachedAuth(inner, ttl=60)
    cache.authenticate(None, _req())
    cache.authenticate(None, _req())
    assert inner.auth_calls == 2  # no Bearer header: always asks the database (CSRF, cookies)
    denied = _FakeAuth(deny_role=True)
    cache2 = CachedAuth(denied, ttl=60)
    for _ in range(3):
        with pytest.raises(AuthError):
            cache2.require_role(None, Principal("u1"), "e1", "scanner")
    assert denied.role_calls == 3  # a refusal is re-checked every time


def test_role_cache_is_keyed_by_user_event_and_role():
    inner = _FakeAuth()
    cache = CachedAuth(inner, ttl=60)
    p = Principal("u1")
    for _ in range(3):
        cache.require_role(None, p, "e1", "scanner")
    cache.require_role(None, p, "e1", "admin")  # a higher role is a different decision
    cache.require_role(None, p, "e2", "scanner")
    cache.require_role(None, Principal("u2"), "e1", "scanner")
    assert inner.role_calls == 4
