"""XChaCha20-Poly1305 key vault crypto (ported from Go keyvault)."""

from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass

from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

try:
    from cryptography.hazmat.primitives.ciphers.aead import XChaCha20Poly1305 as _XChaChaAEAD
except ImportError:  # pragma: no cover - wheel without XChaCha (use PyNaCl)
    _XChaChaAEAD = None

KIND_PASSPHRASE = "passphrase"
KIND_KEYFILE = "keyfile"
KIND_DEMO = "demo"
KDF_ARGON2ID = "argon2id"
KDF_HKDF = "hkdf-sha256"
MIN_PASSPHRASE_RUNES = 12
KEY_LEN = 32
SALT_LEN = 16
DEK_AAD = b"chantier3a.keyvault.dek.v1"
HKDF_INFO = b"chantier3a.keyvault.kek.v1"
DEMO_MATERIAL = b"chantier3a-demo-vault-not-secret-v1"


class KeyVaultError(Exception):
    """Keyvaulterror."""
    pass


class ErrNoSource(KeyVaultError):
    """Errnosource."""
    pass


class ErrWeakSource(KeyVaultError):
    """Errweaksource."""
    pass


class ErrWrongKey(KeyVaultError):
    """Errwrongkey."""
    pass


@dataclass
class KDFParams:
    """Kdfparams."""
    name: str
    salt: bytes
    time: int = 3
    memory: int = 64 * 1024
    lanes: int = 4


@dataclass
class Source:
    """Source."""
    kind: str
    material: bytes

    @staticmethod
    def passphrase(p: str) -> Source:
        """Passphrase on ``Source``."""
        p = p.strip()
        if not p:
            raise ErrNoSource("passphrase is empty")
        if len(p) < MIN_PASSPHRASE_RUNES:
            raise ErrWeakSource(
                f"passphrase is {len(p)} characters, need at least {MIN_PASSPHRASE_RUNES}"
            )
        return Source(KIND_PASSPHRASE, p.encode())

    @staticmethod
    def demo() -> Source:
        """Demo on ``Source``."""
        return Source(KIND_DEMO, DEMO_MATERIAL)

    def valid(self) -> bool:
        """Valid on ``Source``."""
        return bool(self.kind and self.material)


def new_kdf_params(kind: str) -> KDFParams:
    """New kdf params."""
    salt = secrets.token_bytes(SALT_LEN)
    if kind == KIND_PASSPHRASE:
        return KDFParams(KDF_ARGON2ID, salt, time=3, memory=64 * 1024, lanes=4)
    if kind in (KIND_KEYFILE, KIND_DEMO):
        return KDFParams(KDF_HKDF, salt)
    raise KeyVaultError(f"unknown source kind {kind}")


def derive_kek(src: Source, params: KDFParams) -> bytes:
    """Derive kek."""
    if not src.valid():
        raise ErrNoSource()
    if not params.salt:
        raise KeyVaultError("KDF params have no salt")
    if params.name == KDF_ARGON2ID:
        return hash_secret_raw(
            secret=src.material,
            salt=params.salt,
            time_cost=params.time,
            memory_cost=params.memory,
            parallelism=params.lanes,
            hash_len=KEY_LEN,
            type=Type.ID,
        )
    if params.name == KDF_HKDF:
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=KEY_LEN,
            salt=params.salt,
            info=HKDF_INFO,
        )
        return hkdf.derive(src.material)
    raise KeyVaultError(f"unknown kdf {params.name}")


def generate_dek() -> bytes:
    """Generate dek."""
    return os.urandom(KEY_LEN)


XCHACHA_NONCE_SIZE = 24


def _xchacha_encrypt(key: bytes, nonce: bytes, plaintext: bytes, aad: bytes) -> bytes:
    """Internal: xchacha encrypt."""
    if _XChaChaAEAD is not None:
        return _XChaChaAEAD(key).encrypt(nonce, plaintext, aad)
    from nacl.bindings import crypto_aead_xchacha20poly1305_ietf_encrypt

    return crypto_aead_xchacha20poly1305_ietf_encrypt(plaintext, aad, nonce, key)


def _xchacha_decrypt(key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes) -> bytes:
    """Internal: xchacha decrypt."""
    if _XChaChaAEAD is not None:
        return _XChaChaAEAD(key).decrypt(nonce, ciphertext, aad)
    from nacl.bindings import crypto_aead_xchacha20poly1305_ietf_decrypt

    return crypto_aead_xchacha20poly1305_ietf_decrypt(ciphertext, aad, nonce, key)


def seal(key: bytes, aad: bytes, plaintext: bytes) -> tuple[bytes, bytes]:
    """Seal."""
    nonce = os.urandom(XCHACHA_NONCE_SIZE)
    ct = _xchacha_encrypt(key, nonce, plaintext, aad)
    return ct, nonce


def open_box(key: bytes, aad: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
    """Open box."""
    if len(nonce) != XCHACHA_NONCE_SIZE:
        raise ErrWrongKey(f"nonce is {len(nonce)} bytes, want {XCHACHA_NONCE_SIZE}")
    try:
        return _xchacha_decrypt(key, nonce, ciphertext, aad)
    except Exception as err:
        raise ErrWrongKey(str(err)) from err


@dataclass
class Vault:
    """Vault."""
    dek: bytes
    kind: str

    def seal(self, aad: bytes, plaintext: bytes) -> tuple[bytes, bytes]:
        """Seal on ``Vault``."""
        return seal(self.dek, aad, plaintext)

    def open(self, aad: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
        """Open on ``Vault``."""
        return open_box(self.dek, aad, nonce, ciphertext)


def event_key_aad(key_id: str, event_id: str) -> bytes:
    """Event key aad."""
    return f"chantier3a.event_key.v1|{key_id}|{event_id}".encode()
