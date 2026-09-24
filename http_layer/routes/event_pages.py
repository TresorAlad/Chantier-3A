"""Public event landing page data for visitors."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from http_layer.deps import AppState, require_user
from http_layer.errors import json_error

router = APIRouter(prefix="/events", tags=["event-pages"])


@router.get("/{event_id}/page")
def get_event_page(event_id: str, state: AppState = Depends(require_user)):
    """Get event page."""
    return json_error(404, "not_found", "event page not configured")


@router.put("/{event_id}/page")
def put_event_page(event_id: str, body: dict, state: AppState = Depends(require_user)):
    """Put event page."""
    return json_error(404, "not_found", "event page not configured")


@router.delete("/{event_id}/page", status_code=204)
def delete_event_page(event_id: str, state: AppState = Depends(require_user)):
    """Delete event page."""
    return json_error(404, "not_found", "event page not configured")
