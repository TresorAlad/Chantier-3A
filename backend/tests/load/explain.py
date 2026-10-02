"""EXPLAIN (ANALYZE, BUFFERS) of every hot query of the module, with the module's own SQL.

    CHECKIN_LOAD_DATABASE_URL=postgresql://...@127.0.0.1:5434/chantier3a_perf \
        python tests/load/explain.py --scale 200000 > explain.md

The real repository functions are called through a proxy connection that runs
``EXPLAIN (ANALYZE, BUFFERS)`` on each statement, so the plans are those of the code, not a copy of it.
Everything happens in a transaction that is rolled back, except the optional ``--scale`` data
(synthetic journal rows, committed: use a disposable database only).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).parent))

from bench_bulk import make_rows  # noqa: E402

from checkin import repository  # noqa: E402

SKIP_PREFIXES = ("SELECT SET_CONFIG", "SELECT PG_ADVISORY", "SELECT PG_TRY")


class ExplainConn:
    """Runs EXPLAIN (ANALYZE, BUFFERS) on each statement, records the plan, then runs it for real."""

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn
        self.label = ""
        self.plans: list[tuple[str, str, list[str]]] = []

    def execute(self, query, params=None, **kw):
        q = query if isinstance(query, str) else str(query)
        if not q.strip().upper().startswith(SKIP_PREFIXES):
            rows = self._conn.execute("EXPLAIN (ANALYZE, BUFFERS) " + q, params).fetchall()
            self.plans.append((self.label, " ".join(q.split())[:200], [r["QUERY PLAN"] for r in rows]))
        return self._conn.execute(query, params, **kw)

    def __getattr__(self, name):
        return getattr(self._conn, name)


def summarise(plan: list[str]) -> tuple[float, str, str]:
    text = "\n".join(plan)
    m = re.search(r"Execution Time: ([\d.]+) ms", text)
    t = float(m.group(1)) if m else float("nan")
    idx = sorted(set(re.findall(r"(?:Index(?: Only)? Scan|Bitmap Index Scan) (?:Backward )?(?:using|on) (\w+)", text)))
    seq = sorted(set(re.findall(r"Seq Scan on (\w+)", text)))
    reads = re.search(r"Buffers: shared hit=(\d+)(?: read=(\d+))?", text)
    buf = f"hit={reads.group(1)} read={reads.group(2) or 0}" if reads else ""
    return t, (", ".join(idx) or "—"), (", ".join(seq) or "—") + (f" | {buf}" if buf else "")


def scale_up(conn: psycopg.Connection, event_id: str, n: int) -> None:
    conn.execute(
        """
        INSERT INTO scan_logs (operation_id, payload_hash, event_id, ticket_id, terminal_id, station, reported_valid,
                               server_decision, is_claim, ack_status, server_received_at, corrected_evaluated_at,
                               connection_status)
        SELECT gen_random_uuid(), '\\x00'::bytea, %(ev)s, ids[1 + floor(random() * array_length(ids, 1))::int],
               md5((g %% 10)::text)::uuid,
               (ARRAY['EVENT_ENTRY','FOOD_ACCESS','MERCH_PICKUP','AFTER_ENTRY'])[1 + floor(random() * 4)::int],
               true, 'valid', random() < 0.6, 'accepted',
               now() - random() * interval '8 hours', now() - random() * interval '8 hours', 'offline_synced'
        FROM generate_series(1, %(n)s) g, (SELECT array_agg(id) AS ids FROM tickets WHERE event_id = %(ev)s) t
        """,
        {"ev": event_id, "n": n},
    )
    conn.commit()
    conn.execute("ANALYZE scan_logs")
    conn.commit()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=int, default=0, help="synthetic journal rows to add first (committed)")
    ap.add_argument("--ops", type=int, default=200)
    args = ap.parse_args()
    url = os.environ.get("CHECKIN_LOAD_DATABASE_URL", "")
    if not urlparse(url).path.lstrip("/").endswith(("_perf", "_test")):
        sys.exit("set CHECKIN_LOAD_DATABASE_URL to a disposable *_perf / *_test database")
    seed = json.loads(Path(__file__).with_name(".seed.json").read_text(encoding="utf-8"))
    event_id = seed["event_id"]
    ids = [t["id"] for t in seed["tickets"]][: args.ops * 2]

    with psycopg.connect(url, row_factory=dict_row) as conn:
        if args.scale:
            scale_up(conn, event_id, args.scale)
        counts = {
            t: conn.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"]
            for t in ("tickets", "scan_logs", "station_consumptions", "scan_conflicts")
        }
        now = datetime.now(timezone.utc)
        terminal = str(uuid.uuid4())
        conn.execute("INSERT INTO checkin_terminals (terminal_id, event_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (terminal, event_id))
        conn.commit()
        type_ids = [r["id"] for r in conn.execute("SELECT id FROM ticket_types WHERE event_id = %s", (event_id,)).fetchall()]
        with conn.transaction(force_rollback=True):
            ex = ExplainConn(conn)
            first = make_rows(event_id, terminal, ids[: args.ops], now)
            logs = repository.insert_logs(conn, first)  # real insert (rolled back): data for the next calls
            pairs = [(r["ticket_id"], "EVENT_ENTRY") for r in first]
            op_ids = [r["operation_id"] for r in first[:100]] + [uuid.uuid4() for _ in range(100)]

            def run(label, fn):
                ex.label = label
                return fn()

            run("load_tickets (200 ids, one query)", lambda: repository.load_tickets(ex, ids[: args.ops]))
            run("load_rules (event, all types)", lambda: repository.load_rules(ex, event_id, type_ids))
            run("find_operations (200 ids, replay check)", lambda: repository.find_operations(ex, op_ids))
            run("fetch_claims (200 (ticket, station) pairs)", lambda: repository.fetch_claims(ex, pairs))
            second = make_rows(event_id, terminal, ids[args.ops : args.ops * 2], now)
            run("insert_logs (200 rows, ON CONFLICT DO NOTHING)", lambda: repository.insert_logs(ex, second))
            cons = [
                (r["ticket_id"], "EVENT_ENTRY", 0, event_id, logs[str(r["operation_id"])], now) for r in first
            ]
            run("upsert_consumptions (200 rows)", lambda: repository.upsert_consumptions(ex, cons))
            confl = [
                (event_id, r["ticket_id"], "EVENT_ENTRY", None, logs[str(r["operation_id"])], "SAME_TERMINAL_REPLAY", False)
                for r in first
            ]
            run("upsert_conflicts (200 rows)", lambda: repository.upsert_conflicts(ex, confl))
            run("list_logs (page of 200, cursor)", lambda: repository.list_logs(
                ex, event_id=event_id, station=None, ticket_id=None, terminal_id=None, since=None, cursor=0, limit=201))
            run("list_logs (filter terminal_id)", lambda: repository.list_logs(
                ex, event_id=event_id, station=None, ticket_id=None, terminal_id=uuid.UUID(terminal), since=None, cursor=None, limit=201))
            run("list_logs (filter ticket_id)", lambda: repository.list_logs(
                ex, event_id=event_id, station=None, ticket_id=ids[0], terminal_id=None, since=None, cursor=None, limit=201))
            run("list_conflicts (open, newest first)", lambda: repository.list_conflicts(
                ex, event_id=event_id, status="open", ctype=None, cursor=None, limit=101))
            run("stats (4 aggregate queries)", lambda: repository.stats(ex, event_id))
            run("snapshot refresh (recompute entitlements)", lambda: repository.refresh_entitlements_if_stale(ex, event_id, 0))
            run("snapshot_page (delta, 2000 rows)", lambda: repository.snapshot_page(
                ex, event_id, since=0, pin=10**9, after=None, limit=2001))

    print("## Query plans (EXPLAIN ANALYZE, BUFFERS)\n")
    print(f"Table sizes: " + ", ".join(f"{k}={v:,}" for k, v in counts.items()) + "\n")
    print("| Query | Execution (ms) | Index used | Seq scan on / buffers |\n|---|---:|---|---|")
    seen = set()
    for label, sql, plan in ex.plans:
        t, idx, seq = summarise(plan)
        print(f"| {label} | {t:.2f} | {idx} | {seq} |")
        seen.add(label)
    print("\n<details><summary>Full plans</summary>\n")
    for label, sql, plan in ex.plans:
        print(f"### {label}\n\n```\n{sql}\n\n" + "\n".join(plan) + "\n```\n")
    print("</details>")


if __name__ == "__main__":
    main()
