"""Payment provider selection, webhooks, and manual confirm routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request

from http_layer.deps import AppState, get_app_state
from http_layer.errors import json_error
from orders.service import OrdersError
from payments import orchestration
from payments import types as pt
from store.store import NotFoundError

router = APIRouter(prefix="/payments", tags=["payments"])


class _OrderLookup:
    """Internal: OrderLookup."""
    def __init__(self, state: AppState) -> None:
        """Initialize ``_OrderLookup``."""
        self._state = state

    def lookup(self, reference: str) -> pt.OrderRef:
        """Lookup on ``_OrderLookup``."""
        order = self._state.services.orders.get(reference)
        return pt.OrderRef(id=order.id, amount_minor=order.total_minor, currency=order.currency)


@router.post("/verify")
def verify_payment(body: dict, state: AppState = Depends(get_app_state)):
    """Verify payment."""
    reference = (body.get("reference") or "").strip()
    if not reference:
        return json_error(400, "invalid_request", "reference is required")
    try:
        order = state.services.orders.get(reference)
    except NotFoundError:
        return json_error(404, "not_found", "order not found")
    provider = state.services.payments.get(order.provider)
    if provider is None:
        return json_error(500, "internal_error", "provider not registered")
    lookup = _OrderLookup(state)
    try:
        result = orchestration.handle_verify(provider, reference, lookup)
    except Exception:
        return json_error(402, "payment_not_confirmed", "payment could not be verified as paid")
    try:
        _, tickets = state.services.orders.settle(result)
    except Exception:
        return json_error(500, "internal_error", "internal error")
    updated = state.services.orders.get(reference)
    return {
        "order": _order_json(updated),
        "tickets": _tickets_json(tickets),
    }


@router.post("/webhook/{provider_name}")
async def payment_webhook(
    provider_name: str,
    request: Request,
    state: AppState = Depends(get_app_state),
):
    """Payment webhook."""
    provider = state.services.payments.get(provider_name)
    if provider is None:
        return json_error(404, "not_found", "unknown payment provider")
    body = await request.body()
    headers = {k: v for k, v in request.headers.items()}
    lookup = _OrderLookup(state)
    try:
        result = orchestration.handle_webhook(
            provider,
            body,
            headers,
            state.services.webhook_seen,
            lookup,
        )
    except pt.ErrReplayed:
        return {}
    except pt.ErrUnhandledEvent:
        return {}
    except Exception:
        return json_error(400, "invalid_request", "webhook rejected")
    try:
        state.services.orders.settle(result)
    except OrdersError:
        return json_error(500, "internal_error", "internal error")
    return {}


def _order_json(o) -> dict:
    """Internal: order json."""
    out = {
        "id": o.id,
        "event_id": o.event_id,
        "status": o.status,
        "total_minor": o.total_minor,
        "currency": o.currency,
        "provider": o.provider,
    }
    if o.paid_at:
        out["paid_at"] = o.paid_at.isoformat().replace("+00:00", "Z")
    return out


def _tickets_json(tickets) -> list[dict]:
    """Internal: tickets json."""
    from http_layer.routes.orders import _tickets_json as full

    return full(tickets)
