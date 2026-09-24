"""Visitor checkout and order status routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from auth import rbac
from http_layer.deps import AppState, get_app_state, require_user
from http_layer.errors import json_error
from orders.service import CreateOrderInput, OrderItemInput, OrdersError
from payments import types as pt
from payments.manual import ManualProvider
from store.store import NotFoundError

router = APIRouter(tags=["orders"])


class OrderItemBody(BaseModel):
    """Single line item: ticket type id and quantity."""
    ticket_type_id: str
    quantity: int


class BuyerBody(BaseModel):
    """Guest checkout contact details."""
    email: str
    name: str = ""


class CreateOrderBody(BaseModel):
    """Request body to start checkout for an event."""
    event_id: str
    items: list[OrderItemBody]
    buyer: BuyerBody
    provider: str = ""


def _order_json(o) -> dict:
    """Internal: order json."""
    out = {
        "id": o.id,
        "event_id": o.event_id,
        "user_id": o.user_id,
        "buyer_email": o.buyer_email,
        "buyer_name": o.buyer_name,
        "status": o.status,
        "subtotal_minor": o.subtotal_minor,
        "fee_minor": o.fee_minor,
        "total_minor": o.total_minor,
        "currency": o.currency,
        "provider": o.provider,
        "provider_ref": o.provider_ref,
        "created_at": o.created_at.isoformat().replace("+00:00", "Z"),
    }
    if o.paid_at:
        out["paid_at"] = o.paid_at.isoformat().replace("+00:00", "Z")
    if o.items is not None:
        out["items"] = o.items
    return out


def _tickets_json(tickets) -> list[dict]:
    """Internal: tickets json."""
    return [
        {
            "id": t.id,
            "order_id": t.order_id,
            "event_id": t.event_id,
            "ticket_type_id": t.ticket_type_id,
            "holder_user_id": t.holder_user_id,
            "holder_name": t.holder_name,
            "serial": t.serial,
            "capability": t.capability,
            "status": t.status,
            "issued_at": t.issued_at.isoformat().replace("+00:00", "Z"),
        }
        for t in tickets
    ]


@router.post("/orders", status_code=201)
def create_order(body: CreateOrderBody, state: AppState = Depends(get_app_state)):
    """Create order."""
    if not body.event_id or not body.items or not body.buyer.email:
        return json_error(400, "invalid_request", "event_id, at least one item, and buyer.email are required")
    for it in body.items:
        if not it.ticket_type_id or it.quantity <= 0:
            return json_error(
                400,
                "invalid_request",
                "each item requires ticket_type_id and a positive quantity",
            )
    inp = CreateOrderInput(
        event_id=body.event_id,
        buyer_email=body.buyer.email,
        buyer_name=body.buyer.name,
        items=[OrderItemInput(t.ticket_type_id, t.quantity) for t in body.items],
        provider=body.provider,
    )
    if state.current_user:
        inp.user_id = state.current_user.id
    try:
        order, charge = state.services.orders.create(inp)
    except NotFoundError:
        return json_error(404, "not_found", "event or ticket type not found")
    except OrdersError as err:
        return json_error(400, "invalid_request", str(err))
    except Exception:
        return json_error(500, "internal_error", "internal error")
    return {
        "order": _order_json(order),
        "payment": {
            "provider": charge.provider,
            "redirect_url": charge.redirect_url,
            "reference": charge.reference,
            "instructions": charge.instructions,
        },
    }


@router.get("/orders")
def list_my_orders(state: AppState = Depends(require_user)):
    """List my orders."""
    orders = state.services.orders.list_for_user(state.current_user.id)
    return {"orders": [_order_json(o) for o in orders]}


@router.get("/orders/{order_id}")
def get_order(order_id: str, state: AppState = Depends(require_user)):
    """Get order."""
    try:
        order = state.services.orders.get(order_id)
    except NotFoundError:
        return json_error(404, "not_found", "order not found")
    if not order.user_id or order.user_id != state.current_user.id:
        return json_error(404, "not_found", "order not found")
    return {"order": _order_json(order)}


@router.get("/events/{event_id}/orders")
def list_event_orders(event_id: str, state: AppState = Depends(require_user)):
    """List event orders."""
    if not rbac.can_manage_event(state.store, state.current_user.id, event_id, rbac.ROLE_ADMIN):
        return json_error(403, "forbidden", "you are not an admin/owner of this event's org")
    orders = state.services.orders.list_for_event(event_id)
    views = []
    for ord in orders:
        view = _order_json(ord)
        if ord.provider == pt.PROVIDER_NAME_MANUAL:
            provider = state.services.payments.get(pt.PROVIDER_NAME_MANUAL)
            if isinstance(provider, ManualProvider):
                rec, ok = provider.record(ord.id)
                if ok and rec.get("marked_by"):
                    view["marked_by"] = rec["marked_by"]
                    if rec.get("marked_at"):
                        view["marked_at"] = rec["marked_at"].isoformat().replace("+00:00", "Z")
        views.append(view)
    return {"orders": views}


@router.post("/orders/{order_id}/mark-paid")
def mark_order_paid(order_id: str, state: AppState = Depends(require_user)):
    """Mark order paid."""
    return _mark_order(order_id, state, paid=True)


@router.post("/orders/{order_id}/mark-failed")
def mark_order_failed(order_id: str, state: AppState = Depends(require_user)):
    """Mark order failed."""
    return _mark_order(order_id, state, paid=False)


def _mark_order(order_id: str, state: AppState, *, paid: bool):
    """Internal: mark order."""
    try:
        ord = state.services.orders.get(order_id)
    except NotFoundError:
        return json_error(404, "not_found", "order not found")
    if not rbac.can_manage_event(state.store, state.current_user.id, ord.event_id, rbac.ROLE_ADMIN):
        return json_error(403, "forbidden", "you are not an admin/owner of this event's org")
    if ord.provider != pt.PROVIDER_NAME_MANUAL:
        return json_error(400, "invalid_request", "order was not created with the manual payment provider")
    provider = state.services.payments.get(pt.PROVIDER_NAME_MANUAL)
    if not isinstance(provider, ManualProvider):
        return json_error(500, "internal_error", "manual provider unavailable")
    marked_by = state.current_user.email
    if paid:
        if ord.status not in ("pending", "paid"):
            return json_error(409, "conflict", f"order cannot be marked paid from status {ord.status}")
        result = provider.mark_paid(order_id, marked_by)
        try:
            updated, tickets = state.services.orders.settle(result)
        except OrdersError:
            return json_error(409, "conflict", "order could not be settled from its current status")
        return {"order": _order_json(updated), "tickets": _tickets_json(tickets)}
    if ord.status == "failed":
        return {"order": _order_json(ord)}
    if ord.status != "pending":
        return json_error(409, "conflict", f"order cannot be marked failed from status {ord.status}")
    provider.mark_failed(order_id, marked_by)
    try:
        updated = state.services.orders.mark_failed(order_id)
    except OrdersError:
        return json_error(409, "conflict", "order could not be marked failed from its current status")
    return {"order": _order_json(updated)}
