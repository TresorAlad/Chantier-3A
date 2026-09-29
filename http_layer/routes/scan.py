"""Door scanner admission routes (online only)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import rbac
from events import issue as issue_mod
from http_layer.deps import AppState, require_user
from http_layer.errors import json_error
from scan import admission
from store import admissions as admissions_repo
from tickets import capability as cap

router = APIRouter(tags=["scan"])


class ScanBody(BaseModel):
    """Signed ticket capability and scan context from a door device."""
    event_id: str
    capability: str
    device_id: str = ""
    gate_id: str = ""
    scanned_at: str = ""


class _DbSeenSet:
    """Persists first admission per ticket in the database."""

    def __init__(self, st, event_id: str, gate_id: str, device_id: str, scanned_by: str) -> None:
        self._st = st
        self._event_id = event_id
        self._gate_id = gate_id
        self._device_id = device_id
        self._scanned_by = scanned_by

    def mark_seen(self, ticket_id: str, at: datetime) -> tuple[bool, Exception | None]:
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
        rows = self._st.fetchall(
            "SELECT 1 FROM admissions WHERE ticket_id = ? AND result = 'admitted' LIMIT 1",
            (ticket_id,),
        )
        return bool(rows)


@router.post("/scan")
def scan_ticket(body: ScanBody, state: AppState = Depends(require_user)):
    """Verify a capability and record admission (requires live API access)."""
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
    try:
        cap_eid = cap.peek_eid(body.capability)
    except cap.CapabilityError as err:
        return {
            "result": admission.Status.INVALID.value,
            "reason": str(err),
            "ticket_id": "",
        }
    ring = issue_mod.issuer_public_keys(state.store, cap_eid or body.event_id)
    seen = _DbSeenSet(
        state.store,
        body.event_id,
        body.gate_id,
        body.device_id,
        state.current_user.id,
    )
    result = admission.decide(
        body.capability, ring, body.event_id, seen, now, store=state.store
    )
    return {"result": result.status.value, "reason": result.reason, "ticket_id": result.payload.tid if result.payload else ""}


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
