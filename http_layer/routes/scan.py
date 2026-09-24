"""Door scanner bundle download and admission verify routes."""

from __future__ import annotations

import base64
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import rbac
from events import issue as issue_mod
from http_layer.deps import AppState, require_user
from http_layer.errors import json_error
from scan import admission, bundle as bundle_mod
from store import admissions as admissions_repo, events_repo, tickets as tickets_repo
from store.store import NotFoundError

router = APIRouter(tags=["scan"])


class ScanBody(BaseModel):
    """Signed ticket capability and scan context from a door device."""
    event_id: str
    capability: str
    device_id: str = ""
    gate_id: str = ""
    scanned_at: str = ""


class _DbSeenSet:
    """Internal: DbSeenSet."""
    def __init__(self, st, event_id: str, gate_id: str, device_id: str, scanned_by: str) -> None:
        """Initialize ``_DbSeenSet``."""
        self._st = st
        self._event_id = event_id
        self._gate_id = gate_id
        self._device_id = device_id
        self._scanned_by = scanned_by

    def mark_seen(self, ticket_id: str, at: datetime) -> tuple[bool, Exception | None]:
        """Mark seen on ``_DbSeenSet``."""
        ok = admissions_repo.try_insert_admitted(
            self._st,
            ticket_id=ticket_id,
            event_id=self._event_id,
            gate_id=self._gate_id,
            device_id=self._device_id,
            scanned_by=self._scanned_by or None,
            scanned_at=at,
        )
        return ok, None

    def seen(self, ticket_id: str) -> bool:
        """Seen on ``_DbSeenSet``."""
        rows = self._st.fetchall(
            "SELECT 1 FROM admissions WHERE ticket_id = ? AND result = 'admitted' LIMIT 1",
            (ticket_id,),
        )
        return bool(rows)


@router.get("/events/{event_id}/scan-bundle")
def scan_bundle(event_id: str, state: AppState = Depends(require_user)):
    """Scan bundle."""
    if not rbac.can_manage_event(state.store, state.current_user.id, event_id, rbac.ROLE_SCANNER):
        return json_error(403, "forbidden", "you are not allowed to scan for this event")
    try:
        ev = events_repo.get_event_by_id(state.store, event_id)
    except NotFoundError:
        return json_error(404, "not_found", "event not found")
    ring = issue_mod.issuer_public_keys(state.store, event_id)
    ticket_index = tickets_repo.list_valid_ticket_ids_for_event(state.store, event_id)
    admitted = admissions_repo.list_admitted_ticket_ids(state.store, event_id)
    b = bundle_mod.Bundle(
        event=bundle_mod.EventMeta(
            event_id=ev.id,
            title=ev.title,
            venue_name=ev.venue_name,
            starts_at=ev.starts_at,
            ends_at=ev.ends_at,
        ),
        issuer_keys=ring,
        ticket_index=ticket_index,
        ticket_index_present=True,
        admitted_index=admitted,
        issued_at=datetime.now(timezone.utc),
    )
    try:
        b.validate()
    except ValueError as err:
        return json_error(500, "internal_error", str(err))
    return {
        "bundle": {
            "event": {
                "event_id": b.event.event_id,
                "title": b.event.title,
                "venue_name": b.event.venue_name,
                "starts_at": b.event.starts_at.isoformat().replace("+00:00", "Z"),
                "ends_at": b.event.ends_at.isoformat().replace("+00:00", "Z"),
            },
            "issuer_keys": {
                "event_id": ring.event_id,
                "keys": {
                    kid: base64.urlsafe_b64encode(pub).decode().rstrip("=")
                    for kid, pub in ring.keys.items()
                },
            },
            "ticket_index": b.ticket_index,
            "ticket_index_present": b.ticket_index_present,
            "admitted_index": b.admitted_index,
            "issued_at": b.issued_at.isoformat().replace("+00:00", "Z") if b.issued_at else None,
        }
    }


@router.post("/scan")
def scan_ticket(body: ScanBody, state: AppState = Depends(require_user)):
    """Scan ticket."""
    if not body.event_id or not body.capability:
        return json_error(400, "invalid_request", "event_id and capability are required")
    if not rbac.can_manage_event(state.store, state.current_user.id, body.event_id, rbac.ROLE_SCANNER):
        return json_error(403, "forbidden", "you are not allowed to scan for this event")
    now = datetime.now(timezone.utc)
    if body.scanned_at:
        try:
            raw = body.scanned_at
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            now = datetime.fromisoformat(raw).astimezone(timezone.utc)
        except ValueError:
            return json_error(400, "invalid_request", "scanned_at must be RFC3339")
    ring = issue_mod.issuer_public_keys(state.store, body.event_id)
    seen = _DbSeenSet(
        state.store,
        body.event_id,
        body.gate_id,
        body.device_id,
        state.current_user.id,
    )
    result = admission.decide(body.capability, ring, body.event_id, seen, now)
    return {"result": result.status.value, "reason": result.reason, "ticket_id": result.payload.tid if result.payload else ""}


@router.post("/scan/sync")
def scan_sync(body: dict, state: AppState = Depends(require_user)):
    """Scan sync."""
    batch = body.get("admissions") or body.get("batch") or []
    applied: list[bool] = []
    for item in batch:
        event_id = item.get("event_id", "")
        if event_id and not rbac.can_manage_event(
            state.store, state.current_user.id, event_id, rbac.ROLE_SCANNER
        ):
            return json_error(403, "forbidden", "not allowed for one of the events")
    for item in batch:
        ticket_id = item.get("ticket_id", "")
        if not ticket_id:
            applied.append(True)
            continue
        at_raw = item.get("scanned_at") or datetime.now(timezone.utc).isoformat()
        if at_raw.endswith("Z"):
            at_raw = at_raw[:-1] + "+00:00"
        at = datetime.fromisoformat(at_raw).astimezone(timezone.utc)
        result = item.get("result", "admitted")
        if result == "admitted":
            ok = admissions_repo.try_insert_admitted(
                state.store,
                ticket_id=ticket_id,
                event_id=item.get("event_id", ""),
                gate_id=item.get("gate_id", ""),
                device_id=item.get("device_id", ""),
                scanned_by=state.current_user.id,
                scanned_at=at,
            )
            applied.append(ok)
        else:
            applied.append(True)
    return {"applied": applied}


@router.get("/events/{event_id}/attendees")
def list_attendees(event_id: str, state: AppState = Depends(require_user)):
    """List attendees."""
    if not rbac.can_manage_event(state.store, state.current_user.id, event_id, rbac.ROLE_SCANNER):
        return json_error(403, "forbidden", "forbidden")
    rows = state.store.fetchall(
        """
        SELECT t.id, t.order_id, t.serial, t.holder_name, t.status, t.ticket_type_id,
               tt.name AS ticket_type_name
        FROM tickets t
        JOIN ticket_types tt ON tt.id = t.ticket_type_id
        WHERE t.event_id = ?
        ORDER BY t.issued_at ASC, t.id ASC
        """,
        (event_id,),
    )
    attendees = []
    for row in rows:
        if hasattr(row, "keys"):
            attendees.append(
                {
                    "ticket_id": row["id"],
                    "order_id": row["order_id"],
                    "serial": row["serial"],
                    "holder_name": row["holder_name"],
                    "status": row["status"],
                    "ticket_type_id": row["ticket_type_id"],
                    "ticket_type_name": row["ticket_type_name"],
                }
            )
    return {"attendees": attendees}
