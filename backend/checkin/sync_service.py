"""Offline sync, conflicts and stats (TDEV-55). Algorithm and rationale: docs/checkin/ADR-001-conflits.md."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import psycopg
from pydantic import ValidationError

from checkin import domain, repository
from checkin.domain import Claim
from checkin.ports import Principal
from checkin.runtime import Runtime
from checkin.schemas import SyncOperation, SyncRequest
from checkin.service import ApiError, apply_resolution, verify_capability
from tickets import capability as cap


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _aware(dt: datetime) -> datetime:
    """Naive timestamps are read as UTC (the 3B app sends ``toUtc().toIso8601String()``)."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _rejected(oid: str | None, code: str, message: str) -> dict:
    return {"operation_id": oid, "status": "rejected", "error_code": code, "message": message}


def _safe_uuid(value: Any) -> str | None:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        return None


@dataclass
class _Op:
    """One validated offline operation with everything the decision needs."""

    idx: int
    op: SyncOperation
    oid: str
    station: str
    reported: str  # normalized terminal decision
    hash: bytes
    clock: domain.ClockInfo
    capability_verified: bool | None = None
    cap_override: tuple[str, str] | None = None
    ticket: domain.TicketFacts | None = None
    elig: domain.Eligibility | None = None

    @property
    def claims(self) -> bool:
        """The terminal let the person in and the server finds nothing against it."""
        return self.reported == domain.VALID and self.elig is not None and self.elig.eligible


def _sync_hash(req: SyncRequest, op: SyncOperation, station: str) -> bytes:
    """Hash of the contract fields; excludes the capability (QR) and per-attempt batch fields."""
    return domain.payload_hash(
        {
            "kind": "sync",
            "event_id": req.event_id,
            "terminal_id": str(req.terminal_id),
            "operation_id": str(op.operation_id),
            "scan_id": str(op.scan_id) if op.scan_id else None,
            "ticket_id": op.ticket_id,
            "participant_id": op.participant_id,
            "station": station,
            "decision": op.decision,
            "evaluated_at": _iso(_aware(op.evaluated_at)),
            "previous_scan_at": _iso(_aware(op.previous_scan_at)) if op.previous_scan_at else None,
            "qr_version": op.qr_version,
            "staff_id": op.staff_id,
        }
    )


def _conflict_view(
    ctype: str, winner: Claim | None = None, *, terminal: str | None = None, at: datetime | None = None
) -> dict:
    return {
        "type": ctype,
        "winning_terminal_id": winner.terminal_id if winner else terminal,
        "winning_at": _iso(winner.corrected_at if winner else at),
    }


def sync_batch(rt: Runtime, conn: psycopg.Connection, principal: Principal, req: SyncRequest) -> dict:
    """Process a batch of offline operations: partial results, idempotent, order-independent."""
    cfg = rt.cfg
    raw_ops = req.operations
    if not raw_ops:
        raise ApiError(400, "batch_empty", "operations must not be empty")
    if len(raw_ops) > cfg.sync_max_batch:
        raise ApiError(413, "batch_too_large", f"at most {cfg.sync_max_batch} operations per batch")

    received = rt.clock()
    sent = _aware(req.device_sent_at)
    event_id = req.event_id
    results: list[dict | None] = [None] * len(raw_ops)
    parsed: list[_Op] = []
    parsed_by_idx: dict[int, _Op] = {}
    first_idx: dict[str, int] = {}
    dup_of: dict[int, int] = {}

    # 1. Validate each operation on its own: a bad item never fails the batch.
    for idx, raw in enumerate(raw_ops):
        if not isinstance(raw, dict):
            results[idx] = _rejected(None, "operation_invalid", "operation must be an object")
            continue
        oid_hint = _safe_uuid(raw.get("operation_id"))
        try:
            op = SyncOperation.model_validate(raw)
        except ValidationError as exc:
            first = exc.errors()[0]  # location and rule only: never the submitted value
            where = ".".join(str(p) for p in first.get("loc", ()))
            results[idx] = _rejected(oid_hint, "operation_invalid", f"{where}: {first.get('msg', 'invalid')}")
            continue
        oid = str(op.operation_id)
        station = domain.normalize_station(op.station)
        if station is None or station not in cfg.stations:
            results[idx] = _rejected(oid, "unknown_station", "station is not configured for check-in")
            continue
        reported = domain.normalize_decision(op.decision)
        if reported is None:
            results[idx] = _rejected(oid, "invalid_decision", "unknown decision value")
            continue
        if op.qr_version not in (None, cap.CURRENT_VERSION):
            results[idx] = _rejected(oid, "unsupported_qr_version", "unsupported qr_version")
            continue
        if reported == domain.VALID and not op.ticket_id:
            results[idx] = _rejected(oid, "operation_invalid", "ticket_id: required when decision is valid")
            continue
        h = _sync_hash(req, op, station)
        if oid in first_idx:
            if parsed_by_idx[first_idx[oid]].hash == h:
                dup_of[idx] = first_idx[oid]
            else:
                results[idx] = _rejected(oid, "operation_id_reuse", "operation_id repeated with different content")
            continue
        clock = domain.correct_clock(
            device_evaluated_at=_aware(op.evaluated_at),
            device_sent_at=sent,
            received_at=received,
            thresholds=cfg.clock,
        )
        p = _Op(idx, op, oid, station, reported, h, clock)
        parsed.append(p)
        parsed_by_idx[idx] = p
        first_idx[oid] = idx
    offset_ms = domain._ms(received - sent)

    # 2. Optional capability re-verification, at the time of the scan (the QR is never stored).
    keys_cache: dict[str, dict[str, bytes]] = {}

    def keys_for(ev: str) -> dict[str, bytes]:
        if ev not in keys_cache:
            keys_cache[ev] = rt.keys.issuer_keys(conn, ev)
        return keys_cache[ev]

    for p in parsed:
        if not p.op.capability:
            continue
        payload, dec, reason, _sig_ok, _tid = verify_capability(
            p.op.capability, keys_for_event=keys_for, now=p.clock.corrected_at
        )
        if payload is not None:
            p.capability_verified = payload.tid == p.op.ticket_id and payload.eid == event_id
        elif dec in (domain.EXPIRED, domain.NOT_YET_VALID):
            p.capability_verified = True
            p.cap_override = (dec, reason)
        else:
            p.capability_verified = False

    # 3. Reference data for the whole batch: three queries, no N+1.
    tickets = repository.load_tickets(conn, sorted({p.op.ticket_id for p in parsed if p.op.ticket_id}))
    rules = repository.load_rules(conn, event_id, sorted({t.ticket_type_id for t in tickets.values()}))
    for p in parsed:
        p.ticket = tickets.get(p.op.ticket_id) if p.op.ticket_id else None
        if not p.op.ticket_id:
            p.elig = domain.Eligibility(
                False, domain.UNKNOWN, "no_ticket_id", conflict_type=domain.NOT_AUTHORIZED_SERVER_SIDE
            )
            continue
        p.elig = domain.check_eligibility(
            ticket=p.ticket,
            event_id=event_id,
            station=p.station,
            explicit_rules=rules.get(p.ticket.ticket_type_id, {}) if p.ticket else {},
            at=p.clock.corrected_at,
            capability_verified=p.capability_verified,
        )
        if p.cap_override and p.elig.eligible:
            p.elig = domain.Eligibility(
                False, p.cap_override[0], p.cap_override[1], conflict_type=domain.NOT_AUTHORIZED_SERVER_SIDE
            )
    conn.commit()  # end the read transaction: the next one is the real write transaction

    groups: dict[tuple[str, str], list[_Op]] = {}
    for p in parsed:
        if p.ticket is not None:
            groups.setdefault((p.ticket.ticket_id, p.station), []).append(p)

    try:
        with conn.transaction():
            repository.set_lock_timeout(conn, cfg.lock_timeout_ms)
            repository.lock_groups(conn, [repository.group_key(t, s) for t, s in groups])
            stored = repository.find_operations(conn, [p.op.operation_id for p in parsed])
            new_ops: list[_Op] = []
            replayed: dict[int, dict] = {}
            for p in parsed:
                st = stored.get(p.oid)
                if st is None:
                    new_ops.append(p)
                elif bytes(st["payload_hash"]) != p.hash:
                    results[p.idx] = _rejected(p.oid, "operation_id_reuse", "operation_id was already used for another scan")
                else:
                    replayed[p.idx] = st
            new_ids = {p.oid for p in new_ops}

            existing = repository.fetch_claims(conn, list(groups))
            decisions: dict[str, tuple[str, str, bool, str]] = {}  # oid -> decision, reason, is_claim, ack
            resolutions: dict[tuple[str, str], domain.Resolution] = {}
            claimants_of: dict[tuple[str, str], list[_Op]] = {}

            for gkey, gops in groups.items():
                new_in_group = [p for p in gops if p.oid in new_ids]
                if not new_in_group:
                    continue
                ticket = gops[0].ticket
                max_uses = domain.allowed_max_uses(gkey[1], rules.get(ticket.ticket_type_id, {}))
                claimants = [p for p in new_in_group if p.claims]
                claims = [Claim(p.oid, str(req.terminal_id), p.clock.corrected_at, p.clock.suspect) for p in claimants]
                res = domain.resolve(existing.get(gkey, []) + claims, max_uses)
                if claimants:
                    resolutions[gkey] = res
                    claimants_of[gkey] = claimants
                full = len(res.assigned) >= max_uses
                for p in new_in_group:
                    if p.claims:
                        took = res.use_index_of(p.oid) is not None
                        decisions[p.oid] = (
                            domain.VALID if took else domain.ALREADY_SCANNED,
                            "" if took else "already_scanned",
                            True,
                            "accepted" if took else "conflict",
                        )
                    elif p.elig.eligible:  # the terminal did not admit: audit evidence, not a claim
                        decisions[p.oid] = (domain.ALREADY_SCANNED if full else domain.VALID, "", False, "accepted")
                    else:
                        ack = "conflict" if p.reported == domain.VALID else "accepted"
                        decisions[p.oid] = (p.elig.decision, p.elig.reason, False, ack)
            for p in new_ops:
                if p.oid not in decisions:  # no ticket row (unknown id): nothing to rank
                    ack = "conflict" if p.reported == domain.VALID else "accepted"
                    decisions[p.oid] = (p.elig.decision, p.elig.reason, False, ack)

            rows = []
            for p in new_ops:
                decision, reason, is_claim, ack = decisions[p.oid]
                rows.append(
                    {
                        "operation_id": p.op.operation_id,
                        "scan_id": p.op.scan_id,
                        "payload_hash": p.hash,
                        "event_id": event_id,
                        "ticket_id": p.op.ticket_id,
                        "participant_ref": p.op.participant_id,
                        "terminal_id": req.terminal_id,
                        "staff_user_id": p.op.staff_id or principal.user_id,
                        "station": p.station,
                        "reported_decision": p.op.decision,  # verbatim: the server never trusts it
                        "reported_valid": p.reported == domain.VALID,
                        "server_decision": decision,
                        "server_reason": reason,
                        "capability_verified": p.capability_verified,
                        "is_claim": is_claim,
                        "ack_status": ack,
                        "device_evaluated_at": _aware(p.op.evaluated_at),
                        "device_sent_at": sent,
                        "server_received_at": received,
                        "clock_offset_ms": p.clock.offset_ms,
                        "corrected_evaluated_at": p.clock.corrected_at,
                        "clock_suspect": p.clock.suspect,
                        "clock_suspect_reason": p.clock.reason,
                        "app_version": req.app_version,
                        "qr_version": p.op.qr_version,
                        "connection_status": "offline_synced",
                        "batch_id": req.batch_id,
                    }
                )
            inserted = repository.insert_logs(conn, rows)
            for p in new_ops:
                if p.oid not in inserted:
                    if p.claims:  # cannot happen under the group lock: retry the whole (idempotent) batch
                        raise ApiError(503, "service_busy", "concurrent duplicate, retry", {"Retry-After": "1"})
                    replayed[p.idx] = repository.find_operations(conn, [p.op.operation_id])[p.oid]

            for gkey, res in resolutions.items():
                log_ids = {c.operation_id: c.log_id for c in existing.get(gkey, []) if c.log_id is not None}
                log_ids.update({p.oid: inserted[p.oid] for p in claimants_of[gkey]})
                apply_resolution(
                    conn, event_id=event_id, ticket_id=gkey[0], station=gkey[1], resolution=res, log_ids=log_ids
                )
            repository.upsert_conflicts(
                conn,
                [
                    (event_id, p.op.ticket_id, p.station, None, inserted[p.oid], p.elig.conflict_type, p.clock.suspect)
                    for p in new_ops
                    if p.reported == domain.VALID and not p.claims and p.elig.conflict_type and p.oid in inserted
                ],
            )
            repository.touch_batch(conn, req.terminal_id, offset_ms, received, req.pending_count)
            winner_logs = repository.log_ids_to_terminals(
                conn, [st["winning_log_id"] for st in replayed.values() if st["winning_log_id"]]
            )
    except psycopg.errors.LockNotAvailable as err:
        raise ApiError(503, "service_busy", "check-in is busy, retry", {"Retry-After": "1"}) from err

    # 4. Build the answer, in the order received.
    for idx, st in replayed.items():
        conflict = None
        if st["conflict_type"]:
            w = winner_logs.get(st["winning_log_id"]) if st["winning_log_id"] else None
            conflict = _conflict_view(
                st["conflict_type"],
                terminal=str(w["terminal_id"]) if w else None,
                at=w["corrected_evaluated_at"] if w else None,
            )
        results[idx] = {
            "operation_id": str(st["operation_id"]),
            "status": "already_processed",
            "server_decision": st["server_decision"],
            "conflict": conflict,
        }
    claim_index = {c.operation_id: c for res in resolutions.values() for c in res.ranking}
    spec_index = {s.losing_operation_id: s for res in resolutions.values() for s in res.conflicts}
    for p in new_ops:
        decision, _reason, _is_claim, ack = decisions[p.oid]
        conflict = None
        if p.claims:
            spec = spec_index.get(p.oid)
            if spec is not None:
                winner = claim_index.get(spec.winning_operation_id) if spec.winning_operation_id else None
                conflict = _conflict_view(spec.type, winner)
        elif p.reported == domain.VALID and p.elig.conflict_type:
            conflict = _conflict_view(p.elig.conflict_type)
        item = {
            "operation_id": p.oid,
            "status": "conflict" if ack == "conflict" else "accepted",
            "server_decision": decision,
            "conflict": conflict,
        }
        if p.clock.suspect:
            item["flags"] = ["clock_suspect"]
        results[p.idx] = item
    for idx, first in dup_of.items():
        src = results[first]
        results[idx] = dict(src) if src["status"] == "rejected" else {**src, "status": "already_processed"}

    summary = {"accepted": 0, "already_processed": 0, "conflict": 0, "rejected": 0}
    for r in results:
        summary[r["status"]] += 1
    return {
        "batch_id": str(req.batch_id),
        "received_at": _iso(received),
        "clock_offset_ms": offset_ms,
        "summary": summary,
        "results": results,
    }


# ── Conflicts and stats ─────────────────────────────────────────────────────


def conflict_view(r: dict) -> dict:
    """Public shape of a conflict row."""
    return {
        "conflict_id": r["conflict_id"],
        "type": r["type"],
        "station": r["station"],
        "ticket_id": r["ticket_id"],
        "serial": r["serial"] or "",
        "clock_suspect": r["clock_suspect"],
        "status": r["status"],
        "detected_at": _iso(r["detected_at"]),
        "note": r["note"],
        "resolved_by": r["resolved_by"],
        "resolved_at": _iso(r["resolved_at"]),
        "winning": (
            {"log_id": r["w_log_id"], "terminal_id": str(r["w_terminal"]), "corrected_evaluated_at": _iso(r["w_at"])}
            if r["w_log_id"]
            else None
        ),
        "losing": {
            "log_id": r["l_log_id"],
            "terminal_id": str(r["l_terminal"]),
            "corrected_evaluated_at": _iso(r["l_at"]),
        },
    }


def stats_view(event_id: str, now: datetime, raw: dict) -> dict:
    """Aggregate ``repository.stats`` rows into the public counters."""
    by_station: dict[str, dict[str, Any]] = {}
    for r in raw["decisions"]:
        by_station.setdefault(r["station"], {"consumed": 0, "decisions": {}})["decisions"][r["server_decision"]] = r["n"]
    for r in raw["consumed"]:
        by_station.setdefault(r["station"], {"consumed": 0, "decisions": {}})["consumed"] = r["n"]
    conflicts: dict[str, Any] = {"open": 0, "acknowledged": 0, "by_type": {}}
    for r in raw["conflicts"]:
        conflicts[r["status"]] += r["n"]
        conflicts["by_type"][r["type"]] = conflicts["by_type"].get(r["type"], 0) + r["n"]
    return {
        "event_id": event_id,
        "as_of": _iso(now),
        "by_station": by_station,
        "conflicts": conflicts,
        "terminals": [
            {
                "terminal_id": str(t["terminal_id"]),
                "label": t["label"],
                "last_seen_at": _iso(t["last_seen_at"]),
                "last_batch_at": _iso(t["last_batch_at"]),
                "clock_offset_ms": t["clock_offset_ms"],
                "pending_count": t["pending_count"],
                "revoked": t["revoked_at"] is not None,
            }
            for t in raw["terminals"]
        ],
    }
