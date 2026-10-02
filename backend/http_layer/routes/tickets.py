"""Buyer ticket download and capability token routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from auth import rbac
from http_layer.deps import AppState, get_app_state, require_user
from http_layer.errors import json_error
from http_layer.routes.orders import _tickets_json, build_ticket_pdf_bytes
from store.store import NotFoundError

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("")
def list_my_tickets(state: AppState = Depends(require_user)):
    """List my tickets."""
    tickets = state.services.orders.tickets_for_user(state.current_user.id)
    return {"tickets": _tickets_json(tickets)}


@router.get("/{ticket_id}")
def get_ticket(ticket_id: str, state: AppState = Depends(require_user)):
    """Get ticket."""
    try:
        ticket = state.services.orders.ticket(ticket_id)
    except NotFoundError:
        return json_error(404, "not_found", "ticket not found")
    if ticket.holder_user_id and ticket.holder_user_id != state.current_user.id:
        return json_error(404, "not_found", "ticket not found")
    return {"ticket": _tickets_json([ticket])[0]}


def _can_access_ticket_pdf(state: AppState, ticket) -> bool:
    user = state.current_user
    if user is None:
        return False
    if ticket.holder_user_id and ticket.holder_user_id == user.id:
        return True
    return rbac.can_manage_event(state.store, user.id, ticket.event_id, rbac.ROLE_SCANNER)


@router.get("/{ticket_id}/pdf")
def ticket_pdf(ticket_id: str, state: AppState = Depends(require_user)):
    """Authenticated PDF download (holder or event staff)."""
    try:
        ticket = state.services.orders.ticket(ticket_id)
    except NotFoundError:
        return json_error(404, "not_found", "ticket not found")
    if not _can_access_ticket_pdf(state, ticket):
        return json_error(403, "forbidden", "forbidden")
    try:
        pdf, filename = build_ticket_pdf_bytes(state, ticket.order_id, ticket_id=ticket_id)
    except ValueError as err:
        code = str(err)
        if code == "not_paid":
            return json_error(400, "invalid_request", "ticket not available until order is paid")
        return json_error(404, "not_found", "ticket not found")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{ticket_id}/resend")
def resend_ticket_email(ticket_id: str, state: AppState = Depends(require_user)):
    """Re-send the ticket confirmation e-mail (event admin)."""
    try:
        ticket = state.services.orders.ticket(ticket_id)
    except NotFoundError:
        return json_error(404, "not_found", "ticket not found")
    if not rbac.can_manage_event(state.store, state.current_user.id, ticket.event_id, rbac.ROLE_ADMIN):
        return json_error(403, "forbidden", "forbidden")
    try:
        order = state.services.orders.get(ticket.order_id)
    except NotFoundError:
        return json_error(404, "not_found", "order not found")
    if order.status != "paid":
        return json_error(400, "invalid_request", "order is not paid")
    state.services.notify.resend_order_confirmation(ticket.order_id)
    return {"ok": True, "message": "e-mail queued"}
