"""Multi-host sync feed and peer authentication routes."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request, Response

from auth import rbac
from http_layer.deps import AppState, get_app_state, require_user
from http_layer.errors import json_error
from scan import peerauth
from store import sync_identity, sync_ops, sync_peers
from store.sync_peers import SyncPeer
from store.store import new_ulid

router = APIRouter(prefix="/sync", tags=["sync"])
peer_router = APIRouter(tags=["peer-events"])

SYNC_CAVEAT = (
    "Replication makes a cross-gate double admission visible sooner and on more nodes. "
    "It cannot prevent one: two gates that could not see each other at the moment of the scan both "
    "opened the door, and no merge rule, transport, or number of nodes reaches back to that moment. "
    "It is also only as complete as the sync — claims on a node that has not been reached yet, or on "
    "a gate whose log never arrived anywhere, are invisible here."
)

ALGEBRA_NAME = "dmtap-sync-v1"

_nonce_cache = peerauth.NonceCache()


def _authenticate_peer(request: Request, body: bytes, store) -> list[SyncPeer]:
    """Internal: authenticate peer."""
    presented = peerauth.presented_key(dict(request.headers))
    if not presented:
        raise ValueError("unsigned")
    peers = sync_peers.enabled_sync_peers_by_key(store, presented)
    if not peers:
        raise ValueError("unenrolled")
    peerauth.verify_request(
        request.method,
        request.url.path,
        request.url.query,
        dict(request.headers),
        body,
        peers[0].public_key,
        _nonce_cache,
    )
    return peers


def _signed_json_response(request: Request, store, payload: dict, status: int = 200) -> Response:
    """Internal: signed json response."""
    ident = sync_identity.ensure_node_identity(store)
    body = json.dumps(payload).encode()
    headers: dict[str, str] = {}
    req_nonce = request.headers.get(peerauth.HEADER_NONCE) or ""
    peerauth.sign_response_headers(headers, ident.private_key, req_nonce, body)
    return Response(content=body, status_code=status, headers={**headers, "Content-Type": "application/json"})


@router.get("/ops")
async def sync_pull(request: Request, after: int = Query(0), limit: int = Query(128)):
    """Sync pull."""
    body = await request.body()
    state: AppState = request.state.app_state
    try:
        peers = _authenticate_peer(request, body, state.store)
    except peerauth.ErrUnsigned:
        return json_error(401, "unauthorized", "peer authentication required")
    except ValueError as err:
        msg = str(err)
        if msg == "unenrolled":
            return json_error(401, "unauthorized", "this node key is not enrolled here")
        return json_error(401, "unauthorized", "peer request authentication failed")
    if after < 0:
        return json_error(400, "invalid_request", "after must be a non-negative integer cursor")
    if limit <= 0:
        limit = 128
    limit = min(limit, 256)
    ident = sync_identity.ensure_node_identity(state.store)
    ops: list = []
    for p in peers:
        page = sync_ops.sync_ops_for_org_after(state.store, p.org_id, after, limit + 1)
        ops.extend(page)
    ops.sort(key=lambda o: o.seq)
    seen: set[int] = set()
    deduped = []
    for o in ops:
        if o.seq in seen:
            continue
        seen.add(o.seq)
        deduped.append(o)
    complete = len(deduped) <= limit
    if not complete:
        deduped = deduped[:limit]
    next_after = after
    wire = []
    for o in deduped:
        wire.append({"seq": o.seq, "event_id": o.event_id, "cose": base64.standard_b64encode(o.cose).decode()})
        next_after = o.seq
    resp = {
        "node": ident.public_key,
        "algebra": ALGEBRA_NAME,
        "ops": wire,
        "next_after": next_after,
        "complete": complete,
        "caveat": SYNC_CAVEAT,
    }
    return _signed_json_response(request, state.store, resp)


@router.post("/ops")
async def sync_push(request: Request):
    """Sync push."""
    raw = await request.body()
    state: AppState = request.state.app_state
    try:
        peers = _authenticate_peer(request, raw, state.store)
    except peerauth.ErrUnsigned:
        return json_error(401, "unauthorized", "peer authentication required")
    except ValueError:
        return json_error(401, "unauthorized", "peer request authentication failed")
    try:
        req = json.loads(raw)
    except json.JSONDecodeError:
        return json_error(400, "invalid_request", "invalid JSON body")
    ops_in = req.get("ops") or []
    if len(ops_in) > 256:
        return json_error(400, "invalid_request", "too many ops in push")
    ident = sync_identity.ensure_node_identity(state.store)
    delivered_by = peerauth.presented_key(dict(request.headers))
    results = []
    for item in ops_in:
        try:
            cose = sync_ops.decode_cose_b64(item.get("cose") or "")
            event_id = item.get("event_id") or ""
            if not event_id or not cose:
                results.append({"stored": False, "applied": False, "reason": "missing event_id or cose"})
                continue
            op_id = sync_ops.op_id_from_cose(cose)
            op = sync_ops.SyncOp(
                seq=0,
                op_id=op_id,
                event_id=event_id,
                author=delivered_by,
                delivered_by=delivered_by,
                claim_ticket="",
                claim_device="",
                claim_scanned_at=datetime.now(timezone.utc),
                applied=False,
                cose=cose,
                created_at=datetime.now(timezone.utc),
            )
            stored = sync_ops.append_sync_op(state.store, op)
            results.append(
                {
                    "op_id": op_id if stored else "",
                    "stored": stored,
                    "applied": False,
                }
            )
        except Exception as err:
            results.append({"stored": False, "applied": False, "reason": str(err)})
    resp = {
        "node": ident.public_key,
        "algebra": ALGEBRA_NAME,
        "results": results,
        "caveat": SYNC_CAVEAT,
    }
    return _signed_json_response(request, state.store, resp)


@router.get("/status")
def sync_status(org: str = Query(""), state: AppState = Depends(require_user)):
    """Sync status."""
    if not org:
        return json_error(400, "invalid_request", "org query parameter is required")
    if not rbac.can_manage_org(state.store, state.current_user.id, org, rbac.ROLE_OWNER):
        return json_error(403, "forbidden", "sync status requires owner role on this org")
    ident = sync_identity.ensure_node_identity(state.store)
    peers = sync_peers.list_sync_peers(state.store, org)
    stats = sync_ops.sync_op_stats_for_org(state.store, org)
    return {
        "node": ident.public_key,
        "algebra": ALGEBRA_NAME,
        "peers": [_peer_view(p) for p in peers],
        "op_log": {
            "ops": stats.ops,
            "unapplied": stats.unapplied,
            "highest_seq": stats.highest_seq,
            "pending": stats.pending,
        },
        "caveat": SYNC_CAVEAT,
        "standalone": len(peers) == 0,
    }


@router.post("/peers")
def enrol_peer(body: dict, state: AppState = Depends(require_user)):
    """Enrol peer."""
    org_id = (body.get("org_id") or "").strip()
    pub = (body.get("public_key") or "").strip()
    if not org_id or not pub:
        return json_error(400, "invalid_request", "org_id and public_key are required")
    if not rbac.can_manage_org(state.store, state.current_user.id, org_id, rbac.ROLE_OWNER):
        return json_error(403, "forbidden", "enrolling a replication peer requires the owner role")
    try:
        key = sync_peers.normalize_node_key(pub)
    except ValueError:
        return json_error(400, "invalid_request", "public_key must be a 32-byte hex Ed25519 key")
    ident = sync_identity.ensure_node_identity(state.store)
    if ident.public_key == key:
        return json_error(400, "invalid_request", "that is this node's own key")
    p = SyncPeer(
        id=new_ulid(),
        org_id=org_id,
        name=(body.get("name") or "").strip(),
        url=(body.get("url") or "").strip().rstrip("/"),
        public_key=key,
        enabled=True,
        pull_cursor=0,
        push_cursor=0,
        last_sync_at=None,
        last_status="enrolled, never synced",
        created_at=datetime.now(timezone.utc),
    )
    try:
        sync_peers.create_sync_peer(state.store, p)
    except Exception as err:
        if "unique" in str(err).lower():
            return json_error(409, "conflict", "this node key is already enrolled for this org")
        return json_error(500, "internal_error", "internal error")
    return _peer_view(p)


@router.delete("/peers/{peer_id}")
def delete_peer(peer_id: str, state: AppState = Depends(require_user)):
    """Delete peer."""
    try:
        p = sync_peers.get_sync_peer(state.store, peer_id)
    except Exception:
        return json_error(404, "not_found", "peer not found")
    if not rbac.can_manage_org(state.store, state.current_user.id, p.org_id, rbac.ROLE_OWNER):
        return json_error(403, "forbidden", "enrolling a replication peer requires the owner role")
    sync_peers.delete_sync_peer(state.store, peer_id)
    return {"deleted": peer_id, "caveat": SYNC_CAVEAT}


@router.post("/peers/{peer_id}/sync")
def sync_peer_round(peer_id: str, state: AppState = Depends(require_user)):
    """Sync peer round."""
    try:
        p = sync_peers.get_sync_peer(state.store, peer_id)
    except Exception:
        return json_error(404, "not_found", "peer not found")
    if not rbac.can_manage_org(state.store, state.current_user.id, p.org_id, rbac.ROLE_OWNER):
        return json_error(403, "forbidden", "owner role required")
    if not p.url:
        return json_error(400, "invalid_request", "this peer has no address")
    return {
        "peer_id": peer_id,
        "status": "not_implemented",
        "message": "Outbound replication rounds are not implemented in backend-python yet",
        "caveat": SYNC_CAVEAT,
    }


def _peer_view(p: SyncPeer) -> dict:
    """Internal: peer view."""
    return {
        "id": p.id,
        "name": p.name,
        "url": p.url,
        "public_key": p.public_key,
        "enabled": p.enabled,
        "dialable": bool(p.url),
        "pull_cursor": p.pull_cursor,
        "push_cursor": p.push_cursor,
        "last_sync_at": p.last_sync_at.isoformat().replace("+00:00", "Z") if p.last_sync_at else None,
        "last_status": p.last_status,
        "created_at": p.created_at.isoformat().replace("+00:00", "Z"),
        "feed_publish": p.feed_publish,
        "feed_subscribe": p.feed_subscribe,
        "feed_pulled_at": p.feed_pulled_at.isoformat().replace("+00:00", "Z") if p.feed_pulled_at else None,
        "feed_status": p.feed_status,
    }


@peer_router.get("/peer-events")
def list_peer_events(org: str = Query(""), state: AppState = Depends(get_app_state)):
    """List peer events."""
    if not org:
        return json_error(400, "invalid_request", "org query parameter is required")
    return {"events": []}
