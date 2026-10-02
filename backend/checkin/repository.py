"""SQL of the check-in module. Every function takes a psycopg connection (dict rows).

Writes never go through the 3A ``Store`` (it commits on every call); only read-only 3A helpers
are reused, on a pooled connection wrapped in ``Store`` (see ``checkin.adapters``).
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Any, Iterable, Sequence
from uuid import UUID

import psycopg

from checkin.domain import Claim, TicketFacts
from store.timeutil import text_to_null_time

# ── Terminals ───────────────────────────────────────────────────────────────


def register_terminal(
    conn: psycopg.Connection,
    terminal_id: UUID,
    event_id: str,
    user_id: str | None,
    refresh_after_seconds: int = 30,
) -> dict:
    """Register a terminal on first call; refresh ``last_seen_at`` at most every ``refresh_after_seconds``.

    The steady state is a single indexed SELECT (no write, hence no WAL flush per scan).
    """
    row = conn.execute(
        """
        SELECT terminal_id, event_id, revoked_at,
               (now() - last_seen_at) < make_interval(secs => %s) AS fresh
        FROM checkin_terminals WHERE terminal_id = %s
        """,
        (refresh_after_seconds, terminal_id),
    ).fetchone()
    if row is not None and row["fresh"]:
        return row
    return conn.execute(
        """
        INSERT INTO checkin_terminals (terminal_id, event_id, registered_by)
        VALUES (%s, %s, %s)
        ON CONFLICT (terminal_id) DO UPDATE SET last_seen_at = now()
        RETURNING terminal_id, event_id, revoked_at
        """,
        (terminal_id, event_id, user_id),
    ).fetchone()


def touch_batch(
    conn: psycopg.Connection,
    terminal_id: UUID,
    offset_ms: int | None,
    at: datetime,
    pending_count: int | None = None,
) -> None:
    """Record last batch time, raw clock offset and reported outbox size (diagnostic only)."""
    conn.execute(
        """
        UPDATE checkin_terminals
        SET last_batch_at = %s, clock_offset_ms = %s, pending_count = COALESCE(%s, pending_count)
        WHERE terminal_id = %s
        """,
        (at, offset_ms, pending_count, terminal_id),
    )


# ── Reference data (batched reads) ──────────────────────────────────────────


def event_exists(conn: psycopg.Connection, event_id: str) -> bool:
    """Whether the 3A event exists."""
    return conn.execute("SELECT 1 FROM events WHERE id = %s", (event_id,)).fetchone() is not None


def load_tickets(conn: psycopg.Connection, ticket_ids: Sequence[str]) -> dict[str, TicketFacts]:
    """Load every ticket referenced by a batch in one query."""
    if not ticket_ids:
        return {}
    rows = conn.execute(
        """
        SELECT id, event_id, ticket_type_id, status, serial, voided_at
        FROM tickets WHERE id = ANY(%s)
        """,
        (list(ticket_ids),),
    ).fetchall()
    return {
        r["id"]: TicketFacts(
            ticket_id=r["id"],
            event_id=r["event_id"],
            ticket_type_id=r["ticket_type_id"],
            status=r["status"],
            serial=r["serial"] or "",
            voided_at=text_to_null_time(r["voided_at"]),
        )
        for r in rows
    }


def load_rules(conn: psycopg.Connection, event_id: str, type_ids: Sequence[str]) -> dict[str, dict[str, int]]:
    """Effective station rules per ticket type: ``{type_id: {station: max_uses}}``.

    Base: the organizer's flags on the ticket type (``access_event`` ... ``access_after``, one use each).
    An explicit ``checkin_station_rules`` row overrides the flag of its station (and can set several uses).
    """
    if not type_ids:
        return {}
    flags = conn.execute(
        "SELECT id, access_event, access_food, access_merch, access_after FROM ticket_types WHERE id = ANY(%s)",
        (list(type_ids),),
    ).fetchall()
    out: dict[str, dict[str, int]] = {
        r["id"]: {
            "EVENT_ENTRY": int(r["access_event"]),
            "FOOD_ACCESS": int(r["access_food"]),
            "MERCH_PICKUP": int(r["access_merch"]),
            "AFTER_ENTRY": int(r["access_after"]),
        }
        for r in flags
    }
    rows = conn.execute(
        """
        SELECT ticket_type_id, station, max_uses
        FROM checkin_station_rules
        WHERE event_id = %s AND ticket_type_id = ANY(%s)
        """,
        (event_id, list(type_ids)),
    ).fetchall()
    for r in rows:
        out.setdefault(r["ticket_type_id"], {})[r["station"]] = r["max_uses"]
    return out


# ── Locks, claims, journal ──────────────────────────────────────────────────


def group_key(ticket_id: str, station: str) -> str:
    """Advisory-lock key of one (ticket, station) group."""
    return f"{ticket_id}:{station}"


def set_lock_timeout(conn: psycopg.Connection, milliseconds: int) -> None:
    """``SET LOCAL lock_timeout`` for the current transaction."""
    conn.execute("SELECT set_config('lock_timeout', %s, true)", (f"{int(milliseconds)}ms",))


def lock_groups(conn: psycopg.Connection, keys: Iterable[str]) -> None:
    """Take transaction-scoped advisory locks, always in sorted key order (no deadlocks)."""
    ordered = sorted(set(keys))
    if not ordered:
        return
    conn.execute(
        """
        SELECT pg_advisory_xact_lock(hashtextextended(k, 0))
        FROM (SELECT k FROM unnest(%s::text[]) AS k ORDER BY k) AS s
        """,
        (ordered,),
    )


def fetch_claims(conn: psycopg.Connection, pairs: Sequence[tuple[str, str]]) -> dict[tuple[str, str], list[Claim]]:
    """Existing claimants of every (ticket, station) pair of a batch, in one query."""
    if not pairs:
        return {}
    rows = conn.execute(
        """
        SELECT log_id, operation_id, terminal_id, corrected_evaluated_at, clock_suspect, ticket_id, station
        FROM scan_logs
        WHERE is_claim AND (ticket_id, station) IN (
            SELECT t, s FROM unnest(%s::text[], %s::text[]) AS u(t, s))
        """,
        ([p[0] for p in pairs], [p[1] for p in pairs]),
    ).fetchall()
    out: dict[tuple[str, str], list[Claim]] = {}
    for r in rows:
        out.setdefault((r["ticket_id"], r["station"]), []).append(
            Claim(
                operation_id=str(r["operation_id"]),
                terminal_id=str(r["terminal_id"]),
                corrected_at=r["corrected_evaluated_at"],
                suspect=r["clock_suspect"],
                log_id=r["log_id"],
            )
        )
    return out


def find_operations(conn: psycopg.Connection, operation_ids: Sequence[UUID]) -> dict[str, dict]:
    """Already-journaled operations (idempotent replays), keyed by ``operation_id``."""
    if not operation_ids:
        return {}
    rows = conn.execute(
        """
        SELECT l.operation_id, l.log_id, l.payload_hash, l.server_decision, l.server_reason, l.ack_status,
               l.ticket_id, l.station, l.is_claim, c.type AS conflict_type, c.winning_log_id
        FROM scan_logs l LEFT JOIN scan_conflicts c ON c.losing_log_id = l.log_id
        WHERE l.operation_id = ANY(%s)
        """,
        (list(operation_ids),),
    ).fetchall()
    return {str(r["operation_id"]): r for r in rows}


_LOG_COLUMNS: list[tuple[str, str]] = [
    ("operation_id", "uuid"),
    ("scan_id", "uuid"),
    ("payload_hash", "bytea"),
    ("event_id", "text"),
    ("ticket_id", "text"),
    ("participant_ref", "text"),
    ("terminal_id", "uuid"),
    ("staff_user_id", "text"),
    ("station", "text"),
    ("reported_decision", "text"),
    ("reported_valid", "boolean"),
    ("server_decision", "text"),
    ("server_reason", "text"),
    ("capability_verified", "boolean"),
    ("is_claim", "boolean"),
    ("ack_status", "text"),
    ("device_evaluated_at", "timestamptz"),
    ("device_sent_at", "timestamptz"),
    ("server_received_at", "timestamptz"),
    ("clock_offset_ms", "bigint"),
    ("corrected_evaluated_at", "timestamptz"),
    ("clock_suspect", "boolean"),
    ("clock_suspect_reason", "text"),
    ("app_version", "text"),
    ("qr_version", "integer"),
    ("connection_status", "text"),
    ("batch_id", "uuid"),
]

_INSERT_LOGS_SQL = (
    "INSERT INTO scan_logs ("
    + ", ".join(c for c, _ in _LOG_COLUMNS)
    + ") SELECT * FROM unnest("
    + ", ".join(f"%s::{t}[]" for _, t in _LOG_COLUMNS)
    + ") ON CONFLICT (operation_id) DO NOTHING RETURNING operation_id, log_id"
)


def insert_logs(conn: psycopg.Connection, rows: Sequence[dict[str, Any]]) -> dict[str, int]:
    """Bulk-insert journal rows; already-known ``operation_id`` are skipped (no try/except).

    Returns ``{operation_id: log_id}`` for the rows that were actually inserted.
    """
    if not rows:
        return {}
    params = tuple([r.get(col) for r in rows] for col, _ in _LOG_COLUMNS)
    out = conn.execute(_INSERT_LOGS_SQL, params).fetchall()
    return {str(r["operation_id"]): r["log_id"] for r in out}


def upsert_consumptions(
    conn: psycopg.Connection,
    rows: Sequence[tuple[str, str, int, str, int, datetime]],
) -> None:
    """Upsert ``(ticket_id, station, use_index, event_id, winning_log_id, consumed_at)`` rows."""
    if not rows:
        return
    cols = list(zip(*rows))
    conn.execute(
        """
        INSERT INTO station_consumptions (ticket_id, station, use_index, event_id, winning_log_id, consumed_at)
        SELECT * FROM unnest(%s::text[], %s::text[], %s::int[], %s::text[], %s::bigint[], %s::timestamptz[])
        ON CONFLICT (ticket_id, station, use_index) DO UPDATE
            SET winning_log_id = EXCLUDED.winning_log_id,
                consumed_at = EXCLUDED.consumed_at,
                updated_at = now()
            WHERE station_consumptions.winning_log_id IS DISTINCT FROM EXCLUDED.winning_log_id
        """,
        tuple(list(c) for c in cols),
    )


def upsert_conflicts(
    conn: psycopg.Connection,
    rows: Sequence[tuple[str, str | None, str, int | None, int, str, bool]],
) -> None:
    """Upsert ``(event_id, ticket_id, station, winning_log_id, losing_log_id, type, clock_suspect)``.

    Status, note and ``detected_at`` of an existing conflict are preserved.
    """
    if not rows:
        return
    cols = list(zip(*rows))
    conn.execute(
        """
        INSERT INTO scan_conflicts (event_id, ticket_id, station, winning_log_id, losing_log_id, type, clock_suspect)
        SELECT * FROM unnest(%s::text[], %s::text[], %s::text[], %s::bigint[], %s::bigint[], %s::text[], %s::boolean[])
        ON CONFLICT (losing_log_id) DO UPDATE
            SET winning_log_id = EXCLUDED.winning_log_id,
                type = EXCLUDED.type,
                clock_suspect = EXCLUDED.clock_suspect
            WHERE (scan_conflicts.winning_log_id, scan_conflicts.type, scan_conflicts.clock_suspect)
                  IS DISTINCT FROM (EXCLUDED.winning_log_id, EXCLUDED.type, EXCLUDED.clock_suspect)
        """,
        tuple(list(c) for c in cols),
    )


def log_ids_to_terminals(conn: psycopg.Connection, log_ids: Sequence[int]) -> dict[int, dict]:
    """Terminal and corrected time of the given logs (to describe a winner in a response)."""
    if not log_ids:
        return {}
    rows = conn.execute(
        "SELECT log_id, terminal_id, corrected_evaluated_at FROM scan_logs WHERE log_id = ANY(%s)",
        (list(log_ids),),
    ).fetchall()
    return {r["log_id"]: r for r in rows}


# ── Audit log listing ───────────────────────────────────────────────────────

LOG_SELECT = """
    SELECT log_id, operation_id, scan_id, event_id, ticket_id, participant_ref, terminal_id, staff_user_id,
           station, reported_decision, server_decision, server_reason, capability_verified, is_claim, ack_status,
           device_evaluated_at, device_sent_at, server_received_at, clock_offset_ms, corrected_evaluated_at,
           clock_suspect, clock_suspect_reason, app_version, qr_version, connection_status, batch_id
    FROM scan_logs
"""


def list_logs(
    conn: psycopg.Connection,
    *,
    event_id: str,
    station: str | None,
    ticket_id: str | None,
    terminal_id: UUID | None,
    since: datetime | None,
    cursor: int | None,
    limit: int,
) -> list[dict]:
    """Keyset-paginated audit listing (``log_id`` ascending)."""
    where = ["event_id = %s"]
    args: list[Any] = [event_id]
    if station:
        where.append("station = %s")
        args.append(station)
    if ticket_id:
        where.append("ticket_id = %s")
        args.append(ticket_id)
    if terminal_id:
        where.append("terminal_id = %s")
        args.append(terminal_id)
    if since:
        where.append("server_received_at >= %s")
        args.append(since)
    if cursor is not None:
        where.append("log_id > %s")
        args.append(cursor)
    args.append(limit)
    return conn.execute(
        f"{LOG_SELECT} WHERE {' AND '.join(where)} ORDER BY log_id ASC LIMIT %s", args
    ).fetchall()


# ── Snapshot ────────────────────────────────────────────────────────────────

_REFRESH_SQL = """
    WITH types AS (  -- allowed stations are computed once per ticket TYPE, not once per ticket
        SELECT tt.id AS ticket_type_id,
               ARRAY(SELECT x.s FROM (
                         SELECT r.station AS s FROM checkin_station_rules r
                         WHERE r.event_id = %(event)s AND r.ticket_type_id = tt.id AND r.max_uses > 0
                         UNION
                         SELECT f.s FROM (VALUES ('EVENT_ENTRY', tt.access_event), ('FOOD_ACCESS', tt.access_food),
                                                 ('MERCH_PICKUP', tt.access_merch), ('AFTER_ENTRY', tt.access_after))
                                         AS f(s, ok)
                         WHERE f.ok AND NOT EXISTS (
                             SELECT 1 FROM checkin_station_rules r
                             WHERE r.event_id = %(event)s AND r.ticket_type_id = tt.id AND r.station = f.s)
                     ) x ORDER BY x.s) AS stations,
               COALESCE(NULLIF(tt.pass_tier, ''), tt.name) AS pass_type
        FROM ticket_types tt WHERE tt.event_id = %(event)s
    ), uses AS (     -- one pass over the consumptions of the event
        SELECT u.ticket_id, jsonb_object_agg(u.station, u.cnt) AS uses
        FROM (SELECT c.ticket_id, c.station, count(*) AS cnt FROM station_consumptions c
              WHERE c.event_id = %(event)s GROUP BY c.ticket_id, c.station) u
        GROUP BY u.ticket_id
    ), computed AS (
        SELECT t.event_id, t.id AS ticket_id, t.serial, t.ticket_type_id, t.status,
               COALESCE(t.holder_name, '') AS holder_name, COALESCE(ty.pass_type, '') AS pass_type,
               CASE WHEN t.status = 'valid' THEN COALESCE(ty.stations, ARRAY['EVENT_ENTRY']::text[])
                    ELSE ARRAY[]::text[] END AS stations,
               COALESCE(u.uses, '{}'::jsonb) AS uses
        FROM tickets t
        LEFT JOIN types ty ON ty.ticket_type_id = t.ticket_type_id
        LEFT JOIN uses u ON u.ticket_id = t.id
        WHERE t.event_id = %(event)s
    ), hashed AS (
        SELECT c.*, md5(concat_ws('|', c.serial, c.ticket_type_id, c.status,
                                  array_to_string(c.stations, ','), c.uses::text, c.holder_name, c.pass_type)) AS content_hash
        FROM computed c
    )
    INSERT INTO checkin_entitlements (event_id, ticket_id, serial, ticket_type_id, status, stations, uses,
                                      holder_name, pass_type, content_hash, version)
    SELECT h.event_id, h.ticket_id, h.serial, h.ticket_type_id, h.status, h.stations, h.uses,
           h.holder_name, h.pass_type, h.content_hash, nextval('checkin_version_seq')
    FROM hashed h
    ON CONFLICT (event_id, ticket_id) DO UPDATE
        SET serial = EXCLUDED.serial, ticket_type_id = EXCLUDED.ticket_type_id, status = EXCLUDED.status,
            stations = EXCLUDED.stations, uses = EXCLUDED.uses, holder_name = EXCLUDED.holder_name,
            pass_type = EXCLUDED.pass_type, content_hash = EXCLUDED.content_hash,
            version = EXCLUDED.version
        WHERE checkin_entitlements.content_hash IS DISTINCT FROM EXCLUDED.content_hash
"""


def refresh_entitlements_if_stale(conn: psycopg.Connection, event_id: str, ttl_seconds: int) -> dict:
    """Recompute the entitlement cache when older than ``ttl_seconds``; return the meta row.

    Only one process refreshes at a time (``pg_try_advisory_xact_lock``); the others serve the
    previous version. Only rows whose content changed get a new ``version``.
    """
    meta = conn.execute(
        "SELECT refreshed_at, max_version, (now() - refreshed_at) > make_interval(secs => %s) AS stale "
        "FROM checkin_snapshot_meta WHERE event_id = %s",
        (ttl_seconds, event_id),
    ).fetchone()
    if meta is not None and not meta["stale"]:
        return meta
    with conn.transaction():
        got = conn.execute(
            "SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0)) AS ok", (f"checkin_snapshot:{event_id}",)
        ).fetchone()["ok"]
        if got:
            conn.execute(_REFRESH_SQL, {"event": event_id})
            conn.execute(
                """
                DELETE FROM checkin_entitlements e
                WHERE e.event_id = %s AND NOT EXISTS (SELECT 1 FROM tickets t WHERE t.id = e.ticket_id)
                """,
                (event_id,),
            )
            conn.execute(
                """
                INSERT INTO checkin_snapshot_meta (event_id, refreshed_at, max_version)
                VALUES (%s, now(), COALESCE((SELECT max(version) FROM checkin_entitlements WHERE event_id = %s), 0))
                ON CONFLICT (event_id) DO UPDATE
                    SET refreshed_at = now(), max_version = EXCLUDED.max_version
                """,
                (event_id, event_id),
            )
    return conn.execute(
        "SELECT refreshed_at, max_version FROM checkin_snapshot_meta WHERE event_id = %s", (event_id,)
    ).fetchone() or {"refreshed_at": None, "max_version": 0}


def encode_cursor(pin: int, version: int, ticket_id: str) -> str:
    """Opaque snapshot cursor pinned on the version of page 1."""
    raw = json.dumps([pin, version, ticket_id], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[int, int, str]:
    """Inverse of :func:`encode_cursor`; raises ``ValueError`` on garbage."""
    raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
    pin, version, ticket_id = json.loads(raw)
    if not (isinstance(pin, int) and isinstance(version, int) and isinstance(ticket_id, str)):
        raise ValueError("bad cursor")
    return pin, version, ticket_id


def snapshot_page(
    conn: psycopg.Connection,
    event_id: str,
    *,
    since: int,
    pin: int,
    after: tuple[int, str] | None,
    limit: int,
) -> list[dict]:
    """One page of entitlements with ``since < version <= pin`` ordered by ``(version, ticket_id)``."""
    args: list[Any] = [event_id, since, pin]
    cond = ""
    if after is not None:
        cond = "AND (version, ticket_id) > (%s, %s)"
        args += [after[0], after[1]]
    args.append(limit)
    return conn.execute(
        f"""
        SELECT ticket_id, serial, ticket_type_id, status, stations, uses, holder_name, pass_type, version
        FROM checkin_entitlements
        WHERE event_id = %s AND version > %s AND version <= %s {cond}
        ORDER BY version, ticket_id LIMIT %s
        """,
        args,
    ).fetchall()


# ── Conflicts and stats ─────────────────────────────────────────────────────


def conflict_event(conn: psycopg.Connection, conflict_id: int) -> str | None:
    """Event owning a conflict (to authorise an acknowledgement), or ``None``."""
    row = conn.execute("SELECT event_id FROM scan_conflicts WHERE conflict_id = %s", (conflict_id,)).fetchone()
    return row["event_id"] if row else None


_CONFLICT_SELECT = """
    SELECT c.conflict_id, c.type, c.station, c.ticket_id, c.clock_suspect, c.status, c.detected_at, c.note,
           c.resolved_by, c.resolved_at, t.serial,
           w.log_id AS w_log_id, w.terminal_id AS w_terminal, w.corrected_evaluated_at AS w_at,
           l.log_id AS l_log_id, l.terminal_id AS l_terminal, l.corrected_evaluated_at AS l_at
    FROM scan_conflicts c
    JOIN scan_logs l ON l.log_id = c.losing_log_id
    LEFT JOIN scan_logs w ON w.log_id = c.winning_log_id
    LEFT JOIN tickets t ON t.id = c.ticket_id
"""


def list_conflicts(
    conn: psycopg.Connection,
    *,
    event_id: str,
    status: str | None,
    ctype: str | None,
    cursor: int | None,
    limit: int,
) -> list[dict]:
    """Conflicts newest first, keyset-paginated on ``conflict_id``."""
    where = ["c.event_id = %s"]
    args: list[Any] = [event_id]
    if status:
        where.append("c.status = %s")
        args.append(status)
    if ctype:
        where.append("c.type = %s")
        args.append(ctype)
    if cursor is not None:
        where.append("c.conflict_id < %s")
        args.append(cursor)
    args.append(limit)
    return conn.execute(
        f"{_CONFLICT_SELECT} WHERE {' AND '.join(where)} ORDER BY c.conflict_id DESC LIMIT %s", args
    ).fetchall()


def acknowledge_conflict(conn: psycopg.Connection, conflict_id: int, user_id: str, note: str) -> dict | None:
    """Idempotent acknowledgement: the first resolver and note are kept on repeated calls."""
    conn.execute(
        """
        UPDATE scan_conflicts
        SET note = CASE WHEN status = 'open' THEN %s ELSE note END,
            resolved_by = COALESCE(resolved_by, %s),
            resolved_at = COALESCE(resolved_at, now()),
            status = 'acknowledged'
        WHERE conflict_id = %s
        """,
        (note, user_id, conflict_id),
    )
    return conn.execute(f"{_CONFLICT_SELECT} WHERE c.conflict_id = %s", (conflict_id,)).fetchone()


def stats(conn: psycopg.Connection, event_id: str) -> dict:
    """Counters per station, conflicts and terminals of an event (no personal data)."""
    decisions = conn.execute(
        "SELECT station, server_decision, count(*) AS n FROM scan_logs WHERE event_id = %s GROUP BY 1, 2",
        (event_id,),
    ).fetchall()
    consumed = conn.execute(
        "SELECT station, count(*) AS n FROM station_consumptions WHERE event_id = %s GROUP BY 1", (event_id,)
    ).fetchall()
    conflicts = conn.execute(
        "SELECT status, type, count(*) AS n FROM scan_conflicts WHERE event_id = %s GROUP BY 1, 2", (event_id,)
    ).fetchall()
    terminals = conn.execute(
        """
        SELECT terminal_id, label, last_seen_at, last_batch_at, clock_offset_ms, pending_count, revoked_at
        FROM checkin_terminals WHERE event_id = %s ORDER BY last_seen_at DESC
        """,
        (event_id,),
    ).fetchall()
    return {"decisions": decisions, "consumed": consumed, "conflicts": conflicts, "terminals": terminals}


def participant(conn: psycopg.Connection, ticket_id: str) -> dict:
    """Minimal participant data of a ticket for the scanner screen (name and pass type only)."""
    row = conn.execute(
        """
        SELECT COALESCE(t.holder_name, '') AS holder_name, COALESCE(NULLIF(tt.pass_tier, ''), tt.name) AS pass_type
        FROM tickets t JOIN ticket_types tt ON tt.id = t.ticket_type_id WHERE t.id = %s
        """,
        (ticket_id,),
    ).fetchone()
    return {"holder_name": row["holder_name"], "pass_type": row["pass_type"]} if row else {}


def accessible_events(conn: psycopg.Connection, user_id: str) -> list[dict]:
    """Published events of the organisations where the user is at least ``scanner``."""
    rows = conn.execute(
        """
        SELECT e.id AS event_id, e.title, e.slug, e.starts_at, e.ends_at, e.timezone, m.role
        FROM org_members m JOIN events e ON e.org_id = m.org_id
        WHERE m.user_id = %s AND e.status = 'published' AND m.role IN ('scanner', 'admin', 'owner')
        ORDER BY e.starts_at, e.id
        """,
        (user_id,),
    ).fetchall()
    return rows
