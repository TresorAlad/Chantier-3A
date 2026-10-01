"""Use cases of the check-in module (orchestration of ``domain`` and ``repository``)."""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import threading
import uuid
from collections import OrderedDict
from datetime import datetime
from typing import Any

import psycopg

from checkin import domain, repository
from checkin.domain import Claim
from checkin.runtime import Runtime
from checkin.ports import Principal
from checkin.schemas import ScanRequest
from tickets import capability as cap


class ApiError(Exception):
    """A stable, client-visible error: HTTP status + snake_case code + human message."""

    def __init__(self, status: int, code: str, message: str, headers: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.headers = headers or {}


# ── Capability verification (crypto stays in tickets/capability.py) ─────────


def verify_capability(
    token: str,
    *,
    keys_for_event,
    now: datetime,
) -> tuple[cap.Payload | None, str, str, bool | None, str | None]:
    """Verify a QR capability.

    Returns ``(payload, decision, reason, signature_verified, audit_ticket_id)``.
    ``decision`` is ``valid`` when the capability itself is fine; event matching is the caller's job.
    ``audit_ticket_id`` is only set when the signature was verified (never from a forged token).
    """
    try:
        token_event = cap.peek_eid(token)
    except Exception:
        return None, domain.INVALID, "malformed", None, None
    ring = cap.KeyRing(event_id=token_event, keys=keys_for_event(token_event))
    try:
        payload = cap.verify_with_ring(token, ring, now)
        return payload, domain.VALID, "", True, payload.tid
    except cap.CapabilityError as err:
        decision, reason = domain.classify_capability_error(err)
        signed_ok: bool | None
        if isinstance(err, (cap.ErrExpired, cap.ErrNotYetValid)):
            signed_ok = True  # the signature is checked before the validity window
            try:
                tid = cap._peek_payload_field(token, "tid") or None
            except Exception:
                tid = None
            return None, decision, reason, signed_ok, tid
        if isinstance(err, cap.ErrBadSignature):
            signed_ok = False
        else:
            signed_ok = None
        return None, decision, reason, signed_ok, None
    except Exception:
        return None, domain.INVALID, "malformed", None, None


# ── Shared: persist a resolution ────────────────────────────────────────────


def apply_resolution(
    conn: psycopg.Connection,
    *,
    event_id: str,
    ticket_id: str,
    station: str,
    resolution: domain.Resolution,
    log_ids: dict[str, int],
) -> None:
    """Write consumptions and conflicts of one (ticket, station) group (idempotent upserts)."""
    repository.upsert_consumptions(
        conn,
        [
            (ticket_id, station, i, event_id, log_ids[c.operation_id], c.corrected_at)
            for i, c in enumerate(resolution.assigned)
        ],
    )
    repository.upsert_conflicts(
        conn,
        [
            (
                event_id,
                ticket_id,
                station,
                log_ids[s.winning_operation_id] if s.winning_operation_id else None,
                log_ids[s.losing_operation_id],
                s.type,
                s.clock_suspect,
            )
            for s in resolution.conflicts
        ],
    )


# ── Online scan (TDEV-54) ───────────────────────────────────────────────────


def _online_hash(req: ScanRequest, station: str) -> bytes:
    """Hash of the non-secret request fields. The capability (QR) is deliberately excluded."""
    return domain.payload_hash(
        {
            "kind": "online",
            "event_id": req.event_id,
            "terminal_id": str(req.terminal_id),
            "station": station,
            "scanned_at": req.scanned_at.isoformat() if req.scanned_at else None,
        }
    )


def _replay_response(stored: dict, station: str) -> dict:
    return {
        "status": "already_processed",
        "server_decision": stored["server_decision"],
        "reason": stored["server_reason"],
        "ticket_id": stored["ticket_id"] or "",
        "serial": "",
        "station": stored["station"],
        "use_index": None,
        "first_scanned_at": None,
        "operation_id": str(stored["operation_id"]),
    }


def online_scan(rt: Runtime, conn: psycopg.Connection, principal: Principal, req: ScanRequest) -> dict:
    """Verify a capability, apply the station rule, consume atomically and journal."""
    station = domain.normalize_station(req.station)
    if station is None or station not in rt.cfg.stations:
        raise ApiError(400, "unknown_station", "station is not configured for check-in")
    now = rt.clock()
    op_id = req.operation_id or uuid.uuid4()
    p_hash = _online_hash(req, station)

    stored = repository.find_operations(conn, [op_id]).get(str(op_id))
    if stored is not None:
        if bytes(stored["payload_hash"]) != p_hash:
            raise ApiError(409, "operation_id_reuse", "operation_id was already used for another scan")
        return _replay_response(stored, station)

    payload, decision, reason, sig_ok, audit_tid = verify_capability(
        req.capability,
        keys_for_event=lambda ev: rt.keys.issuer_keys(conn, ev),
        now=now,
    )
    conn.commit()  # end the read-only transaction: the write transaction below is a real one

    ticket_id = audit_tid
    ticket = None
    elig: domain.Eligibility | None = None
    rules: dict[str, dict[str, int]] = {}
    if payload is not None:
        ticket_id = payload.tid
        if payload.eid != req.event_id:
            decision, reason = domain.WRONG_EVENT, "wrong_event"
        else:
            tickets = repository.load_tickets(conn, [payload.tid])
            ticket = tickets.get(payload.tid)
            if ticket is not None:
                rules = repository.load_rules(conn, req.event_id, [ticket.ticket_type_id])
            elig = domain.check_eligibility(
                ticket=ticket,
                event_id=req.event_id,
                station=station,
                explicit_rules=rules.get(ticket.ticket_type_id, {}) if ticket else {},
                at=now,
                capability_verified=True,
            )
            decision, reason = elig.decision, elig.reason
    conn.commit()

    row: dict[str, Any] = {
        "operation_id": op_id,
        "scan_id": None,
        "payload_hash": p_hash,
        "event_id": req.event_id,
        "ticket_id": ticket_id,
        "participant_ref": None,
        "terminal_id": req.terminal_id,
        "staff_user_id": principal.user_id,
        "station": station,
        "reported_decision": None,
        "reported_valid": False,
        "server_reason": reason,
        "capability_verified": sig_ok,
        "ack_status": "accepted",
        "device_evaluated_at": req.scanned_at,
        "device_sent_at": None,
        "server_received_at": now,
        "clock_offset_ms": 0,
        "corrected_evaluated_at": now,
        "clock_suspect": False,
        "clock_suspect_reason": "",
        "app_version": req.app_version,
        "qr_version": cap.CURRENT_VERSION if payload is not None else None,
        "connection_status": "online",
        "batch_id": None,
    }

    first_scanned_at: datetime | None = None
    use_index: int | None = None
    try:
        with conn.transaction():
            repository.set_lock_timeout(conn, rt.cfg.lock_timeout_ms)
            resolution: domain.Resolution | None = None
            existing: list[Claim] = []
            if elig is not None and elig.eligible:
                repository.lock_groups(conn, [repository.group_key(ticket_id, station)])
                existing = repository.fetch_claims(conn, [(ticket_id, station)]).get((ticket_id, station), [])
                mine = Claim(str(op_id), str(req.terminal_id), now, False)
                resolution = domain.resolve(existing + [mine], elig.max_uses)
                use_index = resolution.use_index_of(mine.operation_id)
                if use_index is None:
                    decision, reason = domain.ALREADY_SCANNED, "already_scanned"
                    if resolution.assigned:
                        first_scanned_at = min(c.corrected_at for c in resolution.assigned)
                    resolution = None  # the loser is not a claimant: nothing to rewrite
            row["server_decision"] = decision
            row["server_reason"] = reason
            row["is_claim"] = resolution is not None
            inserted = repository.insert_logs(conn, [row])
            if str(op_id) not in inserted:
                raise _Concurrent
            if resolution is not None:
                log_ids = {c.operation_id: c.log_id for c in existing if c.log_id is not None}
                log_ids[str(op_id)] = inserted[str(op_id)]
                apply_resolution(
                    conn,
                    event_id=req.event_id,
                    ticket_id=ticket_id,
                    station=station,
                    resolution=resolution,
                    log_ids=log_ids,
                )
    except _Concurrent:
        stored = repository.find_operations(conn, [op_id]).get(str(op_id))
        if stored is None or bytes(stored["payload_hash"]) != p_hash:
            raise ApiError(409, "operation_id_reuse", "operation_id was already used for another scan") from None
        return _replay_response(stored, station)
    except psycopg.errors.LockNotAvailable as err:
        raise ApiError(503, "service_busy", "check-in is busy, retry", {"Retry-After": "1"}) from err

    return {
        "status": "accepted",
        "server_decision": decision,
        "reason": reason,
        "ticket_id": ticket_id or "",
        "serial": ticket.serial if ticket else "",
        "station": station,
        "use_index": use_index,
        "first_scanned_at": first_scanned_at,
        "operation_id": str(op_id),
    }


class _Concurrent(Exception):
    """The operation_id was inserted by a concurrent request (treated as a replay)."""


# ── Snapshot (TDEV-54) ──────────────────────────────────────────────────────


class _BytesCache:
    """Tiny thread-safe LRU of pre-serialised (and pre-gzipped) snapshot pages, per process."""

    def __init__(self, size: int = 64) -> None:
        self._size = size
        self._data: OrderedDict[str, tuple[bytes, bytes]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> tuple[bytes, bytes] | None:
        with self._lock:
            value = self._data.get(key)
            if value is not None:
                self._data.move_to_end(key)
            return value

    def put(self, key: str, value: tuple[bytes, bytes]) -> None:
        with self._lock:
            self._data[key] = value
            self._data.move_to_end(key)
            while len(self._data) > self._size:
                self._data.popitem(last=False)


SNAPSHOT_CACHE = _BytesCache()


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def snapshot(
    rt: Runtime,
    conn: psycopg.Connection,
    *,
    event_id: str,
    since_version: int,
    cursor: str | None,
    limit: int | None,
) -> tuple[str, bytes, bytes]:
    """Return ``(etag, json_bytes, gzip_bytes)`` for one page of entitlements."""
    limit = min(max(limit or rt.cfg.snapshot_page_default, 1), rt.cfg.snapshot_page_max)
    meta = repository.refresh_entitlements_if_stale(conn, event_id, rt.cfg.snapshot_ttl_seconds)
    conn.commit()
    pin = int(meta["max_version"] or 0)
    after: tuple[int, str] | None = None
    if cursor:
        try:
            pin, last_version, last_ticket = repository.decode_cursor(cursor)
        except Exception as err:
            raise ApiError(400, "invalid_request", "invalid cursor") from err
        after = (last_version, last_ticket)
    etag = '"' + hashlib.md5(f"{event_id}|{pin}|{since_version}|{cursor or ''}|{limit}".encode()).hexdigest() + '"'
    cached = SNAPSHOT_CACHE.get(etag)
    if cached is not None:
        return etag, cached[0], cached[1]

    rows = repository.snapshot_page(conn, event_id, since=since_version, pin=pin, after=after, limit=limit + 1)
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = repository.encode_cursor(pin, rows[-1]["version"], rows[-1]["ticket_id"]) if has_more else None
    keys = rt.keys.issuer_keys(conn, event_id)
    conn.commit()
    body = {
        "schema_version": 1,
        "event_id": event_id,
        "snapshot_version": pin,
        "since_version": since_version,
        "generated_at": rt.clock().isoformat().replace("+00:00", "Z"),
        "has_more": has_more,
        "next_cursor": next_cursor,
        "issuer_keys": {kid: _b64url(pub) for kid, pub in keys.items()},
        "entitlements": [
            {
                "ticket_id": r["ticket_id"],
                "serial": r["serial"],
                "ticket_type_id": r["ticket_type_id"],
                "status": r["status"],
                "stations": list(r["stations"]),
                "uses": r["uses"],
                "version": r["version"],
            }
            for r in rows
        ],
    }
    raw = json.dumps(body, separators=(",", ":")).encode()
    packed = gzip.compress(raw, compresslevel=5)
    SNAPSHOT_CACHE.put(etag, (raw, packed))
    return etag, raw, packed
