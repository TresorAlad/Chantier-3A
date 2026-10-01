"""Ed25519 signature of the snapshot (the offline cache must be provably the server's).

The signing key is dedicated to the snapshot: it is *not* an event issuer key (those only verify in this
module). The app pins the public key (``GET /api/checkin/signing-key``) and checks every page before storing it.
The signature covers the exact bytes of the uncompressed response body, so there is nothing to re-canonicalise.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass, field

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ALGORITHM = "Ed25519"
HEADER = "X-Checkin-Signature"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64url(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


@dataclass(frozen=True)
class SnapshotSigner:
    """Signs snapshot pages with a 32-byte Ed25519 seed (base64url in ``CHECKIN_SNAPSHOT_SIGNING_KEY``)."""

    seed: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if len(self.seed) != 32:
            raise ValueError("snapshot signing key must be a base64url 32-byte Ed25519 seed")

    @classmethod
    def from_text(cls, text: str) -> SnapshotSigner:
        """Build from the environment value; raises ``ValueError`` when it is not a 32-byte seed."""
        try:
            return cls(_unb64url(text.strip()))
        except Exception as err:  # binascii.Error, ValueError
            raise ValueError("snapshot signing key must be a base64url 32-byte Ed25519 seed") from err

    @classmethod
    def generate(cls) -> SnapshotSigner:
        """Fresh random signer (tests, ``python -m checkin.signing``)."""
        return cls(secrets.token_bytes(32))

    @property
    def _key(self) -> Ed25519PrivateKey:
        return Ed25519PrivateKey.from_private_bytes(self.seed)

    @property
    def public_key(self) -> bytes:
        """Raw 32-byte public key."""
        return self._key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)

    @property
    def kid(self) -> str:
        """Key id: first 10 characters of the base64url SHA-256 of the public key."""
        return "snap_" + _b64url(hashlib.sha256(self.public_key).digest())[:10]

    def sign(self, body: bytes) -> str:
        """Header value ``Ed25519; kid=...; sig=...`` for the exact ``body`` bytes."""
        return f"{ALGORITHM}; kid={self.kid}; sig={_b64url(self._key.sign(body))}"

    def describe(self) -> dict:
        """Public description served to the app so it can pin the key."""
        return {"algorithm": ALGORITHM, "kid": self.kid, "public_key": _b64url(self.public_key)}


if __name__ == "__main__":  # python -m checkin.signing  -> new key pair
    new = SnapshotSigner.generate()
    print("CHECKIN_SNAPSHOT_SIGNING_KEY=" + _b64url(new.seed))
    print("# public key to pin in the app:", new.describe())
