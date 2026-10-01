"""Check-in API (``/api/checkin``): online scan, offline sync, snapshot, conflicts, audit, health.

Design: docs/checkin/DESIGN.md. Errors use the 3A envelope ``{"error": {"code", "message"}}``.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Callable
from uuid import UUID

import psycopg
import psycopg_pool
from fastapi import APIRouter, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

from checkin import repository, service, signing, sync_service
from checkin.ports import AuthError
from checkin.runtime import get_runtime
from checkin.schemas import AcknowledgeRequest, ScanRequest, ScanResponse, SyncRequest
from checkin.service import ApiError
from http_layer.errors import json_error


class CheckinRoute(APIRoute):
    """Maps validation, auth and infrastructure errors to the stable check-in error codes."""

    def get_route_handler(self) -> Callable:
        original = super().get_route_handler()

        async def handler(request: Request) -> Response:
            try:
                return await original(request)
            except RequestValidationError as exc:
                first = exc.errors()[0] if exc.errors() else {}
                where = ".".join(str(p) for p in first.get("loc", ())[1:])
                # Only the location and the rule are reported: never the submitted value.
                return json_error(400, "invalid_request", f"{where}: {first.get('msg', 'invalid')}".strip(": "))
            except (ApiError, AuthError) as exc:
                resp = json_error(exc.status, exc.code, exc.message)
                for k, v in getattr(exc, "headers", {}).items():
                    resp.headers[k] = v
                return resp
            except (psycopg.errors.LockNotAvailable, psycopg_pool.PoolTimeout, psycopg.errors.DeadlockDetected):
                resp = json_error(503, "service_busy", "check-in is busy, retry")
                resp.headers["Retry-After"] = "1"
                return resp

        return handler


router = APIRouter(prefix="/checkin", tags=["checkin"], route_class=CheckinRoute)


@contextmanager
def _session(request: Request, *, event_id: str, role: str, terminal_id: UUID | None = None):
    """Pooled connection + authenticated principal (+ terminal registration when relevant)."""
    rt = get_runtime(request.app)
    with rt.pool.connection(timeout=5) as conn:
        principal = rt.auth.authenticate(conn, request)
        rt.auth.require_role(conn, principal, event_id, role)
        if terminal_id is not None:
            if not rt.limiter.allow(str(terminal_id)):
                raise ApiError(429, "rate_limited", "too many requests from this terminal")
            term = repository.register_terminal(conn, terminal_id, event_id, principal.user_id)
            if term["event_id"] != event_id:
                raise ApiError(403, "terminal_event_mismatch", "terminal is registered for another event")
            if term["revoked_at"] is not None:
                raise ApiError(403, "terminal_revoked", "terminal has been revoked")
        conn.commit()
        yield rt, conn, principal


@router.get("/health")
def health(request: Request):
    """Database and pool status. No authentication, no sensitive data."""
    rt = get_runtime(request.app)
    try:
        with rt.pool.connection(timeout=1) as conn:
            conn.execute("SELECT 1")
        db = "ok"
    except Exception:
        db = "down"
    stats = rt.pool.get_stats()
    body = {
        "status": "ok" if db == "ok" else "degraded",
        "db": db,
        "pool": {
            "size": stats.get("pool_size", 0),
            "available": stats.get("pool_available", 0),
            "waiting": stats.get("requests_waiting", 0),
        },
    }
    return body if db == "ok" else _json_503(body)


def _json_503(body: dict):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=503, content=body)


@router.post("/scan", response_model=ScanResponse)
def scan(body: ScanRequest, request: Request):
    """Online scan of one QR: verify, apply the station rule, consume atomically, journal."""
    with _session(request, event_id=body.event_id, role="scanner", terminal_id=body.terminal_id) as (rt, conn, p):
        return service.online_scan(rt, conn, p, body)


@router.post("/sync")
def sync(body: SyncRequest, request: Request):
    """Batch of offline scans: one status per operation, idempotent, order-independent conflicts."""
    with _session(request, event_id=body.event_id, role="scanner", terminal_id=body.terminal_id) as (rt, conn, p):
        return sync_service.sync_batch(rt, conn, p, body)


CONFLICT_TYPES = {
    "CROSS_TERMINAL_DOUBLE_ADMISSION",
    "SAME_TERMINAL_REPLAY",
    "LATE_REVOKED",
    "NOT_AUTHORIZED_SERVER_SIDE",
    "CLOCK_SUSPECT",
}


@router.get("/conflicts")
def conflicts(
    request: Request,
    event_id: str = Query(min_length=1, max_length=64),
    status: str | None = Query(default=None, pattern="^(open|acknowledged)$"),
    type: str | None = Query(default=None, max_length=40),
    cursor: int | None = Query(default=None, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    """Conflicts of an event, newest first (supervisor)."""
    if type is not None and type not in CONFLICT_TYPES:
        raise ApiError(400, "invalid_request", "unknown conflict type")
    with _session(request, event_id=event_id, role="admin") as (_rt, conn, _p):
        rows = repository.list_conflicts(
            conn, event_id=event_id, status=status, ctype=type, cursor=cursor, limit=limit + 1
        )
    has_more = len(rows) > limit
    rows = rows[:limit]
    return {
        "conflicts": [sync_service.conflict_view(r) for r in rows],
        "next_cursor": rows[-1]["conflict_id"] if has_more and rows else None,
    }


@router.post("/conflicts/{conflict_id}/acknowledge")
def acknowledge(conflict_id: int, body: AcknowledgeRequest, request: Request):
    """Supervisor acknowledges a conflict. Idempotent: the first resolver and note are kept."""
    rt = get_runtime(request.app)
    with rt.pool.connection(timeout=5) as conn:
        principal = rt.auth.authenticate(conn, request)
        event_id = repository.conflict_event(conn, conflict_id)
        if event_id is None:
            raise ApiError(404, "not_found", "conflict not found")
        rt.auth.require_role(conn, principal, event_id, "admin")
        row = repository.acknowledge_conflict(conn, conflict_id, principal.user_id, body.note)
        conn.commit()
    return {"conflict": sync_service.conflict_view(row)}


@router.get("/events")
def events(request: Request):
    """Published events the signed-in agent may scan (at least ``scanner`` in the organisation)."""
    rt = get_runtime(request.app)
    with rt.pool.connection(timeout=5) as conn:
        principal = rt.auth.authenticate(conn, request)
        rows = repository.accessible_events(conn, principal.user_id)
        conn.commit()
    return {
        "events": [
            {
                "event_id": r["event_id"],
                "title": r["title"],
                "slug": r["slug"],
                "starts_at": r["starts_at"],
                "ends_at": r["ends_at"],
                "timezone": r["timezone"],
                "role": r["role"],
            }
            for r in rows
        ]
    }


@router.get("/signing-key")
def signing_key(request: Request):
    """Public key that verifies the snapshot signature (to pin in the app). No authentication needed."""
    signer = get_runtime(request.app).signer
    if signer is None:
        raise ApiError(404, "signing_not_configured", "snapshot signing is not configured on this server")
    return signer.describe()


@router.get("/stats")
def stats(request: Request, event_id: str = Query(min_length=1, max_length=64)):
    """Live counters per station, conflicts and terminals (no personal data)."""
    with _session(request, event_id=event_id, role="scanner") as (rt, conn, _p):
        cached = service.STATS_CACHE.get(event_id, rt.cfg.stats_ttl_seconds)
        if cached is not None:
            return cached
        payload = sync_service.stats_view(event_id, rt.clock(), repository.stats(conn, event_id))
        service.STATS_CACHE.put(event_id, payload)
    return payload


@router.get("/snapshot")
def snapshot(
    request: Request,
    event_id: str = Query(min_length=1, max_length=64),
    since_version: int = Query(default=0, ge=0),
    cursor: str | None = Query(default=None, max_length=512),
    limit: int | None = Query(default=None, ge=1, le=5000),
):
    """Versioned entitlements for the offline cache (delta with ``since_version``, ETag, gzip)."""
    with _session(request, event_id=event_id, role="scanner") as (rt, conn, _p):
        etag, raw, packed, signature = service.snapshot(
            rt, conn, event_id=event_id, since_version=since_version, cursor=cursor, limit=limit
        )
    headers = {"ETag": etag, "Cache-Control": "private, max-age=0", "Vary": "Accept-Encoding"}
    if signature:
        headers[signing.HEADER] = signature
    if request.headers.get("If-None-Match") == etag:
        return Response(status_code=304, headers=headers)
    if "gzip" in request.headers.get("Accept-Encoding", "").lower():
        headers["Content-Encoding"] = "gzip"
        return Response(content=packed, media_type="application/json", headers=headers)
    return Response(content=raw, media_type="application/json", headers=headers)


@router.get("/logs")
def logs(
    request: Request,
    event_id: str = Query(min_length=1, max_length=64),
    station: str | None = Query(default=None, max_length=40),
    ticket_id: str | None = Query(default=None, max_length=64),
    terminal_id: UUID | None = None,
    since: datetime | None = None,
    cursor: int | None = Query(default=None, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
):
    """Audit listing of every scan (supervisor). Never returns a QR or capability."""
    from checkin import domain

    st = domain.normalize_station(station) if station else None
    if station and st is None:
        raise ApiError(400, "unknown_station", "invalid station")
    with _session(request, event_id=event_id, role="admin") as (_rt, conn, _p):
        rows = repository.list_logs(
            conn,
            event_id=event_id,
            station=st,
            ticket_id=ticket_id,
            terminal_id=terminal_id,
            since=since,
            cursor=cursor,
            limit=limit + 1,
        )
    has_more = len(rows) > limit
    rows = rows[:limit]
    return {
        "logs": rows,
        "next_cursor": rows[-1]["log_id"] if has_more and rows else None,
    }
