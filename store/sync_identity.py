"""This node's sync identity keys and host metadata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from store.store import Store
from store.timeutil import text_to_time, time_to_text


@dataclass
class NodeIdentity:
    """Nodeidentity."""
    public_key: str
    private_key: bytes
    created_at: datetime


def ensure_node_identity(st: Store) -> NodeIdentity:
    """Ensure node identity."""
    row = st.fetchone(
        "SELECT public_key, private_key, created_at FROM sync_node_identity WHERE id = 1"
    )
    if row is not None:
        if hasattr(row, "keys"):
            return NodeIdentity(
                public_key=row["public_key"],
                private_key=bytes(row["private_key"]),
                created_at=text_to_time(row["created_at"]),
            )
        return NodeIdentity(
            public_key=row[0],
            private_key=bytes(row[1]),
            created_at=text_to_time(row[2]),
        )
    priv = Ed25519PrivateKey.generate()
    priv_raw = priv.private_bytes_raw()
    pub_hex = priv.public_key().public_bytes_raw().hex()
    now = datetime.now(timezone.utc)
    st.execute(
        """
        INSERT INTO sync_node_identity (id, public_key, private_key, created_at)
        VALUES (1, ?, ?, ?)
        """,
        (pub_hex, priv_raw, time_to_text(now)),
    )
    return NodeIdentity(public_key=pub_hex, private_key=priv_raw, created_at=now)
