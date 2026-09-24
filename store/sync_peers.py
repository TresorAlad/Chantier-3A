"""Registered peer nodes for multi-host event replication."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from store.store import NotFoundError, Store, new_ulid
from store.timeutil import text_to_null_time, text_to_time, time_to_text


@dataclass
class SyncPeer:
    """Syncpeer."""
    id: str
    org_id: str
    name: str
    url: str
    public_key: str
    enabled: bool
    pull_cursor: int
    push_cursor: int
    last_sync_at: datetime | None
    last_status: str
    created_at: datetime
    feed_publish: bool = False
    feed_subscribe: bool = False
    feed_pulled_at: datetime | None = None
    feed_status: str = ""


def normalize_node_key(key: str) -> str:
    """Normalize node key."""
    key = (key or "").strip().lower()
    if len(key) != 64:
        raise ValueError("public_key must be a 32-byte hex Ed25519 key")
    int(key, 16)
    return key


def create_sync_peer(st: Store, p: SyncPeer) -> None:
    """Create sync peer."""
    p.public_key = normalize_node_key(p.public_key)
    if not p.id:
        p.id = new_ulid()
    st.execute(
        """
        INSERT INTO sync_peer (
            id, org_id, name, url, public_key, enabled,
            pull_cursor, push_cursor, last_sync_at, last_status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, 0, 0, '', ?, ?)
        """,
        (
            p.id,
            p.org_id,
            p.name,
            p.url,
            p.public_key,
            1 if p.enabled else 0,
            p.last_status,
            time_to_text(p.created_at),
        ),
    )


def list_sync_peers(st: Store, org_id: str) -> list[SyncPeer]:
    """List sync peers."""
    rows = st.fetchall(
        """
        SELECT id, org_id, name, url, public_key, enabled, pull_cursor, push_cursor,
               last_sync_at, last_status, created_at, feed_publish, feed_subscribe,
               feed_pulled_at, feed_status
        FROM sync_peer WHERE org_id = ? ORDER BY created_at ASC
        """,
        (org_id,),
    )
    return [_row_peer(r) for r in rows]


def enabled_sync_peers_by_key(st: Store, public_key: str) -> list[SyncPeer]:
    """Enabled sync peers by key."""
    key = normalize_node_key(public_key)
    rows = st.fetchall(
        """
        SELECT id, org_id, name, url, public_key, enabled, pull_cursor, push_cursor,
               last_sync_at, last_status, created_at, feed_publish, feed_subscribe,
               feed_pulled_at, feed_status
        FROM sync_peer WHERE public_key = ? AND enabled = 1
        """,
        (key,),
    )
    return [_row_peer(r) for r in rows]


def get_sync_peer(st: Store, peer_id: str) -> SyncPeer:
    """Get sync peer."""
    row = st.fetchone(
        """
        SELECT id, org_id, name, url, public_key, enabled, pull_cursor, push_cursor,
               last_sync_at, last_status, created_at, feed_publish, feed_subscribe,
               feed_pulled_at, feed_status
        FROM sync_peer WHERE id = ?
        """,
        (peer_id,),
    )
    if row is None:
        raise NotFoundError()
    return _row_peer(row)


def delete_sync_peer(st: Store, peer_id: str) -> None:
    """Delete sync peer."""
    n = st.execute_rowcount("DELETE FROM sync_peer WHERE id = ?", (peer_id,))
    if n == 0:
        raise NotFoundError()


def set_peer_feed_flags(st: Store, peer_id: str, subscribe: bool, publish: bool) -> None:
    """Set peer feed flags."""
    get_sync_peer(st, peer_id)
    st.execute(
        """
        UPDATE sync_peer SET feed_subscribe = ?, feed_publish = ?
        WHERE id = ?
        """,
        (1 if subscribe else 0, 1 if publish else 0, peer_id),
    )


def _row_peer(row) -> SyncPeer:
    """Internal: row peer."""
    if hasattr(row, "keys"):
        return SyncPeer(
            id=row["id"],
            org_id=row["org_id"],
            name=row["name"] or "",
            url=row["url"] or "",
            public_key=row["public_key"],
            enabled=bool(row["enabled"]),
            pull_cursor=int(row["pull_cursor"]),
            push_cursor=int(row["push_cursor"]),
            last_sync_at=text_to_null_time(row["last_sync_at"]) if row["last_sync_at"] else None,
            last_status=row["last_status"] or "",
            created_at=text_to_time(row["created_at"]),
            feed_publish=bool(row["feed_publish"]),
            feed_subscribe=bool(row["feed_subscribe"]),
            feed_pulled_at=text_to_null_time(row["feed_pulled_at"]),
            feed_status=row["feed_status"] or "",
        )
    return SyncPeer(
        id=row[0],
        org_id=row[1],
        name=row[2] or "",
        url=row[3] or "",
        public_key=row[4],
        enabled=bool(row[5]),
        pull_cursor=int(row[6]),
        push_cursor=int(row[7]),
        last_sync_at=text_to_null_time(row[8]) if row[8] else None,
        last_status=row[9] or "",
        created_at=text_to_time(row[10]),
        feed_publish=bool(row[11]),
        feed_subscribe=bool(row[12]),
        feed_pulled_at=text_to_null_time(row[13]),
        feed_status=row[14] or "",
    )
