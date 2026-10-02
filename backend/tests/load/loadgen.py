"""Pure-Python load generator (httpx + threads): same scenarios as locustfile.py, no native dependency.

Used where Locust cannot run (here: a Windows application-control policy blocks gevent's DLL).

    python tests/load/loadgen.py --scenario checkin --host http://127.0.0.1:8090 --users 10 --duration 45

Scenarios: checkin (scanners + syncers), scan, burst (syncers only, all at once), legacy3a (POST /api/scan).
The load model is the ASSUMPTION of docs/checkin/DESIGN.md §4.1, not project data. Prints a Markdown
table and writes ``--out`` (JSON) for PERF.md.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import threading
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

ap = argparse.ArgumentParser()
ap.add_argument("--scenario", default="checkin", choices=["checkin", "scan", "burst", "legacy3a"])
ap.add_argument("--host", default="http://127.0.0.1:8090", help="base URL; comma-separated list = clients spread round-robin (a reverse proxy)")
ap.add_argument("--users", type=int, default=10, help="door terminals (scanners)")
ap.add_argument("--syncers", type=int, default=0, help="terminals sending offline batches (checkin/burst)")
ap.add_argument("--duration", type=float, default=45.0)
ap.add_argument("--wait-min", type=float, default=1.5)  # ~0.5 scan/s per terminal x 10 terminals = 300/min
ap.add_argument("--wait-max", type=float, default=2.5)
ap.add_argument("--dup", type=float, default=0.1, help="share of repeated (duplicate) scans")
ap.add_argument("--batch", type=int, default=200)
ap.add_argument("--sync-wait", type=float, default=15.0)
ap.add_argument("--seed", default=str(Path(__file__).with_name(".seed.json")))
ap.add_argument("--out", default="")
ap.add_argument("--label", default="")
args = ap.parse_args()

HOSTS = [h.strip() for h in args.host.split(",") if h.strip()]
SEED = json.loads(Path(args.seed).read_text(encoding="utf-8"))
EVENT, TICKETS = SEED["event_id"], SEED["tickets"]
AUTH = {"Authorization": f"Bearer {SEED['scanner_token']}"}
split = int(len(TICKETS) * 0.6)
SCAN_POOL, SYNC_POOL = TICKETS[:split], TICKETS[split:]
lock = threading.Lock()
cursor = {"scan": 0, "sync": 0}
used: list[dict] = []
samples: dict[str, list[tuple[float, bool, int]]] = defaultdict(list)  # name -> (ms, ok, http status)
failures: Counter = Counter()
stop_at = 0.0
t_start = 0.0


def take(pool, key, n=1):
    """Next ``n`` tickets. The sync pool cycles: a reused ticket makes a real conflict (a heavier path)."""
    with lock:
        i = cursor[key]
        if key == "sync":
            cursor[key] = (i + n) % len(pool)
            return [pool[(i + k) % len(pool)] for k in range(n)]
        cursor[key] = min(i + n, len(pool))
        return pool[i : i + n]


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def record(name: str, ms: float, ok: bool, status: int, why: str = "") -> None:
    with lock:
        samples[name].append((ms, ok, status))
        if not ok:
            failures[f"{name}: {why or status}"] += 1


def pick_ticket() -> dict:
    with lock:
        dup = used and random.random() < args.dup
        if dup:
            return random.choice(used)
    got = take(SCAN_POOL, "scan")
    if not got:
        with lock:
            return random.choice(used or SCAN_POOL)
    with lock:
        used.append(got[0])
    return got[0]


def scanner(idx: int) -> None:
    terminal = str(uuid.uuid4())
    with httpx.Client(base_url=HOSTS[idx % len(HOSTS)], headers=AUTH, timeout=30) as c:
        while time.time() < stop_at:
            t = pick_ticket()
            if args.scenario == "legacy3a":
                name, path = "POST /api/scan (3A)", "/api/scan"
                body = {"event_id": EVENT, "capability": t["capability"], "device_id": terminal, "gate_id": "gate"}
                good = ("admitted", "duplicate")
                key = "result"
            else:
                name, path = "POST /api/checkin/scan", "/api/checkin/scan"
                body = {
                    "event_id": EVENT,
                    "terminal_id": terminal,
                    "station": "EVENT_ENTRY",
                    "capability": t["capability"],
                    "operation_id": str(uuid.uuid4()),
                }
                good = ("valid", "already_scanned")
                key = "server_decision"
            t0 = time.perf_counter()
            try:
                r = c.post(path, json=body)
                ms = (time.perf_counter() - t0) * 1000
                if r.status_code != 200:
                    record(name, ms, False, r.status_code)
                elif r.json().get(key) not in good:
                    record(name, ms, False, 200, f"unexpected {key}")
                else:
                    record(name, ms, True, 200)
            except Exception as exc:  # timeouts, resets
                record(name, (time.perf_counter() - t0) * 1000, False, 0, type(exc).__name__)
            time.sleep(random.uniform(args.wait_min, args.wait_max))


def syncer(idx: int) -> None:
    terminal = str(uuid.uuid4())
    name = f"POST /api/checkin/sync [{args.batch} ops]"
    with httpx.Client(base_url=HOSTS[idx % len(HOSTS)], headers=AUTH, timeout=60) as c:
        while time.time() < stop_at:
            tickets = take(SYNC_POOL, "sync", args.batch)
            if len(tickets) < args.batch:
                return
            now = datetime.now(timezone.utc)
            ops = [
                {
                    "operation_id": str(uuid.uuid4()),
                    "scan_id": str(uuid.uuid4()),
                    "ticket_id": tk["id"],
                    "participant_id": None,
                    "station": "eventEntry",
                    "decision": "valid",
                    "evaluated_at": iso(now - timedelta(seconds=random.randint(1, 900))),
                    "previous_scan_at": None,
                    "qr_version": 1,
                }
                for tk in tickets
            ]
            body = {
                "event_id": EVENT,
                "terminal_id": terminal,
                "batch_id": str(uuid.uuid4()),
                "device_sent_at": iso(now),
                "app_version": "load",
                "operations": ops,
            }
            t0 = time.perf_counter()
            try:
                r = c.post("/api/checkin/sync", json=body)
                ms = (time.perf_counter() - t0) * 1000
                if r.status_code != 200:
                    record(name, ms, False, r.status_code)
                else:
                    s = r.json().get("summary", {})
                    bad = s.get("rejected") or sum(s.values()) != args.batch
                    record(name, ms, not bad, 200, "bad summary")
            except Exception as exc:
                record(name, (time.perf_counter() - t0) * 1000, False, 0, type(exc).__name__)
            if args.scenario == "burst" and args.sync_wait <= 0:
                return
            time.sleep(args.sync_wait)


def pct(v: list[float], p: float) -> float:
    v = sorted(v)
    return v[min(len(v) - 1, int(round(p * (len(v) - 1))))]


def main() -> None:
    global stop_at, t_start
    n_scan = 0 if args.scenario == "burst" else args.users
    n_sync = args.syncers if args.scenario in ("checkin", "burst") else 0
    if args.scenario == "burst" and not n_sync:
        n_sync = args.users
    threads = [threading.Thread(target=scanner, args=(i,), daemon=True) for i in range(n_scan)]
    threads += [threading.Thread(target=syncer, args=(i,), daemon=True) for i in range(n_sync)]
    t_start = time.time()
    stop_at = t_start + args.duration
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=args.duration + 90)
    elapsed = time.time() - t_start
    rows = []
    for name, vals in sorted(samples.items()):
        ok = [ms for ms, good, _ in vals if good]
        n_fail = sum(1 for _, good, _ in vals if not good)
        allv = [ms for ms, _, _ in vals]
        rows.append(
            {
                "name": name,
                "requests": len(vals),
                "failures": n_fail,
                "rps": round(len(vals) / elapsed, 1),
                "p50": round(pct(ok or allv, 0.50), 1),
                "p95": round(pct(ok or allv, 0.95), 1),
                "p99": round(pct(ok or allv, 0.99), 1),
                "max": round(max(allv), 1),
            }
        )
    label = f" ({args.label})" if args.label else ""
    print(f"### {args.scenario}{label}: {n_scan} scanners + {n_sync} syncers, {elapsed:.0f} s\n")
    print("| Request | n | fail | req/s | p50 ms | p95 ms | p99 ms | max ms |\n|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        print(f"| {r['name']} | {r['requests']} | {r['failures']} | {r['rps']} | {r['p50']} | {r['p95']} | {r['p99']} | {r['max']} |")
    if failures:
        print("\nFailures: " + "; ".join(f"{k} x{v}" for k, v in failures.most_common(5)))
    if args.out:
        Path(args.out).write_text(json.dumps({"args": vars(args), "rows": rows, "failures": failures}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
