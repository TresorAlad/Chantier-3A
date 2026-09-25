-- Encrypt event signing keys at rest.
--
-- What was wrong
-- ──────────────
-- `event_keys.private_key` was a PLAINTEXT BLOB in the SQLite file. Every
-- event's Ed25519 issuer private key sat in the clear, in the one file an
-- operator is told to back up. Whoever obtained a copy could mint tickets
-- that verify perfectly for every event in it, forever, and no gate could
-- tell — the forgery carries a real signature from the real key. On a cloud
-- node that is one over-broad backup, one snapshot of a decommissioned
-- volume, or one misconfigured static-file route away.
--
-- This migration moves the private half under envelope encryption keyed by
-- material the operator supplies at boot (passphrase or keyfile) and which is
-- never stored in the database. See internal/store/keyvault.
--
-- Two-phase, and why
-- ──────────────────
-- Re-encrypting existing rows is not expressible in SQL — it needs Argon2id
-- and an AEAD. So this file does only the SCHEMA half, leaving each existing
-- row's plaintext parked in `legacy_private_key`, and the DATA half runs in
-- Go: store.SealLegacyEventKeys, invoked from legacy Go cmd at boot once the
-- vault is unlocked. That function is idempotent (it only touches rows where
-- legacy_private_key IS NOT NULL) and it NULLs the plaintext in the same
-- transaction that writes the ciphertext, so a crash mid-migration can leave
-- a row sealed or unsealed but never both and never neither.
--
-- If a database still has legacy rows and no key material is configured,
-- legacy Go cmd REFUSES TO START and says what to set. It does not half-migrate,
-- and it does not keep serving from plaintext.
--
-- The CHECK constraint is the load-bearing part
-- ────────────────────────────────────────────
-- Exactly one of {sealed, legacy} must be present on every row. That makes
-- three bad states unrepresentable rather than merely unlikely:
--
--   * a sealed row that ALSO still carries plaintext (a migration that
--     "encrypted" the key and forgot to remove the original — the failure
--     mode this whole exercise exists to prevent),
--   * a row with neither, i.e. an event whose key silently vanished,
--   * a row with ciphertext but no nonce, which would be undecryptable.
--
-- After store.SealLegacyEventKeys has run there is no row with a non-NULL
-- legacy_private_key, and the insert path in internal/store/event_keys.go has
-- no code that writes that column at all — it is only ever read and cleared.
--
-- Residue, stated honestly
-- ────────────────────────
-- Rewriting the table frees the pages the old plaintext lived on; freed pages
-- are not scrubbed. store.SealLegacyEventKeys therefore checkpoints the WAL
-- and VACUUMs after committing, which rebuilds the file without them. What
-- that CANNOT do is reach copies that already left: every backup, snapshot
-- and replica taken before this migration still contains plaintext keys.
-- Treat them as key material — see docs/SELF-HOSTING.md.

CREATE TABLE key_vault (
    -- Single row, id = 'dek'. Present only once a vault has been
    -- initialised; a database with no key_vault row has never had key
    -- material configured.
    id           TEXT PRIMARY KEY,
    -- The data-encryption key, wrapped under the KEK derived from operator
    -- material. Ciphertext only; the KEK is never stored anywhere.
    wrapped_key  BLOB NOT NULL,
    nonce        BLOB NOT NULL,
    -- KDF used to turn operator material into the KEK, with its (non-secret)
    -- salt and cost parameters — the same reason a password hash stores its
    -- own salt and cost.
    kdf          TEXT NOT NULL,
    salt         BLOB NOT NULL,
    argon_time   INTEGER NOT NULL DEFAULT 0,
    argon_memory INTEGER NOT NULL DEFAULT 0,
    argon_lanes  INTEGER NOT NULL DEFAULT 0,
    -- 'passphrase' | 'keyfile' | 'demo'. Recorded so a boot with the wrong
    -- KIND of material fails with a useful message instead of a generic
    -- authentication failure, and so a database sealed with `--demo`'s
    -- public key can be recognised and refused in a real deployment.
    source_kind  TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    rotated_at   TEXT
);

-- SQLite cannot drop NOT NULL or add a CHECK in place, so event_keys is
-- rebuilt. Nothing references event_keys as a foreign-key parent (it is a
-- child of events), so the rebuild needs no reference rewriting.
CREATE TABLE event_keys_sealed (
    id                 TEXT PRIMARY KEY,
    event_id           TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    -- The public half stays in the clear: it is not secret, it is what gates
    -- pin, and keeping it readable without the vault is what lets a scan
    -- bundle be built by a process that holds no key material at all.
    public_key         BLOB NOT NULL,
    sealed_private_key BLOB,
    sealed_nonce       BLOB,
    -- Plaintext parked here by this migration, cleared by
    -- store.SealLegacyEventKeys. Always NULL on a fully-migrated database.
    legacy_private_key BLOB,
    created_at         TEXT NOT NULL,
    revoked_at         TEXT,
    CHECK (
        (sealed_private_key IS NOT NULL AND sealed_nonce IS NOT NULL AND legacy_private_key IS NULL)
        OR
        (sealed_private_key IS NULL AND sealed_nonce IS NULL AND legacy_private_key IS NOT NULL)
    )
);

INSERT INTO event_keys_sealed
    (id, event_id, public_key, sealed_private_key, sealed_nonce, legacy_private_key, created_at, revoked_at)
SELECT id, event_id, public_key, NULL, NULL, private_key, created_at, revoked_at
FROM event_keys;

DROP TABLE event_keys;
ALTER TABLE event_keys_sealed RENAME TO event_keys;

CREATE INDEX idx_event_keys_event_id ON event_keys(event_id);
-- Lets the boot-time "is anything still plaintext?" check be an index probe
-- rather than a scan of every key in the database.
CREATE INDEX idx_event_keys_legacy ON event_keys(id) WHERE legacy_private_key IS NOT NULL;
