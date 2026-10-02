"""Seed a DISPOSABLE database for the check-in load tests.

    CHECKIN_LOAD_DATABASE_URL=postgresql://...@127.0.0.1:5434/chantier3a_perf \
        python tests/load/seed.py --tickets 3000

Applies every migration (explicit commits), then creates through the 3A API, in-process: two users,
an organisation, a published event, two ticket types and ``--tickets`` paid tickets with real Ed25519
capabilities. Writes ``tests/load/.seed.json`` (gitignored: it holds test-only tokens and QR contents).

Refuses to run unless the database name ends with ``_perf`` or ``_test``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import psycopg

BACKEND = Path(__file__).resolve().parents[2]
# Small orders on purpose: the 3A allocates the random TDEV-YYYY-NNNN of every ticket of an order BEFORE
# inserting any of them, so two tickets of one big order can draw the same 4-digit suffix
# (about 39 % for an order of 100). See docs/checkin/BUGS_3A.md, observation 4.
ORDER_SIZE = 5
sys.path.insert(0, str(BACKEND))


def apply_migrations(url: str) -> None:
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)"
        )
        for path in sorted((BACKEND / "migrations").glob("*.sql")):
            version = int(re.match(r"(\d+)_", path.name).group(1))
            if conn.execute("SELECT 1 FROM schema_migrations WHERE version = %s", (version,)).fetchone():
                continue
            with conn.transaction():
                conn.execute(path.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO schema_migrations VALUES (%s, %s, %s)", (version, path.name, "seed"))


def mark_paid_with_retry(client, admin, order_id: str, attempts: int = 6):
    """Settle an order, retrying when the 3A draws the same public serial twice inside one order."""
    for attempt in range(attempts):
        try:
            paid = client.post(f"/api/orders/{order_id}/mark-paid", headers=admin)
            paid.raise_for_status()
            return paid
        except Exception as exc:  # the 3A raises UniqueViolation (tickets_serial_key) through the test client
            if "tickets_serial_key" not in str(exc) or attempt == attempts - 1:
                raise
    raise RuntimeError("unreachable")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickets", type=int, default=3000)
    ap.add_argument("--vip-share", type=float, default=0.2)
    ap.add_argument("--out", default=str(Path(__file__).with_name(".seed.json")))
    args = ap.parse_args()

    url = os.environ.get("CHECKIN_LOAD_DATABASE_URL", "")
    name = urlparse(url).path.lstrip("/")
    if not url or not (name.endswith("_perf") or name.endswith("_test")):
        sys.exit("set CHECKIN_LOAD_DATABASE_URL to a disposable database whose name ends with _perf or _test")
    apply_migrations(url)

    from fastapi.testclient import TestClient

    from bootstrap import build_services
    from config import load_config
    from http_layer.app import create_app
    from store.store import open_postgres

    store = open_postgres(url)
    cfg = load_config(database_url=url, demo=True)
    client = TestClient(create_app(store, cfg, build_services(store, cfg)))

    def signup(label: str) -> dict:
        # POST /api/auth/signup fails on the current 3A main (create_user signature): create the user directly.
        from auth import service as auth_svc
        from store import users as user_store

        user = user_store.create_user(
            store,
            user_store.UserPartial(email=f"{label}-{uuid.uuid4().hex[:8]}@example.com", password_hash="not-a-real-hash", name=label),
        )
        token, _expires = auth_svc.gen_new_jwt_token(store, cfg, user, 60 * 24)
        return {"Authorization": f"Bearer {token}"}

    admin, scanner = signup("load-admin"), signup("load-scanner")
    slug = uuid.uuid4().hex[:8]
    org = client.post("/api/orgs", json={"name": f"Load {slug}", "slug": f"load-{slug}"}, headers=admin).json()["org"]["id"]
    # the scanner user joins the org with the lowest role
    scanner_id = client.get("/api/auth/me", headers=scanner).json()["user"]["id"]
    store.execute(
        "INSERT INTO org_members (org_id, user_id, role, created_at) VALUES (?, ?, 'scanner', ?)",
        (org, scanner_id, "2026-01-01T00:00:00Z"),
    )
    now = datetime.now(timezone.utc)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    event_id = client.post(
        "/api/events",
        json={
            "org_id": org,
            "slug": f"load-ev-{slug}",
            "title": "Load event",
            "starts_at": (now - timedelta(hours=1)).strftime(fmt),
            "ends_at": (now + timedelta(days=2)).strftime(fmt),
        },
        headers=admin,
    ).json()["event"]["id"]
    client.post(f"/api/events/{event_id}/publish", headers=admin).raise_for_status()

    n_vip = int(args.tickets * args.vip_share)
    plan = {"GA": args.tickets - n_vip, "VIP": n_vip}
    tickets: list[dict] = []
    type_ids: dict[str, str] = {}
    for tname, count in plan.items():
        tt = client.post(
            f"/api/events/{event_id}/ticket-types",
            json={"name": tname, "price_minor": 500, "quantity_total": count + 10, "max_per_order": ORDER_SIZE},
            headers=admin,
        )
        tt.raise_for_status()
        type_ids[tname] = tt.json()["ticket_type"]["id"]
        left = count
        while left > 0:
            q = min(ORDER_SIZE, left)
            order = client.post(
                "/api/orders",
                json={
                    "event_id": event_id,
                    "items": [{"ticket_type_id": type_ids[tname], "quantity": q}],
                    "buyer": {"email": f"buyer-{uuid.uuid4().hex[:8]}@example.com", "name": "Buyer"},
                    "provider": "manual",
                },
            )
            order.raise_for_status()
            paid = mark_paid_with_retry(client, admin, order.json()["order"]["id"])
            for t in paid.json()["tickets"]:
                tickets.append({"id": t["id"], "capability": t["capability"], "type": tname})
            left -= q
            if len(tickets) % 500 == 0:
                print(f"  {len(tickets)}/{args.tickets} tickets", flush=True)
    # station rules: food for everyone, after party and merch for VIP only
    for tname, tid in type_ids.items():
        rules = [("FOOD_ACCESS", 1)] + ([("AFTER_ENTRY", 1), ("MERCH_PICKUP", 1)] if tname == "VIP" else [])
        for station, max_uses in rules:
            store.execute(
                "INSERT INTO checkin_station_rules (event_id, ticket_type_id, station, max_uses) VALUES (?, ?, ?, ?)",
                (event_id, tid, station, max_uses),
            )
    store._pg.commit()  # 3A bug 3: the Store leaves work uncommitted; other connections would not see it
    store.close()
    Path(args.out).write_text(
        json.dumps(
            {
                "event_id": event_id,
                "scanner_token": scanner["Authorization"].removeprefix("Bearer "),
                "admin_token": admin["Authorization"].removeprefix("Bearer "),
                "tickets": tickets,
            }
        ),
        encoding="utf-8",
    )
    print(f"\nseeded event {event_id}: {len(tickets)} tickets -> {args.out}")


if __name__ == "__main__":
    main()
