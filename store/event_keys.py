"""Per-event Ed25519 signing keys for ticket capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from store import keyvault_db
from store.store import NotFoundError, Store, new_ulid
from store.timeutil import text_to_null_time, text_to_time, time_to_text
@dataclass
class EventKey:
    """Eventkey."""
    id: str
    event_id: str
    public_key: bytes
    private_key: bytes | None
    created_at: datetime
    revoked_at: datetime | None = None


def create_event_with_key(
    st: Store,
    event_row: dict,
    pub: bytes,
    priv: bytes,
) -> None:
    """Create event with key."""
    key_id_val = new_ulid()
    sealed, nonce = keyvault_db.seal_private_key(st, key_id_val, event_row["id"], priv)
    now = time_to_text(datetime.now(timezone.utc))
    st.execute(
        """
        INSERT INTO events (
            id, org_id, slug, title, summary, description, venue_name, address,
            lat, lng, starts_at, ends_at, timezone, cover_image, status, currency,
            category, cover_image_id, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_row["id"],
            event_row["org_id"],
            event_row["slug"],
            event_row["title"],
            event_row.get("summary", ""),
            event_row.get("description", ""),
            event_row.get("venue_name", ""),
            event_row.get("address", ""),
            event_row.get("lat"),
            event_row.get("lng"),
            event_row["starts_at"],
            event_row["ends_at"],
            event_row.get("timezone", "UTC"),
            event_row.get("cover_image", ""),
            event_row.get("status", "draft"),
            event_row["currency"],
            event_row.get("category", ""),
            event_row.get("cover_image_id"),
            now,
            now,
        ),
    )
    st.execute(
        """
        INSERT INTO event_keys (id, event_id, public_key, sealed_private_key, sealed_nonce, created_at, revoked_at)
        VALUES (?, ?, ?, ?, ?, ?, NULL)
        """,
        (key_id_val, event_row["id"], pub, sealed, nonce, now),
    )


def latest_active_event_key(st: Store, event_id: str) -> EventKey:
    """Latest active event key."""
    row = st.fetchone(
        """
        SELECT id, event_id, public_key, sealed_private_key, sealed_nonce, created_at, revoked_at
        FROM event_keys
        WHERE event_id = ? AND revoked_at IS NULL
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (event_id,),
    )
    if row is None:
        raise NotFoundError()
    return _hydrate_key(st, row, with_private=True)


def active_event_keys(st: Store, event_id: str) -> list[EventKey]:
    """Active event keys."""
    rows = st.fetchall(
        """
        SELECT id, event_id, public_key, sealed_private_key, sealed_nonce, created_at, revoked_at
        FROM event_keys
        WHERE event_id = ? AND revoked_at IS NULL
        ORDER BY created_at ASC, id ASC
        """,
        (event_id,),
    )
    return [_hydrate_key(st, r, with_private=False) for r in rows]


def _hydrate_key(st: Store, row, *, with_private: bool) -> EventKey:
    """Internal: hydrate key."""
    if hasattr(row, "keys"):
        kid = row["id"]
        event_id = row["event_id"]
        pub = bytes(row["public_key"])
        sealed = bytes(row["sealed_private_key"])
        nonce = bytes(row["sealed_nonce"])
        created = text_to_time(row["created_at"])
        revoked = text_to_null_time(row["revoked_at"])
    else:
        kid, event_id, pub, sealed, nonce = row[0], row[1], bytes(row[2]), bytes(row[3]), bytes(row[4])
        created = text_to_time(row[5])
        revoked = text_to_null_time(row[6])

    priv: bytes | None = None
    if with_private:
        priv = keyvault_db.open_private_key(st, kid, event_id, sealed, nonce)
    return EventKey(
        id=kid,
        event_id=event_id,
        public_key=pub,
        private_key=priv,
        created_at=created,
        revoked_at=revoked,
    )


def generate_ed25519_keypair() -> tuple[bytes, bytes]:
    """Generate ed25519 keypair."""
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key().public_bytes_raw()
    priv_raw = priv.private_bytes_raw()
    return pub, priv_raw
