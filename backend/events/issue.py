"""Mint signed ticket capabilities after successful payment."""

from __future__ import annotations

from store import event_keys as event_keys_repo
from store.store import Store
from tickets import capability as cap


def issue_ticket(st: Store, event_id: str, payload: cap.Payload) -> tuple[str, str]:
    """Issue ticket."""
    key = event_keys_repo.latest_active_event_key(st, event_id)
    if key.private_key is None:
        raise RuntimeError("signing key unavailable (vault locked?)")
    kid = cap.key_id(key.public_key)
    payload.kid = kid
    token = cap.issue(payload, key.private_key)
    return token, kid


def issuer_public_keys(st: Store, event_id: str) -> cap.KeyRing:
    """Issuer public keys."""
    rows = event_keys_repo.active_event_keys(st, event_id)
    ring = cap.KeyRing.new(event_id)
    for k in rows:
        ring.add(cap.key_id(k.public_key), k.public_key)
    return ring
