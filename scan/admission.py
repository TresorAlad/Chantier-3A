"""Verify ticket capabilities and enforce one-scan admission rules (online API)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from scan.seenset import SeenSet
from store.store import Store
from tickets import capability as cap


class Status(str, Enum):
    """Outcome of a door scan against a ticket capability."""
    ADMITTED = "admitted"
    DUPLICATE = "duplicate"
    INVALID = "invalid"
    WRONG_EVENT = "wrong_event"


@dataclass
class Result:
    """Admission decision with optional decoded payload and human reason."""
    status: Status
    payload: cap.Payload | None = None
    reason: str = ""


def decide(
    token: str,
    ring: cap.KeyRing,
    event_id: str,
    seen: SeenSet,
    now: datetime,
    *,
    store: Store | None = None,
) -> Result:
    """Verify signature and expiry, then admit or flag duplicate scan."""
    payload, terminal, ok = _verify_for_event(token, ring, event_id, now)
    if not ok:
        return terminal
    if store is not None:
        blocked = _reject_if_ticket_not_valid(store, payload)
        if blocked is not None:
            return blocked
    return _admit_or_duplicate(payload, seen, now)


def _reject_if_ticket_not_valid(st: Store, payload: cap.Payload) -> Result | None:
    row = st.fetchone("SELECT status FROM tickets WHERE id = ?", (payload.tid,))
    if row is None:
        return Result(Status.INVALID, payload=payload, reason="ticket not issued for this event")
    status = row["status"] if hasattr(row, "keys") else row[0]
    if status != "valid":
        return Result(Status.INVALID, payload=payload, reason="ticket revoked or not valid")
    return None


def _verify_for_event(
    token: str, ring: cap.KeyRing, event_id: str, now: datetime
) -> tuple[cap.Payload | None, Result, bool]:
    """Internal: verify for event."""
    try:
        payload = cap.verify_with_ring(token, ring, now)
    except cap.CapabilityError as err:
        return None, Result(Status.INVALID, reason=str(err)), False
    if payload.eid != event_id:
        return (
            None,
            Result(Status.WRONG_EVENT, payload=payload, reason="capability is for a different event"),
            False,
        )
    return payload, Result(Status.INVALID), True


def _admit_or_duplicate(payload: cap.Payload, seen: SeenSet, now: datetime) -> Result:
    """Internal: admit or duplicate."""
    first, err = seen.mark_seen(payload.tid, now)
    if err is not None:
        return Result(
            Status.INVALID,
            payload=payload,
            reason=f"local dedupe check failed: {err}",
        )
    if not first:
        return Result(Status.DUPLICATE, payload=payload, reason="ticket already admitted")
    return Result(Status.ADMITTED, payload=payload, reason="ok")
