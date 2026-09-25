-- Chantier 3A — baseline schema (folded).
--
-- This is the whole schema in one clean, forward-only file: every table with
-- its final columns inline, no ALTER/DROP, no intermediate states. Chantier 3A has
-- never shipped a production database, so the historical 0001–0006 migration
-- series (init + password-reset tokens + images/categories + org invites +
-- org bank accounts + currency minor-unit rework) was collapsed into this
-- single baseline. New databases apply exactly this file; nothing is lost —
-- this reproduces the same schema those six migrations produced.
--
-- Conventions:
--   * IDs are ULID strings (TEXT). Timestamps are RFC-3339 TEXT (see
--     store.timeToText). Money is always an INTEGER count of minor units in
--     the row's own currency (never a float) — column suffix `_minor`.
--   * Foreign keys are declared inline; SQLite permits forward references, so
--     the events↔images cover-image cycle needs no follow-up ALTER.
--   * `schema_migrations` is created and maintained by the Go runner
--     (internal/store.Migrate), never here.

-- ── Identity & auth ─────────────────────────────────────────────────────────

CREATE TABLE users (
    id                TEXT PRIMARY KEY,
    email             TEXT NOT NULL UNIQUE,
    password_hash     TEXT NOT NULL,
    name              TEXT NOT NULL DEFAULT '',
    created_at        TEXT NOT NULL,
    email_verified_at TEXT
);

CREATE TABLE sessions (
    token_hash TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);

CREATE TABLE oauth_identities (
    provider   TEXT NOT NULL,
    subject    TEXT NOT NULL,
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    PRIMARY KEY (provider, subject)
);
CREATE INDEX idx_oauth_identities_user_id ON oauth_identities(user_id);

CREATE TABLE password_reset_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    used_at    TEXT
);
CREATE INDEX idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);

-- ── Orgs & membership ───────────────────────────────────────────────────────

CREATE TABLE orgs (
    id               TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    slug             TEXT NOT NULL UNIQUE,
    created_at       TEXT NOT NULL,
    default_currency TEXT NOT NULL DEFAULT 'USD'
);

CREATE TABLE org_members (
    org_id     TEXT NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role       TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'scanner')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (org_id, user_id)
);
CREATE INDEX idx_org_members_user_id ON org_members(user_id);

CREATE TABLE org_invites (
    id          TEXT PRIMARY KEY,
    org_id      TEXT NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    email       TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'scanner')),
    token_hash  TEXT NOT NULL UNIQUE,
    invited_by  TEXT REFERENCES users(id) ON DELETE SET NULL,
    expires_at  TEXT NOT NULL,
    accepted_at TEXT,
    created_at  TEXT NOT NULL
);
CREATE INDEX idx_org_invites_org_id ON org_invites(org_id);
CREATE INDEX idx_org_invites_email ON org_invites(email);

CREATE TABLE org_bank_accounts (
    org_id         TEXT PRIMARY KEY REFERENCES orgs(id) ON DELETE CASCADE,
    bank_code      TEXT NOT NULL,
    bank_name      TEXT NOT NULL DEFAULT '',
    account_number TEXT NOT NULL,
    account_name   TEXT NOT NULL,
    recipient_code TEXT NOT NULL DEFAULT '',
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);

-- ── Events ──────────────────────────────────────────────────────────────────
-- events.cover_image_id references images(id); images.event_id references
-- events(id). SQLite resolves these forward references at CREATE time, so the
-- cycle is declared inline with no ALTER.

CREATE TABLE events (
    id             TEXT PRIMARY KEY,
    org_id         TEXT NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    slug           TEXT NOT NULL UNIQUE,
    title          TEXT NOT NULL,
    summary        TEXT NOT NULL DEFAULT '',
    description    TEXT NOT NULL DEFAULT '',
    venue_name     TEXT NOT NULL DEFAULT '',
    address        TEXT NOT NULL DEFAULT '',
    lat            REAL,
    lng            REAL,
    starts_at      TEXT NOT NULL,
    ends_at        TEXT NOT NULL,
    timezone       TEXT NOT NULL DEFAULT 'UTC',
    cover_image    TEXT NOT NULL DEFAULT '',
    status         TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'cancelled')),
    currency       TEXT NOT NULL DEFAULT 'ZAR',
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    category       TEXT NOT NULL DEFAULT '',
    cover_image_id TEXT REFERENCES images(id) ON DELETE SET NULL
);
CREATE INDEX idx_events_org_id ON events(org_id);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_category ON events(category);

CREATE TABLE images (
    id          TEXT PRIMARY KEY,
    event_id    TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    format      TEXT NOT NULL CHECK (format IN ('png', 'jpeg', 'webp')),
    width       INTEGER NOT NULL,
    height      INTEGER NOT NULL,
    size_bytes  INTEGER NOT NULL,
    uploaded_by TEXT REFERENCES users(id) ON DELETE SET NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX idx_images_event_id ON images(event_id);

CREATE TABLE event_keys (
    id          TEXT PRIMARY KEY,
    event_id    TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    public_key  BLOB NOT NULL,
    private_key BLOB NOT NULL,
    created_at  TEXT NOT NULL,
    revoked_at  TEXT
);
CREATE INDEX idx_event_keys_event_id ON event_keys(event_id);

CREATE TABLE ticket_types (
    id             TEXT PRIMARY KEY,
    event_id       TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name           TEXT NOT NULL,
    description    TEXT NOT NULL DEFAULT '',
    price_minor    INTEGER NOT NULL DEFAULT 0,
    quantity_total INTEGER NOT NULL DEFAULT 0,
    quantity_sold  INTEGER NOT NULL DEFAULT 0,
    sales_start    TEXT,
    sales_end      TEXT,
    max_per_order  INTEGER NOT NULL DEFAULT 0,
    status         TEXT NOT NULL DEFAULT 'draft',
    sort_order     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_ticket_types_event_id ON ticket_types(event_id);

-- ── Orders & tickets ────────────────────────────────────────────────────────

CREATE TABLE orders (
    id             TEXT PRIMARY KEY,
    event_id       TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    user_id        TEXT REFERENCES users(id) ON DELETE SET NULL,
    buyer_email    TEXT NOT NULL,
    buyer_name     TEXT NOT NULL DEFAULT '',
    status         TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'failed', 'refunded', 'cancelled')),
    subtotal_minor INTEGER NOT NULL DEFAULT 0,
    fee_minor      INTEGER NOT NULL DEFAULT 0,
    total_minor    INTEGER NOT NULL DEFAULT 0,
    currency       TEXT NOT NULL DEFAULT 'ZAR',
    provider       TEXT NOT NULL DEFAULT '',
    provider_ref   TEXT,
    created_at     TEXT NOT NULL,
    paid_at        TEXT
);
CREATE INDEX idx_orders_event_id ON orders(event_id);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE UNIQUE INDEX idx_orders_provider_ref ON orders(provider, provider_ref) WHERE provider_ref IS NOT NULL;

CREATE TABLE order_items (
    id               TEXT PRIMARY KEY,
    order_id         TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    ticket_type_id   TEXT NOT NULL REFERENCES ticket_types(id),
    quantity         INTEGER NOT NULL,
    unit_price_minor INTEGER NOT NULL
);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);

CREATE TABLE tickets (
    id             TEXT PRIMARY KEY,
    order_id       TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    event_id       TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    ticket_type_id TEXT NOT NULL REFERENCES ticket_types(id),
    holder_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    holder_name    TEXT NOT NULL DEFAULT '',
    serial         TEXT NOT NULL UNIQUE,
    capability     TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'valid' CHECK (status IN ('valid', 'void', 'refunded')),
    issued_at      TEXT NOT NULL,
    voided_at      TEXT
);
CREATE INDEX idx_tickets_order_id ON tickets(order_id);
CREATE INDEX idx_tickets_event_id ON tickets(event_id);
CREATE INDEX idx_tickets_holder_user_id ON tickets(holder_user_id);

-- ── Admission (the offline gate) ────────────────────────────────────────────

CREATE TABLE admissions (
    id         TEXT PRIMARY KEY,
    ticket_id  TEXT NOT NULL REFERENCES tickets(id),
    event_id   TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    gate_id    TEXT NOT NULL DEFAULT '',
    scanned_by TEXT,
    device_id  TEXT NOT NULL DEFAULT '',
    scanned_at TEXT NOT NULL,
    result     TEXT NOT NULL CHECK (result IN ('admitted', 'duplicate', 'invalid', 'wrong_event')),
    note       TEXT NOT NULL DEFAULT ''
);
-- One successful admission per ticket, enforced even across offline batch sync.
CREATE UNIQUE INDEX idx_admissions_admitted_once ON admissions(ticket_id) WHERE result = 'admitted';
CREATE INDEX idx_admissions_event_id ON admissions(event_id);
CREATE INDEX idx_admissions_ticket_id ON admissions(ticket_id);
CREATE INDEX idx_admissions_sync_key ON admissions(ticket_id, device_id, scanned_at);

CREATE TABLE allocations (
    id             TEXT PRIMARY KEY,
    event_id       TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    device_id      TEXT NOT NULL,
    ticket_type_id TEXT REFERENCES ticket_types(id),
    count          INTEGER NOT NULL DEFAULT 0,
    issued_at      TEXT NOT NULL,
    expires_at     TEXT,
    signature      TEXT NOT NULL
);
CREATE INDEX idx_allocations_event_id ON allocations(event_id);
CREATE INDEX idx_allocations_device_id ON allocations(device_id);

-- ── Payments (seam) ─────────────────────────────────────────────────────────

CREATE TABLE payouts (
    id           TEXT PRIMARY KEY,
    event_id     TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    org_id       TEXT NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    amount_minor INTEGER NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',
    provider_ref TEXT,
    created_at   TEXT NOT NULL,
    paid_at      TEXT,
    currency     TEXT NOT NULL DEFAULT ''
);
CREATE INDEX idx_payouts_event_id ON payouts(event_id);
CREATE INDEX idx_payouts_org_id ON payouts(org_id);

CREATE TABLE payment_records (
    provider     TEXT NOT NULL,
    reference    TEXT NOT NULL,
    amount_minor INTEGER NOT NULL,
    currency     TEXT NOT NULL,
    status       TEXT NOT NULL,
    instructions TEXT NOT NULL DEFAULT '',
    marked_by    TEXT NOT NULL DEFAULT '',
    marked_at    TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    PRIMARY KEY (provider, reference)
);
CREATE INDEX idx_payment_records_provider ON payment_records(provider);
