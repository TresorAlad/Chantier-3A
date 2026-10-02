"""A ticket has exactly one QR string: non-canonical base64url encodings are refused."""

from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tickets import capability as cap

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def _token_and_pub():
    priv = Ed25519PrivateKey.generate()
    raw = priv.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    pub = priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    now = int(datetime.now(timezone.utc).timestamp())
    payload = cap.Payload(tid="t1", ref="TDEV-2026-0001", eid="e1", tt="tt1", kid=cap.key_id(pub), sub="", name="N",
                          iat=now, nbf=now - 10, exp=now + 3600)
    return cap.issue(payload, raw), pub


def test_canonical_token_verifies():
    token, pub = _token_and_pub()
    assert cap.verify(token, pub, datetime.now(timezone.utc)).tid == "t1"


def test_same_signature_with_other_trailing_bits_is_refused():
    token, pub = _token_and_pub()
    head, body, sig = token.split(".")
    # the last char of an 86-char signature carries 4 unused bits: change them, the decoded bytes stay identical
    last = ALPHABET.index(sig[-1])
    variant = ALPHABET[last ^ 1]
    forged = ".".join([head, body, sig[:-1] + variant])
    with pytest.raises(cap.ErrMalformed):
        cap.verify(forged, pub, datetime.now(timezone.utc))
