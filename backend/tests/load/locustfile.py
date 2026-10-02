"""Locust scenarios for the check-in API (opening rush). See tests/load/README.md.

SCENARIO (environment variable):
  checkin   door scanners (online /scan) + offline syncers (/sync batches)   [default]
  scan      online scans only
  burst     offline syncers only: a burst of batches after a network cut
  legacy3a  the existing 3A POST /api/scan, as the "before" reference

Load model = the ASSUMPTIONS of docs/checkin/DESIGN.md §4.1 (3000 participants, 10 terminals, peak
300 scans/min, batches of 200 operations). They are assumptions, not project data.
"""

from __future__ import annotations

import json
import os
import random
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from locust import HttpUser, between, constant, task

SEED = json.loads(Path(os.environ.get("CHECKIN_SEED", Path(__file__).with_name(".seed.json"))).read_text(encoding="utf-8"))
EVENT = SEED["event_id"]
AUTH = {"Authorization": f"Bearer {SEED['scanner_token']}"}
TICKETS = SEED["tickets"]
SCENARIO = os.environ.get("SCENARIO", "checkin")
DUPLICATE_RATIO = float(os.environ.get("DUPLICATE_RATIO", "0.1"))
BATCH = int(os.environ.get("SYNC_BATCH_SIZE", "200"))
WAIT_MIN = float(os.environ.get("WAIT_MIN", "1.5"))  # ~0.5 scan/s per terminal x 10 terminals = 300/min
WAIT_MAX = float(os.environ.get("WAIT_MAX", "2.5"))
SYNC_WAIT = float(os.environ.get("SYNC_WAIT", "15"))

# 60 % of the tickets are for online scans, 40 % for offline batches (each ticket is used once).
_SPLIT = int(len(TICKETS) * 0.6)
_SCAN_POOL, _SYNC_POOL = TICKETS[:_SPLIT], TICKETS[_SPLIT:]
_lock = threading.Lock()
_next = {"scan": 0, "sync": 0}
_used: list[dict] = []


def _take(pool: list[dict], key: str, n: int = 1) -> list[dict]:
    with _lock:
        start = _next[key]
        _next[key] = min(start + n, len(pool))
        got = pool[start : start + n]
    return got


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class _Scanner(HttpUser):
    abstract = True
    wait_time = between(WAIT_MIN, WAIT_MAX)

    def on_start(self) -> None:
        self.terminal = str(uuid.uuid4())

    def _pick(self) -> dict:
        if _used and random.random() < DUPLICATE_RATIO:
            return random.choice(_used)
        got = _take(_SCAN_POOL, "scan")
        if not got:
            return random.choice(_used or _SCAN_POOL)
        _used.append(got[0])
        return got[0]


if SCENARIO in ("checkin", "scan"):

    class DoorScanner(_Scanner):
        weight = 10

        @task
        def scan(self) -> None:
            t = self._pick()
            body = {
                "event_id": EVENT,
                "terminal_id": self.terminal,
                "station": "EVENT_ENTRY",
                "capability": t["capability"],
                "operation_id": str(uuid.uuid4()),
            }
            with self.client.post(
                "/api/checkin/scan", json=body, headers=AUTH, name="POST /api/checkin/scan", catch_response=True
            ) as r:
                if r.status_code != 200:
                    return r.failure(f"HTTP {r.status_code}")
                decision = r.json().get("server_decision")
                if decision not in ("valid", "already_scanned"):
                    r.failure(f"unexpected decision {decision}")


if SCENARIO in ("checkin", "burst"):

    class OfflineSyncer(HttpUser):
        weight = 1
        wait_time = constant(SYNC_WAIT)

        def on_start(self) -> None:
            self.terminal = str(uuid.uuid4())

        @task
        def sync(self) -> None:
            tickets = _take(_SYNC_POOL, "sync", BATCH)
            if len(tickets) < BATCH:
                return  # pool exhausted: nothing fresh to send
            now = datetime.now(timezone.utc)
            ops = [
                {
                    "operation_id": str(uuid.uuid4()),
                    "scan_id": str(uuid.uuid4()),
                    "ticket_id": t["id"],
                    "participant_id": None,
                    "station": "eventEntry",
                    "decision": "valid",
                    "evaluated_at": _iso(now - timedelta(seconds=random.randint(1, 900))),
                    "previous_scan_at": None,
                    "qr_version": 1,
                }
                for t in tickets
            ]
            body = {
                "event_id": EVENT,
                "terminal_id": self.terminal,
                "batch_id": str(uuid.uuid4()),
                "device_sent_at": _iso(now),
                "app_version": "load",
                "operations": ops,
            }
            with self.client.post(
                "/api/checkin/sync", json=body, headers=AUTH, name=f"POST /api/checkin/sync [{BATCH} ops]", catch_response=True
            ) as r:
                if r.status_code != 200:
                    return r.failure(f"HTTP {r.status_code}")
                summary = r.json().get("summary", {})
                if summary.get("rejected") or sum(summary.values()) != BATCH:
                    r.failure(f"bad summary {summary}")


if SCENARIO == "legacy3a":

    class LegacyScanner(_Scanner):
        """The existing 3A endpoint: single shared connection, one scan per call."""

        @task
        def scan(self) -> None:
            t = self._pick()
            body = {"event_id": EVENT, "capability": t["capability"], "device_id": self.terminal, "gate_id": "gate"}
            with self.client.post("/api/scan", json=body, headers=AUTH, name="POST /api/scan (3A)", catch_response=True) as r:
                if r.status_code == 429:
                    return r.failure("429 rate_limited (3A limiter: 120/min per IP)")
                if r.status_code != 200:
                    return r.failure(f"HTTP {r.status_code}")
                if r.json().get("result") not in ("admitted", "duplicate"):
                    r.failure(f"unexpected result {r.json().get('result')}")
