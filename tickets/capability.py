"""Ed25519-signed ticket capability tokens (QR payload); wire format matches Go and docs/TICKET-FORMAT.md."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

CURRENT_VERSION = 1
TOKEN_PREFIX = "cackle"


class CapabilityError(Exception):
    """Capabilityerror."""
    pass


class ErrMalformed(CapabilityError):
    """Errmalformed."""
    pass


class ErrUnsupportedVersion(CapabilityError):
    """Errunsupportedversion."""
    pass


class ErrBadSignature(CapabilityError):
    """Errbadsignature."""
    pass


class ErrNotYetValid(CapabilityError):
    """Errnotyetvalid."""
    pass


class ErrExpired(CapabilityError):
    """Errexpired."""
    pass


class ErrUnknownKID(CapabilityError):
    """Errunknownkid."""
    pass


@dataclass
class Payload:
    """Payload."""
    tid: str = ""
    eid: str = ""
    tt: str = ""
    kid: str = ""
    sub: str = ""
    name: str = ""
    iat: int = 0
    nbf: int = 0
    exp: int = 0
    seat: str = ""

    def to_wire_dict(self) -> dict:
        """To wire dict on ``Payload``."""
        out: dict = {
            "v": CURRENT_VERSION,
            "tid": self.tid,
            "eid": self.eid,
            "tt": self.tt,
            "kid": self.kid,
            "sub": self.sub,
            "nm": self.name,
            "iat": self.iat,
        }
        if self.nbf:
            out["nbf"] = self.nbf
        if self.exp:
            out["exp"] = self.exp
        if self.seat:
            out["seat"] = self.seat
        return out


@dataclass
class KeyRing:
    """Keyring."""
    event_id: str
    keys: dict[str, bytes]

    @classmethod
    def new(cls, event_id: str) -> KeyRing:
        """New on ``KeyRing``."""
        return KeyRing(event_id=event_id, keys={})

    def add(self, kid: str, pub: bytes) -> None:
        """Add on ``KeyRing``."""
        self.keys[kid] = pub

    def lookup(self, kid: str) -> bytes | None:
        """Lookup on ``KeyRing``."""
        return self.keys.get(kid)


def _marshal_payload_bytes(data: dict) -> bytes:
    """Match Go encoding/json HTML-safe escapes for &, <, > in string values."""
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    return (
        raw.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .encode()
    )


def key_id(pub: bytes) -> str:
    """Key id."""
    digest = hashlib.sha256(pub).digest()[:16]
    return "k_" + base64.urlsafe_b64encode(digest).decode().rstrip("=")


def issue(payload: Payload, priv_raw: bytes) -> str:
    """Issue."""
    if len(priv_raw) != 32:
        raise CapabilityError("invalid private key size")
    priv = Ed25519PrivateKey.from_private_bytes(priv_raw)
    body = _marshal_payload_bytes(payload.to_wire_dict())
    sig = priv.sign(body)
    enc_payload = base64.urlsafe_b64encode(body).decode().rstrip("=")
    enc_sig = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    return f"{TOKEN_PREFIX}.{enc_payload}.{enc_sig}"


def verify(token: str, pub_raw: bytes, now: datetime) -> Payload:
    """Verify."""
    if len(pub_raw) != 32:
        raise ErrMalformed("invalid public key size")
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != TOKEN_PREFIX:
        raise ErrMalformed("expected 3 dot-separated segments")
    for seg in (parts[1], parts[2]):
        if "=" in seg or "+" in seg or "/" in seg:
            raise ErrMalformed("non-raw base64url segment")
    try:
        body = base64.urlsafe_b64decode(parts[1] + "==")
        sig = base64.urlsafe_b64decode(parts[2] + "==")
    except Exception as err:
        raise ErrMalformed(f"base64: {err}") from err
    pub = Ed25519PublicKey.from_public_bytes(pub_raw)
    try:
        pub.verify(sig, body)
    except Exception as err:
        raise ErrBadSignature(str(err)) from err
    try:
        data = json.loads(body.decode())
    except json.JSONDecodeError as err:
        raise ErrMalformed(f"payload json: {err}") from err
    if not isinstance(data, dict):
        raise ErrMalformed("payload json: not an object")
    allowed = {"v", "tid", "eid", "tt", "kid", "sub", "nm", "iat", "nbf", "exp", "seat"}
    if extra := set(data) - allowed:
        raise ErrMalformed(f"payload json: unknown field {sorted(extra)[0]}")
    for num_key in ("v", "iat", "nbf", "exp"):
        if num_key in data and not isinstance(data[num_key], int):
            raise ErrMalformed(f"payload json: {num_key} must be a number")
    if data.get("v") != CURRENT_VERSION:
        raise ErrUnsupportedVersion(f"got version {data.get('v')}")
    p = Payload(
        tid=data.get("tid", ""),
        eid=data.get("eid", ""),
        tt=data.get("tt", ""),
        kid=data.get("kid", ""),
        sub=data.get("sub", ""),
        name=data.get("nm", ""),
        iat=int(data.get("iat", 0)),
        nbf=int(data.get("nbf", 0) or 0),
        exp=int(data.get("exp", 0) or 0),
        seat=data.get("seat", "") or "",
    )
    now_unix = int(now.timestamp())
    if p.nbf and now_unix < p.nbf:
        raise ErrNotYetValid()
    if p.exp and now_unix >= p.exp:
        raise ErrExpired()
    return p


def peek_kid(token: str) -> str:
    """Peek kid."""
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != TOKEN_PREFIX:
        raise ErrMalformed("bad token shape")
    body = base64.urlsafe_b64decode(parts[1] + "==")
    data = json.loads(body.decode())
    return data.get("kid", "")


def verify_with_ring(token: str, ring: KeyRing, now: datetime) -> Payload:
    """Verify with ring."""
    kid = peek_kid(token)
    pub = ring.lookup(kid)
    if pub is None:
        raise ErrUnknownKID(kid)
    return verify(token, pub, now)
