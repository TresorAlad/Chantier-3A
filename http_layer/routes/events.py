"""Public and organizer event listing and detail routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from events import service as events_svc
from http_layer.deps import AppState, get_app_state
from http_layer.errors import json_error

router = APIRouter(prefix="/events", tags=["events"])


def _parse_rfc3339(label: str, value: str) -> datetime | None:
    """Internal: parse rfc3339."""
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{label} must be RFC3339")


@router.get("/")
def list_public_events(
    state: AppState = Depends(get_app_state),
    q: str = Query("", alias="q"),
    category: str = Query(""),
    host: str = Query(""),
    from_: str = Query("", alias="from"),
    to: str = Query(""),
    limit: int = Query(0),
):
    """List public events."""
    try:
        scope, org_views, org_ids = events_svc.host_scope(state.store, state.config)
    except RuntimeError:
        return json_error(500, "internal_error", "internal error")

    view = {
        "scope": scope,
        "name": events_svc.host_display_name(state.config, scope, org_views),
        "organisations": org_views,
        "multi_org": len(org_views) > 1,
        "peers_included": scope == "peers",
    }

    if host:
        matched = next((o for o in org_views if o["slug"] == host or o["id"] == host), None)
        if not matched:
            return json_error(404, "not_found", "no such host")
        org_ids = [matched["id"]]
        view["org"] = matched

    try:
        from_ts = _parse_rfc3339("from", from_)
        to_ts = _parse_rfc3339("to", to)
    except ValueError as err:
        return json_error(400, "invalid_request", str(err))

    if limit < 0:
        return json_error(400, "invalid_request", "limit must be a non-negative integer")

    events = events_svc.list_public(
        state.store,
        state.config,
        query=q,
        category=category,
        org_ids=org_ids,
        from_ts=from_ts,
        to_ts=to_ts,
        limit=limit,
    )
    return {"events": events, "host": view}
