"""Peer request/response authentication (ported from backend/internal/scan/substrate/peerauth.go)."""

from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass, field

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

HEADER_KEY = "X-Chantier3A-Node"
HEADER_TIMESTAMP = "X-Chantier3A-Timestamp"
HEADER_NONCE = "X-Chantier3A-Nonce"
HEADER_SIG = "X-Chantier3A-Sig"

MAX_CLOCK_SKEW_SEC = 5 * 60

REQUEST_DOMAIN = "chantier3a-sync-request-v1"
RESPONSE_DOMAIN = "chantier3a-sync-response-v1"


class ErrUnsigned(Exception):
    """Errunsigned."""
    pass


def body_hash(body: bytes) -> str:
    """Body hash."""
    return hashlib.sha256(body).hexdigest()


def request_sig_base(method: str, path: str, raw_query: str, body_hash_hex: str, ts: str, nonce: str) -> bytes:
    """Request sig base."""
    return "\n".join([REQUEST_DOMAIN, method, path, raw_query, body_hash_hex, ts, nonce]).encode()


def response_sig_base(request_nonce: str, body_hash_hex: str, ts: str) -> bytes:
    """Response sig base."""
    return "\n".join([RESPONSE_DOMAIN, request_nonce, body_hash_hex, ts]).encode()


def normalize_key(key: str) -> str:
    """Normalize key."""
    key = (key or "").strip().lower()
    if len(key) != 64:
        raise ValueError("node key must be 32-byte hex")
    int(key, 16)
    return key


def presented_key(headers: dict) -> str:
    """Presented key."""
    try:
        return normalize_key(headers.get(HEADER_KEY) or headers.get(HEADER_KEY.lower()) or "")
    except ValueError:
        return ""


def new_nonce() -> str:
    """New nonce."""
    return secrets.token_hex(16)


@dataclass
class NonceCache:
    """Noncecache."""
    seen: dict[str, float] = field(default_factory=dict)

    def check_and_add(self, key: str, now: float) -> bool:
        """Check and add on ``NonceCache``."""
        ttl = 2 * MAX_CLOCK_SKEW_SEC
        expired = [k for k, exp in self.seen.items() if now > exp]
        for k in expired:
            del self.seen[k]
        if key in self.seen and now < self.seen[key]:
            return False
        self.seen[key] = now + ttl
        return True


def _verify_sig(pub_hex: str, base: bytes, sig_hex: str) -> None:
    """Internal: verify sig."""
    pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex))
    sig = bytes.fromhex(sig_hex)
    pub.verify(sig, base)


def verify_request(
    method: str,
    path: str,
    raw_query: str,
    headers: dict,
    body: bytes,
    want_key: str,
    nonces: NonceCache | None,
    now: float | None = None,
) -> None:
    """Verify request."""
    now = now if now is not None else time.time()
    key = headers.get(HEADER_KEY) or ""
    ts = headers.get(HEADER_TIMESTAMP) or ""
    nonce = headers.get(HEADER_NONCE) or ""
    sig = headers.get(HEADER_SIG) or ""
    if not key or not ts or not nonce or not sig:
        raise ErrUnsigned()
    presented = normalize_key(key)
    pinned = normalize_key(want_key)
    if presented != pinned:
        raise ValueError("request signed by wrong key")
    ts_int = int(ts)
    if abs(now - ts_int) > MAX_CLOCK_SKEW_SEC:
        raise ValueError("request timestamp outside allowed skew")
    base = request_sig_base(method, path, raw_query, body_hash(body), ts, nonce)
    _verify_sig(pinned, base, sig)
    if nonces is not None and not nonces.check_and_add(f"{pinned}|{nonce}", now):
        raise ValueError("replayed request nonce")


def sign_response_headers(
    headers: dict,
    priv_raw: bytes,
    request_nonce: str,
    body: bytes,
    now: float | None = None,
) -> None:
    """Sign response headers."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    now = now if now is not None else time.time()
    ts = str(int(now))
    base = response_sig_base(request_nonce, body_hash(body), ts)
    priv = Ed25519PrivateKey.from_private_bytes(priv_raw)
    sig = priv.sign(base)
    pub = priv.public_key().public_bytes_raw().hex()
    headers[HEADER_KEY] = pub
    headers[HEADER_TIMESTAMP] = ts
    headers[HEADER_NONCE] = request_nonce
    headers[HEADER_SIG] = sig.hex()
