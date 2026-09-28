-- Opt-in event feeds between Chantier 3A nodes, over the peer channel that already
-- exists (migration 0003).
--
-- What this is for
-- ────────────────
-- Migration 0003 gave two nodes a way to exchange ADMISSION CLAIMS. It gave
-- them nothing else: an organiser who runs their own box has no way to let
-- another organiser they know list their events, and no way to show that
-- organiser's events beside their own. This migration adds exactly that, and
-- nothing wider.
--
-- The unit of trust is unchanged and is not extended: a `sync_peer` row, which
-- exists because a human typed another node's address and pinned its key. There
-- is no discovery here — no directory, no index, no rendezvous, no "organisers
-- near you", no global feed. A node that has not been enrolled by hand is never
-- contacted and is never answered. Enrolment is still the whole model.
--
-- Two switches, because the two directions are two decisions
-- ─────────────────────────────────────────────────────────
-- Enrolling a peer to reconcile door scans is NOT consent to publish a
-- programme to them, and it is not consent to show theirs. So the two
-- directions are separate columns, and BOTH DEFAULT TO OFF:
--
--   feed_publish   — this node answers GET /api/sync/feed for that peer's key
--                    with its own PUBLISHED events. 0 means the peer is refused
--                    that route even though it is fully enrolled for admission
--                    replication.
--
--   feed_subscribe — this node will pull that peer's feed when an operator asks
--                    it to. 0 means the pull route refuses before any socket is
--                    opened, so an un-subscribed peer is never dialled for a
--                    feed at all.
--
-- Every existing row gets 0 for both. An operator who upgrades an already
-- clustered deployment publishes nothing and shows nothing until they say so,
-- which is the only safe way for a switch like this to arrive.
--
-- feed_pulled_at / feed_status are the same diagnostics the sync round already
-- keeps (last_sync_at / last_status), for the feed direction, and they record
-- refusals as readily as successes.
ALTER TABLE sync_peer ADD COLUMN feed_publish   INTEGER NOT NULL DEFAULT 0;
ALTER TABLE sync_peer ADD COLUMN feed_subscribe INTEGER NOT NULL DEFAULT 0;
ALTER TABLE sync_peer ADD COLUMN feed_pulled_at TEXT    NOT NULL DEFAULT '';
ALTER TABLE sync_peer ADD COLUMN feed_status    TEXT    NOT NULL DEFAULT '';

-- ── A peer's events, as this node last saw them ─────────────────────────────
--
-- A CACHE, and only a cache. Every row here is a copy of something that lives
-- on another operator's box, fetched over a signed response from a pinned key,
-- and it is replaced wholesale on every pull: an event the publisher has
-- unpublished, renamed or deleted stops existing here on the next pull rather
-- than lingering as a stale listing pointing at a dead page.
--
-- What is deliberately NOT here is as important as what is. There is no price,
-- no ticket type, no capacity, no currency and no order path, because THIS NODE
-- CANNOT SELL A PEER'S TICKETS and must never render something that looks as if
-- it can. A peer event is a signpost: a title, a time, a place, and a link back
-- to the publisher's own /h/ page on the publisher's own box, where the
-- publisher's own keys issue the tickets. Chantier 3A has no cross-node checkout and
-- this table is shaped so that none can be built on top of it by accident.
--
-- org_id is the SUBSCRIBING organisation — the scope in which these listings are
-- shown here — and it cascades, so deleting an org takes its borrowed listings
-- with it. peer_id cascades too, which is what makes revocation real: deleting
-- the enrolment deletes the cached events in the same statement, so a peer an
-- operator has cut off cannot keep being displayed by a stale cache.
--
-- publisher_key is the pinned node key whose SIGNED response carried this row.
-- It is stored per row rather than only on the peer, so a listing can always
-- name the key it came from even while a peer row is being rewritten, and so a
-- display can never attribute an event to the wrong publisher.
--
-- url is built HERE, from the enrolled peer's own base URL and a slug this node
-- has validated, and never taken from the publisher's answer. A publisher that
-- could hand over an arbitrary link could point a listing carrying its
-- neighbour's name at anything at all; it cannot, because the link is composed
-- locally out of an origin a human typed.
CREATE TABLE peer_event (
    id              TEXT PRIMARY KEY,
    peer_id         TEXT NOT NULL REFERENCES sync_peer(id) ON DELETE CASCADE,
    org_id          TEXT NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    publisher_key   TEXT NOT NULL,
    publisher_name  TEXT NOT NULL DEFAULT '',
    remote_event_id TEXT NOT NULL,
    slug            TEXT NOT NULL,
    url             TEXT NOT NULL,
    title           TEXT NOT NULL,
    summary         TEXT NOT NULL DEFAULT '',
    venue_name      TEXT NOT NULL DEFAULT '',
    address         TEXT NOT NULL DEFAULT '',
    starts_at       TEXT NOT NULL,
    ends_at         TEXT NOT NULL,
    timezone        TEXT NOT NULL DEFAULT '',
    category        TEXT NOT NULL DEFAULT '',
    fetched_at      TEXT NOT NULL
);
-- One row per remote event per peer. A second pull replaces the peer's rows
-- rather than accumulating them, and this index is what makes that a constraint
-- rather than a convention.
CREATE UNIQUE INDEX idx_peer_event_peer_remote ON peer_event(peer_id, remote_event_id);
-- Reading is always "the borrowed listings of one organisation, soonest first".
CREATE INDEX idx_peer_event_org_start ON peer_event(org_id, starts_at);
