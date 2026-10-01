-- pg-only: PostgreSQL only; skipped by the SQLite test store (tests/sqlite_store.py).
-- Minimal participant data for the scanner screen (no e-mail, no school), served by /api/checkin/snapshot.
ALTER TABLE checkin_entitlements ADD COLUMN holder_name text NOT NULL DEFAULT '';
ALTER TABLE checkin_entitlements ADD COLUMN pass_type   text NOT NULL DEFAULT '';
