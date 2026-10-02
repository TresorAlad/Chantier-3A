"""Standalone deployment (``checkin.asgi``): works without the 3A middleware or 3A Store connection."""

from __future__ import annotations

import psycopg
import pytest
from checkin_fixtures import applied_schema, checkin_rt, clock, commit_3a, db  # noqa: F401  (fixtures)
from checkin_helpers import make_world, scan_body
from fastapi.testclient import TestClient

from checkin.asgi import create_standalone_app

URL = "/api/checkin/scan"


@pytest.fixture()
def world(client, db, checkin_rt, commit_3a):
    return make_world(client, db, commit_3a)


@pytest.fixture()
def standalone(checkin_rt):
    return TestClient(create_standalone_app(runtime=checkin_rt), raise_server_exceptions=False)


def test_the_standalone_app_serves_the_checkin_api_only(world, standalone):
    assert standalone.get("/api/checkin/health").json()["status"] == "ok"
    r = standalone.post(URL, json=scan_body(world, world.tickets[0], world.terminal()), headers=world.scanner)
    assert r.status_code == 200 and r.json()["server_decision"] == "valid"
    assert standalone.get("/api/events").status_code == 404  # no 3A route
    assert standalone.get("/api/checkin/health").headers["X-Content-Type-Options"] == "nosniff"


def test_the_standalone_app_refuses_cookie_sessions_without_a_csrf_secret(world, standalone, checkin_rt):
    from checkin.adapters import Sessions3AAuth

    token = world.scanner["Authorization"].removeprefix("Bearer ")
    checkin_rt.auth = Sessions3AAuth("")  # no CSRF secret configured
    r = standalone.post(
        URL, json=scan_body(world, world.tickets[0], world.terminal()), cookies={"chantier3a_session": token}
    )
    assert r.status_code == 401 and "Bearer" in r.json()["error"]["message"]
    ok = standalone.post(URL, json=scan_body(world, world.tickets[0], world.terminal()), headers=world.scanner)
    assert ok.status_code == 200  # Bearer still works


def test_standalone_survives_a_poisoned_3a_connection_while_the_mounted_app_does_not(
    client, demo_store, world, standalone
):
    """Documents 3A bug 2: one failed statement on the shared Store connection breaks every request
    that goes through the 3A session middleware. The standalone deployment is not affected."""
    store = demo_store[0]
    with pytest.raises(psycopg.errors.UndefinedTable):
        store._pg.execute("SELECT * FROM table_that_does_not_exist")  # no rollback, like try_insert_admitted
    assert store._pg.info.transaction_status == psycopg.pq.TransactionStatus.INERROR

    mounted = TestClient(client.app, raise_server_exceptions=False)
    body = scan_body(world, world.tickets[0], world.terminal())
    assert mounted.post(URL, json=body, headers=world.scanner).status_code == 500  # 3A middleware is stuck
    r = standalone.post(URL, json=body, headers=world.scanner)
    assert r.status_code == 200 and r.json()["server_decision"] == "valid"
