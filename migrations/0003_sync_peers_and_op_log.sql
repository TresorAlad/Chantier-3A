-- Server-to-server replication of the admission ledger: the pinned peer set,
-- the durable op log, and this node's own identity.
--
-- What this makes possible, and what it deliberately does not
-- ──────────────────────────────────────────────────────────
-- Before this migration two Chantier 3A instances exchanged NOTHING. The admission
-- ledger converged between GATES and a server (`POST /api/scan/sync` up,
-- `scan-bundle`'s admitted_index down) and stopped there; an organiser running
-- a venue node and a cloud node had two databases that never learned about each
-- other. These three tables are the transport's durable side.
--
-- It replicates ADMISSION CLAIMS and nothing else. It does not replicate
-- events, tickets, orders, users or keys, and it is not a backup: a peer's
-- claim about a ticket this node has never heard of is stored (in `sync_op`,
-- which deliberately has no foreign key to `events` or `tickets`) and reported,
-- but it cannot be written into `admissions`, because that table's foreign key
-- to `tickets` is what keeps an admission row meaning something.
--
-- And it does not make a cross-gate double admission preventable. Replication
-- makes a duplicate VISIBLE SOONER and on MORE NODES. Two gates that cannot
-- see each other at the moment of the scan still both open the door, and no
-- merge rule, transport or table changes that. See docs/CLUSTERING.md.

-- ── This node's replication identity ────────────────────────────────────────
--
-- One row, ever (CHECK (id = 1)). An Ed25519 keypair that is this node's name
-- in the mesh: it signs every op this node mints and every request and response
-- it exchanges with a peer, and a peer's operator pins its public half by hand.
--
-- It is created LAZILY — the first time an operator reads it or enrols a peer —
-- and never at boot. A node with no peers is the default and must stay free of
-- key material it has no use for.
--
-- The private half lives here, in the database file, which has two
-- consequences an operator needs to know rather than discover:
--
--   * Copying the database clones this node's identity. A restored backup
--     brought up alongside the original is a second node signing as the first.
--     If that is not what you want, delete this row on the copy; the next
--     enrolment generates a fresh key and every peer must re-pin it.
--
--   * Rotation is deletion. Drop the row, and this node comes back with a new
--     key that no peer has pinned — so every peer REFUSES it until a human
--     re-enrols the new key at the other end. That refusal is the correct
--     direction: a node whose key changed is exactly what an impostor looks
--     like, and nothing in Chantier 3A silently re-pins one.
CREATE TABLE sync_node_identity (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    public_key  TEXT NOT NULL,   -- Ed25519 public key, lowercase hex
    private_key BYTEA NOT NULL,   -- Ed25519 private key seed+public (64 bytes)
    created_at  TEXT NOT NULL
);

-- ── Enrolled peers: manual, pinned, per organisation ────────────────────────
--
-- A row is created by a human typing another node's address and its public key
-- (POST /api/sync/peers). There is no discovery, no directory, no default
-- endpoint, no LAN broadcast, no pairing secret and no trust-on-first-use: an
-- inbound request presenting a key with no row here is refused, full stop, and
-- a key that does not match the pin is refused rather than re-pinned.
--
-- org_id is the scope, and it is the whole authorisation model. A peer sees the
-- admission ledger of the events belonging to the organisation it was enrolled
-- for and nothing else, so enrolling a cloud node for one organisation does not
-- hand it a multi-tenant node's other organisations. Enrolment therefore
-- requires the org's OWNER role, checked against `org_members` like every other
-- org route.
--
-- url is OPTIONAL and its emptiness is meaningful, not missing data. A peer WITH
-- a url is one this node dials (it pushes its ops there and pulls the peer's
-- back). A peer with NO url is inbound-only: this node cannot reach it and will
-- never try, it can only answer when that peer dials in. That is what makes a
-- venue node behind NAT work — the venue enrols the cloud node with its URL and
-- drives both directions; the cloud node enrols the venue node by key alone.
--
-- pull_cursor is the peer's own `sync_op.seq` this node has consumed up to.
-- push_cursor is THIS node's `sync_op.seq` it has successfully handed to that
-- peer. Both are resumable and both only move forward on success, so an
-- interrupted round repeats work rather than skipping it.
CREATE TABLE sync_peer (
    id           TEXT PRIMARY KEY,
    org_id       TEXT NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    name         TEXT NOT NULL DEFAULT '',
    url          TEXT NOT NULL DEFAULT '',
    public_key   TEXT NOT NULL,
    enabled      INTEGER NOT NULL DEFAULT 1,
    pull_cursor  INTEGER NOT NULL DEFAULT 0,
    push_cursor  INTEGER NOT NULL DEFAULT 0,
    last_sync_at TEXT NOT NULL DEFAULT '',
    last_status  TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL
);
-- One pin per key per organisation. A second enrolment of the same key for the
-- same org with a DIFFERENT url is a conflict a human resolves, not a silent
-- overwrite of a pin.
CREATE UNIQUE INDEX idx_sync_peer_org_key ON sync_peer(org_id, public_key);
-- Inbound authentication looks a presented key up across every organisation.
CREATE INDEX idx_sync_peer_key ON sync_peer(public_key);

-- ── The op log: signed admission claims, in receipt order ───────────────────
--
-- One row per admission claim this node holds, carrying the COSE_Sign1 envelope
-- that replicates it (KOTVA `substrate/SYNC.md` §4.1, minted by
-- internal/scan/substrate). Both directions live in one table: an op minted
-- from this node's own `admissions` row and an op verified on arrival from a
-- peer are the same kind of thing and are forwarded onward identically.
--
-- seq is an AUTOINCREMENT integer and it is the replication cursor. That works
-- because SQLite has exactly one writer at a time: the write lock is held from
-- a transaction's first write until it commits, so seq is assigned in commit
-- order and a reader that has seen seq N can never later be handed an
-- unseen row below N. A cursor over `admissions.id` would NOT be safe — those
-- are ULIDs, and two ULIDs minted in the same millisecond have no guaranteed
-- order, so a `>` cursor over them could step past a row forever. AUTOINCREMENT
-- (rather than a bare INTEGER PRIMARY KEY) additionally guarantees ids are
-- never reused after a delete.
--
-- op_id is the §4.1 content address: the same claim signed by the same node is
-- byte-identical and therefore one row, which is what makes a re-push a no-op.
--
-- The (event_id, claim_ticket, claim_device, claim_scanned_at) uniqueness is
-- the SAME idempotency key `POST /api/scan/sync` has always used. It means this
-- node keeps ONE op per claim even when two nodes each minted their own
-- (different author, different op_id, identical §4.3 element bytes — the
-- element carries the claim, never its author). Whichever it keeps, the merged
-- observable state is the same on every node, which is precisely why
-- substrate.Ledger.StateRoot is comparable across nodes at all.
--
-- delivered_by records WHICH ENROLLED PEER handed this op over, separately from
-- `author`, which is the node that signed it. They differ for a relayed op, and
-- keeping both is the honest record: a signature proves the authoring node
-- recorded the claim, not that a physical scanner produced it (a Chantier 3A gate is
-- a browser with no keypair and cannot sign anything). '' means this node
-- minted it from its own `admissions` table.
--
-- There is deliberately no foreign key on event_id. A verified claim about an
-- event this node does not have is still evidence about a door, and dropping it
-- to satisfy referential integrity would throw away the one thing replication
-- exists to move.
CREATE TABLE sync_op (
    seq              SERIAL PRIMARY KEY,
    op_id            TEXT NOT NULL UNIQUE,
    event_id         TEXT NOT NULL,
    author           TEXT NOT NULL,
    delivered_by     TEXT NOT NULL DEFAULT '',
    claim_ticket     TEXT NOT NULL,
    claim_device     TEXT NOT NULL,
    claim_scanned_at TEXT NOT NULL,
    applied          INTEGER NOT NULL DEFAULT 0,
    cose             BYTEA NOT NULL,
    created_at       TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_sync_op_claim
    ON sync_op(event_id, claim_ticket, claim_device, claim_scanned_at);
-- Serving a pull is "seq > cursor, for the events of one org", and minting is
-- an anti-join from `admissions` on the claim key; these cover both.
CREATE INDEX idx_sync_op_event_seq ON sync_op(event_id, seq);
CREATE INDEX idx_sync_op_claim_key ON sync_op(claim_ticket, claim_device, claim_scanned_at);
-- `applied` = 0 marks a verified op that could not be written into
-- `admissions` yet, which on a node that does not hold the ticket means "known
-- but not counted". It is reported as such (GET /api/sync/status) rather than
-- being allowed to look like a clean ledger.
CREATE INDEX idx_sync_op_unapplied ON sync_op(applied) WHERE applied = 0;
