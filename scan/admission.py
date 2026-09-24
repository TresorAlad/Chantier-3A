"""Verify ticket capabilities and enforce one-scan admission rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from scan import bundle as bundle_mod
from scan.seenset import SeenSet
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
) -> Result:
    """Verify signature and expiry, then admit or flag duplicate scan."""
    payload, terminal, ok = _verify_for_event(token, ring, event_id, now)
    if not ok:
        return terminal
    return _admit_or_duplicate(payload, seen, now)


def decide_with_bundle(token: str, b: bundle_mod.Bundle, seen: SeenSet, now: datetime) -> Result:
    """Offline admission using a downloaded bundle (keys, index, seen hints)."""
    payload, terminal, ok = _verify_for_event(token, b.issuer_keys, b.event.event_id, now)
    if not ok:
        return terminal
    if b.ticket_index_present and payload.tid not in b.ticket_index:
        return Result(Status.INVALID, reason="ticket revoked or not issued for this event")
    if payload.tid in b.admitted_index:
        seen.mark_seen(payload.tid, now)
        return Result(
            Status.DUPLICATE,
            payload=payload,
            reason="ticket already admitted at another gate",
        )
    return _admit_or_duplicate(payload, seen, now)


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
