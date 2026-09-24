"""Outbound and inbound sync operation log for replication."""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from store.store import Store
from store.timeutil import text_to_time, time_to_text


@dataclass
class SyncOp:
    """Syncop."""
    seq: int
    op_id: str
    event_id: str
    author: str
    delivered_by: str
    claim_ticket: str
    claim_device: str
    claim_scanned_at: datetime
    applied: bool
    cose: bytes
    created_at: datetime


@dataclass
class SyncOpStats:
    """Syncopstats."""
    ops: int = 0
    unapplied: int = 0
    highest_seq: int = 0
    pending: int = 0


def sync_ops_for_org_after(st: Store, org_id: str, after: int, limit: int) -> list[SyncOp]:
    """Sync ops for org after."""
    if limit <= 0:
        return []
    rows = st.fetchall(
        """
        SELECT o.seq, o.op_id, o.event_id, o.author, o.delivered_by,
               o.claim_ticket, o.claim_device, o.claim_scanned_at,
               o.applied, o.cose, o.created_at
        FROM sync_op o
        JOIN events e ON e.id = o.event_id
        WHERE e.org_id = ? AND o.seq > ?
        ORDER BY o.seq
        LIMIT ?
        """,
        (org_id, after, limit),
    )
    return [_row_op(r) for r in rows]


def append_sync_op(st: Store, op: SyncOp) -> bool:
    """Append sync op."""
    if not op.created_at:
        op.created_at = datetime.now(timezone.utc)
    n = st.execute_rowcount(
        """
        INSERT INTO sync_op (
            op_id, event_id, author, delivered_by, claim_ticket, claim_device,
            claim_scanned_at, applied, cose, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT DO NOTHING
        """,
        (
            op.op_id,
            op.event_id,
            op.author,
            op.delivered_by,
            op.claim_ticket,
            op.claim_device,
            op.claim_scanned_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            1 if op.applied else 0,
            op.cose,
            time_to_text(op.created_at),
        ),
    )
    return n > 0


def sync_op_stats_for_org(st: Store, org_id: str) -> SyncOpStats:
    """Sync op stats for org."""
    row = st.fetchone(
        """
        SELECT COUNT(*),
               COALESCE(SUM(CASE WHEN o.applied = 0 THEN 1 ELSE 0 END), 0),
               COALESCE(MAX(o.seq), 0)
        FROM sync_op o
        JOIN events e ON e.id = o.event_id
        WHERE e.org_id = ?
        """,
        (org_id,),
    )
    stats = SyncOpStats()
    if row is not None:
        if hasattr(row, "keys"):
            vals = list(row.values())
            stats.ops, stats.unapplied, stats.highest_seq = int(vals[0]), int(vals[1]), int(vals[2])
        else:
            stats.ops, stats.unapplied, stats.highest_seq = int(row[0]), int(row[1]), int(row[2])
    pend = st.fetchone(
        """
        SELECT COUNT(*)
        FROM admissions a
        JOIN events e ON e.id = a.event_id
        LEFT JOIN sync_op o
          ON o.event_id = a.event_id
         AND o.claim_ticket = a.ticket_id
         AND o.claim_device = a.device_id
         AND o.claim_scanned_at = a.scanned_at
        WHERE e.org_id = ? AND o.seq IS NULL
        """,
        (org_id,),
    )
    if pend is not None:
        stats.pending = int(list(pend.values())[0] if hasattr(pend, "keys") else pend[0])
    return stats


def op_id_from_cose(cose: bytes) -> str:
    """Op id from cose."""
    return hashlib.sha256(cose).hexdigest()


def decode_cose_b64(text: str) -> bytes:
    """Decode cose b64."""
    return base64.standard_b64decode(text)


def _row_op(row) -> SyncOp:
    """Internal: row op."""
    if hasattr(row, "keys"):
        scanned = row["claim_scanned_at"]
        if isinstance(scanned, str):
            if scanned.endswith("Z"):
                scanned = scanned[:-1] + "+00:00"
            scanned_at = datetime.fromisoformat(scanned).astimezone(timezone.utc)
        else:
            scanned_at = scanned
        return SyncOp(
            seq=int(row["seq"]),
            op_id=row["op_id"],
            event_id=row["event_id"],
            author=row["author"],
            delivered_by=row["delivered_by"] or "",
            claim_ticket=row["claim_ticket"],
            claim_device=row["claim_device"],
            claim_scanned_at=scanned_at,
            applied=bool(row["applied"]),
            cose=bytes(row["cose"]),
            created_at=text_to_time(row["created_at"]),
        )
    return SyncOp(
        seq=int(row[0]),
        op_id=row[1],
        event_id=row[2],
        author=row[3],
        delivered_by=row[4] or "",
        claim_ticket=row[5],
        claim_device=row[6],
        claim_scanned_at=text_to_time(row[7]),
        applied=bool(row[8]),
        cose=bytes(row[9]),
        created_at=text_to_time(row[10]),
    )
