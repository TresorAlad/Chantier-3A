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

from checkin import repository, service
from checkin.ports import AuthError
from checkin.runtime import get_runtime
from checkin.schemas import ScanRequest, ScanResponse
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
        etag, raw, packed = service.snapshot(
            rt, conn, event_id=event_id, since_version=since_version, cursor=cursor, limit=limit
        )
    headers = {"ETag": etag, "Cache-Control": "private, max-age=0", "Vary": "Accept-Encoding"}
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
