"""Micro-benchmark of the write path: row-by-row inserts versus the module's bulk statements.

    CHECKIN_LOAD_DATABASE_URL=postgresql://...@127.0.0.1:5434/chantier3a_perf \
        python tests/load/bench_bulk.py --ops 200 --runs 30

For one batch of ``--ops`` operations it compares, on the same database:
  naive      one INSERT + COMMIT per operation, ``try/except`` on the unique violation, one SELECT per ticket
  optimised  repository.load_tickets (1 query) + repository.insert_logs (1 statement, ON CONFLICT DO NOTHING)
Truncates scan_logs first and last: use a disposable database only.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from checkin import repository  # noqa: E402

ROW_SQL_COLS = [c for c, _ in repository._LOG_COLUMNS]


def make_rows(event_id: str, terminal: str, tickets: list[str], now: datetime) -> list[dict]:
    return [
        {
            "operation_id": uuid.uuid4(),
            "scan_id": uuid.uuid4(),
            "payload_hash": b"\x00" * 32,
            "event_id": event_id,
            "ticket_id": t,
            "participant_ref": None,
            "terminal_id": terminal,
            "staff_user_id": None,
            "station": "EVENT_ENTRY",
            "reported_decision": "valid",
            "reported_valid": True,
            "server_decision": "valid",
            "server_reason": "",
            "capability_verified": None,
            "is_claim": True,
            "ack_status": "accepted",
            "device_evaluated_at": now,
            "device_sent_at": now,
            "server_received_at": now,
            "clock_offset_ms": 0,
            "corrected_evaluated_at": now,
            "clock_suspect": False,
            "clock_suspect_reason": "",
            "app_version": "bench",
            "qr_version": 1,
            "connection_status": "offline_synced",
            "batch_id": uuid.uuid4(),
        }
        for t in tickets
    ]


def naive(conn: psycopg.Connection, rows: list[dict]) -> None:
    sql = f"INSERT INTO scan_logs ({', '.join(ROW_SQL_COLS)}) VALUES ({', '.join(['%s'] * len(ROW_SQL_COLS))})"
    for r in rows:
        conn.execute("SELECT id, status FROM tickets WHERE id = %s", (r["ticket_id"],)).fetchone()  # N+1
        try:
            conn.execute(sql, tuple(r[c] for c in ROW_SQL_COLS))
            conn.commit()  # what Store.execute does on every call
        except psycopg.errors.UniqueViolation:
            conn.rollback()


def optimised(conn: psycopg.Connection, rows: list[dict]) -> None:
    with conn.transaction():
        repository.load_tickets(conn, [r["ticket_id"] for r in rows])
        repository.insert_logs(conn, rows)


def pct(values: list[float], p: float) -> float:
    values = sorted(values)
    return values[min(len(values) - 1, int(round(p * (len(values) - 1))))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ops", type=int, default=200)
    ap.add_argument("--runs", type=int, default=30)
    args = ap.parse_args()
    url = os.environ.get("CHECKIN_LOAD_DATABASE_URL", "")
    if not urlparse(url).path.lstrip("/").endswith(("_perf", "_test")):
        sys.exit("set CHECKIN_LOAD_DATABASE_URL to a disposable *_perf / *_test database")
    seed = json.loads((Path(__file__).with_name(".seed.json")).read_text(encoding="utf-8"))
    ids = [t["id"] for t in seed["tickets"]]
    terminal = str(uuid.uuid4())
    results: dict[str, list[float]] = {"naive": [], "optimised": []}
    with psycopg.connect(url, row_factory=dict_row) as conn:
        conn.execute("TRUNCATE scan_logs CASCADE")
        conn.commit()
        for mode, fn in (("naive", naive), ("optimised", optimised)):
            for i in range(args.runs + 3):  # 3 warm-up runs, discarded
                rows = make_rows(seed["event_id"], terminal, ids[: args.ops], datetime.now(timezone.utc))
                t0 = time.perf_counter()
                fn(conn, rows)
                dt = (time.perf_counter() - t0) * 1000
                if i >= 3:
                    results[mode].append(dt)
        conn.execute("TRUNCATE scan_logs CASCADE")
        conn.commit()
    print(f"batch of {args.ops} operations, {args.runs} runs each (ms):")
    for mode, vals in results.items():
        print(
            f"  {mode:10s} p50={statistics.median(vals):8.1f}  p95={pct(vals, 0.95):8.1f}  "
            f"max={max(vals):8.1f}  mean={statistics.mean(vals):8.1f}"
        )
    ratio = statistics.median(results["naive"]) / max(statistics.median(results["optimised"]), 0.001)
    print(f"  => optimised is {ratio:.0f}x faster at the median")


if __name__ == "__main__":
    main()
