"""Buyer ticket download and capability token routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from http_layer.deps import AppState, get_app_state, require_user
from http_layer.errors import json_error
from http_layer.routes.orders import _tickets_json
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


@router.get("/{ticket_id}/pdf")
def ticket_pdf(ticket_id: str, state: AppState = Depends(get_app_state)):
    """Ticket pdf."""
    try:
        ticket = state.services.orders.ticket(ticket_id)
    except NotFoundError:
        return json_error(404, "not_found", "ticket not found")
    body = (
        f"Cackle ticket\nSerial: {ticket.serial}\nEvent: {ticket.event_id}\n"
        f"Holder: {ticket.holder_name}\n\nCapability (QR):\n{ticket.capability}\n"
    ).encode()
    return Response(content=body, media_type="text/plain; charset=utf-8")
