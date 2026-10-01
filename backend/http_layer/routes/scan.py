"""Online and offline-reconciled ticket admission routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from auth import rbac
from events import issue as issue_mod
from events import service as events_svc
from http_layer.deps import AppState, require_user
from http_layer.errors import json_error
from scan import admission
from store import admissions as admissions_repo
from store import ticket_types as ticket_types_repo
from tickets import capability as cap

router = APIRouter(tags=["scan"])
ControlType = Literal["event_entry", "food_access", "merch_pickup", "after_entry"]


class ScanBody(BaseModel):
    """Signed ticket capability and scan context from a door device."""
    event_id: str
    capability: str
    device_id: str = ""
    gate_id: str = ""
    scanned_at: str = ""
    control_type: ControlType = "event_entry"


class SyncScanItem(BaseModel):
    """One durable operation produced by the mobile offline outbox."""
    operation_id: str
    capability: str
    device_id: str
    gate_id: str = ""
    scanned_at: str
    reported_result: Literal["admitted", "duplicate"] = "admitted"
    control_type: ControlType = "event_entry"


class SyncScanBody(BaseModel):
    """Bounded, idempotent batch of offline scan operations."""
    event_id: str
    operations: list[SyncScanItem] = Field(default_factory=list, max_length=500)


class _DbSeenSet:
    """Persists first admission per ticket and control type."""
    def __init__(self, st, event_id, gate_id, device_id, scanned_by, control_type) -> None:
        self._st = st
        self._event_id = event_id
        self._gate_id = gate_id
        self._device_id = device_id
        self._scanned_by = scanned_by
        self._control_type = control_type

    def mark_seen(self, ticket_id: str, at: datetime) -> tuple[bool, Exception | None]:
        ok = admissions_repo.try_insert_admitted(
            self._st,
            ticket_id=ticket_id,
            event_id=self._event_id,
            gate_id=self._gate_id,
            device_id=self._device_id,
            scanned_by=self._scanned_by or None,
            scanned_at=at,
            control_type=self._control_type,
        )
        return ok, None

    def seen(self, ticket_id: str) -> bool:
        rows = self._st.fetchall(
            """SELECT 1 FROM admissions
               WHERE ticket_id = ? AND control_type = ? AND result = 'admitted'
               LIMIT 1""",
            (ticket_id, self._control_type),
        )
        return bool(rows)


@router.get("/scan/events")
def list_scan_events(state: AppState = Depends(require_user)):
    """List published events the authenticated staff member may scan.

    The mobile application uses this endpoint during startup so an operator
    never has to know or configure an event identifier at build time.
    """
    memberships = state.store.fetchall(
        """SELECT org_id, role FROM org_members
           WHERE user_id = ?""",
        (state.current_user.id,),
    )
    events = []
    for membership in memberships:
        role = membership["role"]
        if not rbac.role_meets(role, rbac.ROLE_SCANNER):
            continue
        for event in events_svc.list_by_org(state.store, membership["org_id"]):
            if event["status"] != "published":
                continue
            events.append({**event, "scan_role": role})
    events.sort(key=lambda event: (event["starts_at"], event["id"]))
    return {"events": events}


def _parse_scanned_at(value: str) -> datetime:
    raw = value
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw).astimezone(timezone.utc)


def _participant_view(st, row) -> dict:
    options = st.fetchall(
        """SELECT tt.name, tt.product_kind, oi.quantity
           FROM order_items oi
           JOIN ticket_types tt ON tt.id = oi.ticket_type_id
           WHERE oi.order_id = ? AND tt.product_kind IN ('option', 'goodie')
           ORDER BY tt.sort_order ASC, tt.name ASC""",
        (row["order_id"],),
    )
    return {
        "first_name": row["buyer_first_name"] or "",
        "last_name": row["buyer_last_name"] or "",
        "holder_name": row["holder_name"] or "",
        "email": row["buyer_email"] or "",
        "school_name": row["school_name"] or "",
        "pass_type": row["pass_tier"] or row["ticket_type_name"] or "",
        "options": [
            {"name": option["name"], "kind": option["product_kind"], "quantity": option["quantity"]}
            for option in options
        ],
    }


def _ticket_details(st, ticket_id: str) -> dict:
    row = st.fetchone(
        """SELECT t.serial, t.holder_name, tt.name AS ticket_type_name,
                  tt.pass_tier, o.buyer_first_name, o.buyer_last_name,
                  o.buyer_email, o.school_name, t.order_id
           FROM tickets t
           JOIN ticket_types tt ON tt.id = t.ticket_type_id
           JOIN orders o ON o.id = t.order_id
           WHERE t.id = ?""",
        (ticket_id,),
    )
    if row is None:
        return {}
    return {
        "serial": row["serial"] or "",
        "holder_name": row["holder_name"] or "",
        "participant": _participant_view(st, row),
    }


def _control_allowed(st, ticket_type_id: str, control_type: str) -> bool:
    """Return the explicit organizer-configured right for one ticket type."""
    ticket_type = ticket_types_repo.get_ticket_type_by_id(st, ticket_type_id)
    return {
        "event_entry": ticket_type.access_event,
        "food_access": ticket_type.access_food,
        "merch_pickup": ticket_type.access_merch,
        "after_entry": ticket_type.access_after,
    }[control_type]


@router.post("/scan")
def scan_ticket(body: ScanBody, state: AppState = Depends(require_user)):
    """Verify a capability and record an online control operation."""
    if not body.event_id or not body.capability:
        return json_error(400, "invalid_request", "event_id and capability are required")
    if not rbac.can_manage_event(state.store, state.current_user.id, body.event_id, rbac.ROLE_SCANNER):
        return json_error(403, "forbidden", "you are not allowed to scan for this event")
    now = datetime.now(timezone.utc)
    if body.scanned_at:
        try:
            now = _parse_scanned_at(body.scanned_at)
        except ValueError:
            return json_error(400, "invalid_request", "scanned_at must be RFC3339")
    try:
        cap_eid = cap.peek_eid(body.capability)
    except cap.CapabilityError as err:
        return {"result": admission.Status.INVALID.value, "reason": str(err), "ticket_id": ""}
    ring = issue_mod.issuer_public_keys(state.store, cap_eid or body.event_id)
    try:
        verified = cap.verify_with_ring(body.capability, ring, now)
        if verified.eid == body.event_id and not _control_allowed(
            state.store, verified.tt, body.control_type
        ):
            return {
                "result": admission.Status.NOT_AUTHORIZED.value,
                "reason": "ticket does not grant this control",
                "ticket_id": verified.tid,
                "control_type": body.control_type,
            }
    except cap.CapabilityError:
        # The admission engine below returns its normalized invalid reason.
        pass
    seen = _DbSeenSet(
        state.store, body.event_id, body.gate_id, body.device_id,
        state.current_user.id, body.control_type,
    )
    result = admission.decide(body.capability, ring, body.event_id, seen, now, store=state.store)
    ticket_id = result.payload.tid if result.payload else ""
    out = {
        "result": result.status.value,
        "reason": result.reason,
        "ticket_id": ticket_id,
        "serial": "",
        "holder_name": "",
        "participant": None,
        "control_type": body.control_type,
        "first_scan": None,
    }
    if ticket_id:
        out.update(_ticket_details(state.store, ticket_id))
    if result.status == admission.Status.DUPLICATE and ticket_id:
        out["first_scan"] = admissions_repo.first_admission(state.store, ticket_id, body.control_type)
    return out


@router.post("/scan/sync")
def sync_scans(body: SyncScanBody, state: AppState = Depends(require_user)):
    """Verify and reconcile a bounded mobile outbox batch idempotently."""
    if not body.event_id:
        return json_error(400, "invalid_request", "event_id is required")
    if not rbac.can_manage_event(state.store, state.current_user.id, body.event_id, rbac.ROLE_SCANNER):
        return json_error(403, "forbidden", "you are not allowed to scan for this event")
    ring = issue_mod.issuer_public_keys(state.store, body.event_id)
    results = []
    for item in body.operations:
        try:
            scanned_at = _parse_scanned_at(item.scanned_at)
        except (TypeError, ValueError):
            results.append({"operation_id": item.operation_id, "result": "invalid", "reason": "scanned_at must be RFC3339", "replayed": False})
            continue
        try:
            payload = cap.verify_with_ring(item.capability, ring, scanned_at)
        except cap.CapabilityError as err:
            results.append({"operation_id": item.operation_id, "result": "invalid", "reason": str(err), "replayed": False})
            continue
        if payload.eid != body.event_id:
            results.append({"operation_id": item.operation_id, "result": "wrong_event", "reason": "capability is for a different event", "replayed": False})
            continue
        if not _control_allowed(state.store, payload.tt, item.control_type):
            results.append({
                "operation_id": item.operation_id,
                "ticket_id": payload.tid,
                "result": "not_authorized",
                "reason": "ticket does not grant this control",
                "replayed": False,
            })
            continue
        blocked = admission.reject_if_ticket_not_valid(state.store, payload)
        if blocked is not None:
            results.append({"operation_id": item.operation_id, "result": blocked.status.value, "reason": blocked.reason, "replayed": False})
            continue
        result, replayed = admissions_repo.record_offline_claim(
            state.store,
            operation_id=item.operation_id,
            ticket_id=payload.tid,
            event_id=body.event_id,
            control_type=item.control_type,
            gate_id=item.gate_id,
            device_id=item.device_id,
            scanned_by=state.current_user.id,
            scanned_at=scanned_at,
            reported_result=item.reported_result,
        )
        results.append({
            "operation_id": item.operation_id,
            "ticket_id": payload.tid,
            "result": result,
            "reported_result": item.reported_result,
            "replayed": replayed,
            "first_scan": admissions_repo.first_admission(state.store, payload.tid, item.control_type),
        })
    return {"results": results}


@router.get("/events/{event_id}/scan-bundle")
def scan_bundle(event_id: str, state: AppState = Depends(require_user)):
    """Return the signed offline snapshot required by authorized scan devices."""
    if not rbac.can_manage_event(state.store, state.current_user.id, event_id, rbac.ROLE_SCANNER):
        return json_error(403, "forbidden", "you are not allowed to scan for this event")
    rows = state.store.fetchall(
        """SELECT t.id, t.capability, t.status, t.holder_name, t.ticket_type_id,
                  t.holder_user_id, t.order_id,
                  tt.name AS ticket_type_name, tt.pass_tier,
                  tt.access_event, tt.access_food, tt.access_merch, tt.access_after,
                  o.buyer_first_name, o.buyer_last_name, o.school_name
           FROM tickets t
           JOIN ticket_types tt ON tt.id = t.ticket_type_id
           JOIN orders o ON o.id = t.order_id
           WHERE t.event_id = ?
           ORDER BY t.issued_at ASC, t.id ASC""",
        (event_id,),
    )
    tickets = []
    for row in rows:
        tickets.append({
            "ticket_id": row["id"],
            "capability": row["capability"],
            "status": row["status"],
            "participant": {
                "participant_id": row["holder_user_id"] or row["order_id"],
                "first_name": row["buyer_first_name"] or "",
                "last_name": row["buyer_last_name"] or "",
                "holder_name": row["holder_name"] or "",
                "school_name": row["school_name"] or "",
                "pass_type": row["pass_tier"] or row["ticket_type_name"] or "",
            },
            "scan_rights": {
                "event_entry": bool(row["access_event"]),
                "food_access": bool(row["access_food"]),
                "merch_pickup": bool(row["access_merch"]),
                "after_entry": bool(row["access_after"]),
            },
        })
    return {
        "event_id": event_id,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "issuer_keys": events_svc.issuer_keys_json(state.store, event_id),
        "tickets": tickets,
    }


@router.get("/events/{event_id}/attendees")
def list_attendees(event_id: str, state: AppState = Depends(require_user)):
    """List attendees."""
    if not rbac.can_manage_event(state.store, state.current_user.id, event_id, rbac.ROLE_SCANNER):
        return json_error(403, "forbidden", "forbidden")
    rows = state.store.fetchall(
        """SELECT t.id, t.order_id, t.serial, t.holder_name, t.status, t.ticket_type_id,
                  tt.name AS ticket_type_name, tt.pass_tier,
                  o.buyer_email, o.buyer_first_name, o.buyer_last_name, o.school_name
           FROM tickets t
           JOIN ticket_types tt ON tt.id = t.ticket_type_id
           JOIN orders o ON o.id = t.order_id
           WHERE t.event_id = ?
           ORDER BY t.issued_at ASC, t.id ASC""",
        (event_id,),
    )
    attendees = []
    for row in rows:
        attendees.append({
            "ticket_id": row["id"], "order_id": row["order_id"], "serial": row["serial"],
            "holder_name": row["holder_name"], "status": row["status"],
            "ticket_type_id": row["ticket_type_id"], "ticket_type_name": row["ticket_type_name"],
            "pass_type": row["pass_tier"] or row["ticket_type_name"], "email": row["buyer_email"],
            "first_name": row["buyer_first_name"] or "", "last_name": row["buyer_last_name"] or "",
            "school_name": row["school_name"] or "",
        })
    return {"attendees": attendees}
