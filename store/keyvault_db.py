"""Unlock and persist the org key vault using configured key material."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

from store import keyvault_crypto as kv
from store.store import Store
from store.timeutil import text_to_time, time_to_text

DEK_ROW_ID = "dek"
ErrKeyVaultLocked = Exception("store: event key vault is locked")


@dataclass
class _DEKRow:
    """Internal: DEKRow."""
    wrapped: bytes
    nonce: bytes
    source_kind: str
    kdf: str
    salt: bytes
    argon_time: int
    argon_memory: int
    argon_lanes: int


def unlock_key_vault(st: Store, src: kv.Source, *, demo: bool = False) -> None:
    """Unlock key vault."""
    if not src.valid():
        raise kv.ErrNoSource()
    row = _load_dek_row(st)
    if row is None:
        params = kv.new_kdf_params(src.kind)
        dek = kv.generate_dek()
        kek = kv.derive_kek(src, params)
        wrapped, nonce = kv.seal(kek, kv.DEK_AAD, dek)
        now = time_to_text(datetime.now(timezone.utc))
        st.execute(
            """
            INSERT INTO key_vault (
                id, wrapped_key, nonce, kdf, salt,
                argon_time, argon_memory, argon_lanes, source_kind, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                DEK_ROW_ID,
                wrapped,
                nonce,
                params.name,
                params.salt,
                params.time if params.name == kv.KDF_ARGON2ID else 0,
                params.memory if params.name == kv.KDF_ARGON2ID else 0,
                params.lanes if params.name == kv.KDF_ARGON2ID else 0,
                src.kind,
                now,
            ),
        )
        st._vault = kv.Vault(dek, src.kind)  # type: ignore[attr-defined]
        return

    if demo and row.source_kind != kv.KIND_DEMO:
        raise kv.ErrWrongKey("demo mode cannot unlock a non-demo vault")
    if not demo and row.source_kind == kv.KIND_DEMO and src.kind != kv.KIND_DEMO:
        raise kv.ErrWrongKey("non-demo source cannot unlock a demo vault")

    params = kv.KDFParams(
        row.kdf,
        row.salt,
        time=row.argon_time or 3,
        memory=row.argon_memory or 64 * 1024,
        lanes=row.argon_lanes or 4,
    )
    kek = kv.derive_kek(src, params)
    dek = kv.open_box(kek, kv.DEK_AAD, row.nonce, row.wrapped)
    st._vault = kv.Vault(dek, src.kind)  # type: ignore[attr-defined]


def key_vault_unlocked(st: Store) -> bool:
    """Key vault unlocked."""
    return getattr(st, "_vault", None) is not None


def _load_dek_row(st: Store) -> _DEKRow | None:
    """Internal: load dek row."""
    row = st.fetchone(
        """
        SELECT wrapped_key, nonce, source_kind, kdf, salt,
               argon_time, argon_memory, argon_lanes
        FROM key_vault WHERE id = ?
        """,
        (DEK_ROW_ID,),
    )
    if row is None:
        return None

    def g(i: int, key: str | None = None):
        """G."""
        if hasattr(row, "keys"):
            return row[key or i]
        return row[i]

    return _DEKRow(
        wrapped=bytes(g(0, "wrapped_key")),
        nonce=bytes(g(1, "nonce")),
        source_kind=g(2, "source_kind"),
        kdf=g(3, "kdf"),
        salt=bytes(g(4, "salt")),
        argon_time=int(g(5, "argon_time") or 0),
        argon_memory=int(g(6, "argon_memory") or 0),
        argon_lanes=int(g(7, "argon_lanes") or 0),
    )


def seal_private_key(st: Store, key_id: str, event_id: str, priv: bytes) -> tuple[bytes, bytes]:
    """Seal private key."""
    vault: kv.Vault | None = getattr(st, "_vault", None)
    if vault is None:
        raise ErrKeyVaultLocked()
    return vault.seal(kv.event_key_aad(key_id, event_id), priv)


def open_private_key(
    st: Store, key_id: str, event_id: str, sealed: bytes, nonce: bytes
) -> bytes:
    """Open private key."""
    vault: kv.Vault | None = getattr(st, "_vault", None)
    if vault is None:
        raise ErrKeyVaultLocked()
    return vault.open(kv.event_key_aad(key_id, event_id), nonce, sealed)
