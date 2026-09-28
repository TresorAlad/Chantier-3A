"""Conformance tests against docs/pass-format-vectors.json (issue + verify)."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tickets import capability as cap

VECTORS = Path(__file__).resolve().parents[1] / "docs" / "pass-format-vectors.json"

ERROR_MAP = {
    "malformed": cap.ErrMalformed,
    "unsupported_version": cap.ErrUnsupportedVersion,
    "bad_signature": cap.ErrBadSignature,
    "not_yet_valid": cap.ErrNotYetValid,
    "expired": cap.ErrExpired,
    "unknown_kid": cap.ErrUnknownKID,
}


@pytest.fixture(scope="module")
def vectors():
    """Vectors."""
    data = json.loads(VECTORS.read_text(encoding="utf-8"))
    assert data["format"] == "chantier3a-capability-token"
    assert data["payload_version"] == cap.CURRENT_VERSION
    return data


def test_issue_vectors(vectors):
    """Test issue vectors."""
    issuer = vectors["keys"]["issuer"]
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    seed = bytes.fromhex(issuer["seed_hex"])
    priv = Ed25519PrivateKey.from_private_bytes(seed)
    priv_raw = priv.private_bytes_raw()
    pub = priv.public_key().public_bytes_raw()
    assert base64.urlsafe_b64encode(pub).decode().rstrip("=") == issuer["public_key_b64url"]
    assert cap.key_id(pub) == issuer["kid"]
    for vec in vectors["issue"]:
        raw = vec["payload"]
        payload = cap.Payload(
            tid=raw.get("tid", ""),
            ref=raw.get("ref", ""),
            eid=raw.get("eid", ""),
            tt=raw.get("tt", ""),
            kid=raw.get("kid") or issuer["kid"],
            sub=raw.get("sub", ""),
            name=raw.get("nm", ""),
            iat=int(raw.get("iat", 0)),
            nbf=int(raw.get("nbf", 0) or 0),
            exp=int(raw.get("exp", 0) or 0),
            seat=raw.get("seat", "") or "",
        )
        token = cap.issue(payload, priv_raw)
        assert token == vec["token"]


def test_verify_vectors(vectors):
    """Test verify vectors."""
    keys = vectors["keys"]
    for vec in vectors["verify"]:
        pub = base64.urlsafe_b64decode(keys[vec["key"]]["public_key_b64url"] + "==")
        now = datetime.fromtimestamp(vec["now_unix"], tz=timezone.utc)
        if vec["result"] == "ok":
            got = cap.verify(vec["token"], pub, now)
            assert got.tid == vec.get("tid", got.tid)
            continue
        if vec.get("error") == "unknown_kid":
            ring = cap.KeyRing.new("e")
            with pytest.raises(cap.ErrUnknownKID):
                cap.verify_with_ring(vec["token"], ring, now)
            continue
        with pytest.raises(cap.CapabilityError):
            cap.verify(vec["token"], pub, now)
