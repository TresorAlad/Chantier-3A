"""Argon2id password hashing and verification (PHC string format)."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass

from argon2 import Type
from argon2.exceptions import VerifyMismatchError
from argon2.low_level import hash_secret_raw, verify_secret

_PHC_RE = re.compile(
    r"^\$argon2id\$v=(\d+)\$m=(\d+),t=(\d+),p=(\d+)\$([A-Za-z0-9+/]+)\$([A-Za-z0-9+/]+)$"
)


@dataclass
class _Params:
    """Internal: Params."""
    memory: int
    time: int
    threads: int


def hash_password(password: str) -> str:
    """Hash a plaintext password as an Argon2id PHC string."""
    salt = __import__("os").urandom(16)
    memory = 64 * 1024
    time_cost = 1
    parallelism = 4
    key_len = 32
    digest = hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=time_cost,
        memory_cost=memory,
        parallelism=parallelism,
        hash_len=key_len,
        type=Type.ID,
    )
    salt_b64 = base64.b64encode(salt).decode("ascii").rstrip("=")
    hash_b64 = base64.b64encode(digest).decode("ascii").rstrip("=")
    return f"$argon2id$v=19$m={memory},t={time_cost},p={parallelism}${salt_b64}${hash_b64}"


def _decode_hash(encoded: str) -> tuple[_Params, bytes, bytes]:
    """Internal: decode hash."""
    m = _PHC_RE.match(encoded)
    if not m:
        raise ValueError("invalid password hash")
    memory = int(m.group(2))
    time_cost = int(m.group(3))
    threads = int(m.group(4))
    def _pad(s: str) -> bytes:
        """Internal: pad."""
        pad = "=" * ((4 - len(s) % 4) % 4)
        return base64.b64decode(s + pad)

    salt = _pad(m.group(5))
    digest = _pad(m.group(6))
    return _Params(memory=memory, time=time_cost, threads=threads), salt, digest


def verify_password(encoded_hash: str, password: str) -> bool:
    """Return whether ``password`` matches the encoded Argon2id hash."""
    try:
        params, salt, expected = _decode_hash(encoded_hash)
    except ValueError:
        return False
    try:
        verify_secret(
            hash=expected,
            secret=password.encode("utf-8"),
            salt=salt,
            type=Type.ID,
            time_cost=params.time,
            memory_cost=params.memory,
            parallelism=params.threads,
        )
        return True
    except VerifyMismatchError:
        return False
