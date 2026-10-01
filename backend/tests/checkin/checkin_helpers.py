"""Helpers of the check-in tests: a paid-tickets world, rules, request bodies, parallel runner."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


class ShiftClock:
    """Real time plus an adjustable shift (to test expiry / not-yet-valid without sleeping)."""

    def __init__(self) -> None:
        self.shift = timedelta(0)

    def __call__(self) -> datetime:
        return datetime.now(timezone.utc) + self.shift


@dataclass
class World:
    """A published event with paid tickets and two authenticated callers."""

    event_id: str
    org_id: str
    admin: dict  # Authorization header of the org owner
    scanner: dict  # Authorization header of a user with the `scanner` role
    outsider: dict  # authenticated but member of no organisation
    tickets: list[dict] = field(default_factory=list)  # {id, serial, capability, ticket_type_id}
    type_ids: dict[str, str] = field(default_factory=dict)

    def terminal(self) -> str:
        """A fresh terminal UUID."""
        return str(uuid.uuid4())


def _signup(client, label: str) -> tuple[dict, str]:
    """A user with a valid 3A access token, created directly in the store.

    ``POST /api/auth/signup`` is not used: on the current 3A main it fails (``auth.service.signup`` calls
    ``create_user`` with its old signature), see docs/checkin/BUGS_3A.md.
    """
    from auth import service as auth_svc
    from store import users as user_store

    store, cfg = client.app.state.store, client.app.state.config
    user = user_store.create_user(
        store,
        user_store.UserPartial(email=f"{label}-{uuid.uuid4().hex[:10]}@example.com", password_hash="not-a-real-hash", name=label),
    )
    token, _expires = auth_svc.gen_new_jwt_token(store, cfg, user, 60)
    return {"Authorization": f"Bearer {token}"}, user.id


def make_world(client, db, commit, *, type_names=("GA",), per_type: int = 1) -> World:
    """Create org, published event and ``per_type`` paid tickets for each ticket type.

    ``commit`` validates the 3A connection: the 3A ``Store`` leaves work uncommitted after a
    ``transaction()`` (see docs/checkin/BUGS_3A.md, bug 3), so other connections would not see it.
    """
    admin, _ = _signup(client, "owner")
    scanner, scanner_id = _signup(client, "scanner")
    outsider, _ = _signup(client, "outsider")
    suffix = uuid.uuid4().hex[:8]
    org = client.post("/api/orgs", json={"name": f"Org {suffix}", "slug": f"org-{suffix}"}, headers=admin)
    assert org.status_code == 201, org.text
    org_id = org.json()["org"]["id"]
    db.execute(
        "INSERT INTO org_members (org_id, user_id, role, created_at) VALUES (%s, %s, 'scanner', %s)",
        (org_id, scanner_id, "2026-01-01T00:00:00Z"),
    )
    now = datetime.now(timezone.utc)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    ev = client.post(
        "/api/events",
        json={
            "org_id": org_id,
            "slug": f"ev-{suffix}",
            "title": "Check-in event",
            "starts_at": (now - timedelta(hours=1)).strftime(fmt),
            "ends_at": (now + timedelta(hours=8)).strftime(fmt),
        },
        headers=admin,
    )
    assert ev.status_code == 201, ev.text
    event_id = ev.json()["event"]["id"]
    assert client.post(f"/api/events/{event_id}/publish", headers=admin).status_code == 200
    world = World(event_id, org_id, admin, scanner, outsider)
    for name in type_names:
        tt = client.post(
            f"/api/events/{event_id}/ticket-types",
            json={"name": name, "price_minor": 500, "quantity_total": 200, "max_per_order": max(per_type, 1)},
            headers=admin,
        )
        assert tt.status_code == 201, tt.text
        type_id = tt.json()["ticket_type"]["id"]
        world.type_ids[name] = type_id
        order = client.post(
            "/api/orders",
            json={
                "event_id": event_id,
                "items": [{"ticket_type_id": type_id, "quantity": per_type}],
                "buyer": {"email": f"buyer-{uuid.uuid4().hex[:8]}@example.com", "name": "Buyer"},
                "provider": "manual",
            },
        )
        assert order.status_code == 201, order.text
        paid = client.post(f"/api/orders/{order.json()['order']['id']}/mark-paid", headers=admin)
        assert paid.status_code == 200, paid.text
        for t in paid.json()["tickets"]:
            world.tickets.append(
                {
                    "id": t["id"],
                    "serial": t["serial"],
                    "capability": t["capability"],
                    "ticket_type_id": type_id,
                    "type_name": name,
                }
            )
    client.cookies.clear()
    commit()
    return world


def add_rule(db, world: World, type_name: str, station: str, max_uses: int = 1) -> None:
    """Insert an explicit station rule for a ticket type."""
    db.execute(
        "INSERT INTO checkin_station_rules (event_id, ticket_type_id, station, max_uses) VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (event_id, ticket_type_id, station) DO UPDATE SET max_uses = EXCLUDED.max_uses",
        (world.event_id, world.type_ids[type_name], station, max_uses),
    )


def scan_body(world: World, ticket: dict, terminal: str, station: str = "EVENT_ENTRY", **extra) -> dict:
    """JSON body of ``POST /api/checkin/scan``."""
    return {
        "event_id": world.event_id,
        "terminal_id": terminal,
        "station": station,
        "capability": ticket["capability"],
        **extra,
    }


def run_parallel(n: int, fn):
    """Run ``fn(i)`` in ``n`` threads released together; return their results in order."""
    barrier = threading.Barrier(n)
    results: list = [None] * n
    errors: list = []

    def worker(i: int) -> None:
        try:
            barrier.wait(timeout=10)
            results[i] = fn(i)
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    if errors:
        raise errors[0]
    return results


# ── Sync helpers (TDEV-55) ──────────────────────────────────────────────────


def iso(dt: datetime) -> str:
    """UTC timestamp as sent by the 3B app (``toUtc().toIso8601String()``)."""
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def op(ticket, *, at: datetime, station="EVENT_ENTRY", decision="valid", op_id=None, **extra) -> dict:
    """One outbox operation. ``ticket`` may be ``None`` (terminal could not read the QR)."""
    return {
        "operation_id": op_id or str(uuid.uuid4()),
        "scan_id": str(uuid.uuid4()),
        "ticket_id": ticket["id"] if ticket else None,
        "participant_id": None,
        "station": station,
        "decision": decision,
        "evaluated_at": iso(at),
        "previous_scan_at": None,
        "qr_version": 1,
        **extra,
    }


def sync_body(world, terminal, operations, *, sent_at: datetime, batch_id=None, **extra) -> dict:
    """JSON body of ``POST /api/checkin/sync``."""
    return {
        "event_id": world.event_id,
        "terminal_id": terminal,
        "batch_id": batch_id or str(uuid.uuid4()),
        "device_sent_at": iso(sent_at),
        "app_version": "test",
        "operations": operations,
        **extra,
    }
