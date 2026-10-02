-- pg-only: PostgreSQL only; skipped by the SQLite test store (tests/sqlite_store.py).
-- Check-in module (TDEV-54/55/56): terminals, station rules, immutable scan journal,
-- canonical consumptions, conflicts and the precomputed entitlement snapshot.
-- Design: docs/checkin/DESIGN.md, docs/checkin/ADR-001-conflits.md.
--
-- Nothing in the existing 3A schema is altered. The journals carry no ON DELETE CASCADE
-- foreign key to events: deleting an event must not erase an "immutable" audit log.
-- Derived tables (rules, consumptions, entitlements) do cascade.

CREATE TABLE checkin_terminals (
    terminal_id     uuid PRIMARY KEY,
    event_id        text NOT NULL,
    label           text NOT NULL DEFAULT '',
    default_station text,
    registered_by   text,
    first_seen_at   timestamptz NOT NULL DEFAULT now(),
    last_seen_at    timestamptz NOT NULL DEFAULT now(),
    last_batch_at   timestamptz,
    pending_count   integer,                       -- outbox size reported by the app (optional)
    clock_offset_ms bigint,
    revoked_at      timestamptz,
    revoked_by      text
);
CREATE INDEX idx_checkin_terminals_event ON checkin_terminals (event_id, last_seen_at DESC);

CREATE TABLE checkin_station_rules (
    event_id       text NOT NULL REFERENCES events(id)       ON DELETE CASCADE,
    ticket_type_id text NOT NULL REFERENCES ticket_types(id) ON DELETE CASCADE,
    station        text NOT NULL CHECK (station ~ '^[A-Z][A-Z0-9_]{1,31}$'),
    max_uses       integer NOT NULL DEFAULT 1 CHECK (max_uses >= 0),
    PRIMARY KEY (event_id, ticket_type_id, station)
);

CREATE TABLE scan_logs (
    log_id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    operation_id           uuid    NOT NULL UNIQUE,
    scan_id                uuid,
    payload_hash           bytea   NOT NULL,
    event_id               text    NOT NULL,
    ticket_id              text,
    participant_ref        text,
    terminal_id            uuid    NOT NULL,
    staff_user_id          text,
    station                text    NOT NULL,
    reported_decision      text,
    reported_valid         boolean NOT NULL,
    server_decision        text    NOT NULL,
    server_reason          text    NOT NULL DEFAULT '',
    capability_verified    boolean,
    is_claim               boolean NOT NULL,
    ack_status             text    NOT NULL CHECK (ack_status IN ('accepted', 'conflict')),
    device_evaluated_at    timestamptz,
    device_sent_at         timestamptz,
    server_received_at     timestamptz NOT NULL,
    clock_offset_ms        bigint  NOT NULL DEFAULT 0,
    corrected_evaluated_at timestamptz NOT NULL,
    clock_suspect          boolean NOT NULL DEFAULT false,
    clock_suspect_reason   text    NOT NULL DEFAULT '',
    app_version            text    NOT NULL DEFAULT '',
    qr_version             integer,
    connection_status      text    NOT NULL CHECK (connection_status IN ('online', 'offline_synced')),
    batch_id               uuid
);

-- Append-only: enforced by the database, not only by convention.
CREATE FUNCTION scan_logs_immutable() RETURNS trigger LANGUAGE plpgsql AS
$$ BEGIN RAISE EXCEPTION 'scan_logs is append-only'; END $$;
CREATE TRIGGER trg_scan_logs_immutable
    BEFORE UPDATE OR DELETE ON scan_logs
    FOR EACH ROW EXECUTE FUNCTION scan_logs_immutable();

-- Ranking of the claimants of one (ticket, station): the critical path of conflict resolution.
CREATE INDEX idx_scan_logs_claims
    ON scan_logs (ticket_id, station, corrected_evaluated_at, operation_id) WHERE is_claim;
-- /logs cursor pagination.
CREATE INDEX idx_scan_logs_event_log ON scan_logs (event_id, log_id);
-- /logs?terminal_id=, /stats last activity per terminal.
CREATE INDEX idx_scan_logs_terminal ON scan_logs (terminal_id, server_received_at DESC);

CREATE TABLE station_consumptions (
    ticket_id      text    NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    station        text    NOT NULL,
    use_index      integer NOT NULL CHECK (use_index >= 0),
    event_id       text    NOT NULL,
    winning_log_id bigint  NOT NULL REFERENCES scan_logs(log_id),
    consumed_at    timestamptz NOT NULL,
    updated_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (ticket_id, station, use_index)
);
CREATE INDEX idx_station_consumptions_event_station ON station_consumptions (event_id, station);
CREATE INDEX idx_station_consumptions_winner ON station_consumptions (winning_log_id);

CREATE TABLE scan_conflicts (
    conflict_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id       text   NOT NULL,
    ticket_id      text,
    station        text   NOT NULL,
    winning_log_id bigint REFERENCES scan_logs(log_id),
    losing_log_id  bigint NOT NULL UNIQUE REFERENCES scan_logs(log_id),
    type           text   NOT NULL CHECK (type IN (
                       'CROSS_TERMINAL_DOUBLE_ADMISSION', 'SAME_TERMINAL_REPLAY',
                       'LATE_REVOKED', 'NOT_AUTHORIZED_SERVER_SIDE', 'CLOCK_SUSPECT')),
    clock_suspect  boolean NOT NULL DEFAULT false,
    detected_at    timestamptz NOT NULL DEFAULT now(),
    status         text   NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'acknowledged')),
    note           text   NOT NULL DEFAULT '',
    resolved_by    text,
    resolved_at    timestamptz
);
-- GET /conflicts: newest first, cursor on conflict_id (detected_at grows with conflict_id).
CREATE INDEX idx_scan_conflicts_event_status ON scan_conflicts (event_id, status, conflict_id DESC);
CREATE INDEX idx_scan_conflicts_ticket_station ON scan_conflicts (ticket_id, station);

-- Precomputed, versioned entitlements served by /api/checkin/snapshot.
CREATE SEQUENCE checkin_version_seq;
CREATE TABLE checkin_entitlements (
    event_id       text   NOT NULL,
    ticket_id      text   NOT NULL,
    serial         text   NOT NULL,
    ticket_type_id text   NOT NULL,
    status         text   NOT NULL,
    stations       text[] NOT NULL,
    uses           jsonb  NOT NULL DEFAULT '{}',
    content_hash   text   NOT NULL,
    version        bigint NOT NULL,
    PRIMARY KEY (event_id, ticket_id)
);
CREATE INDEX idx_checkin_entitlements_delta ON checkin_entitlements (event_id, version, ticket_id);

CREATE TABLE checkin_snapshot_meta (
    event_id     text PRIMARY KEY,
    refreshed_at timestamptz NOT NULL,
    max_version  bigint NOT NULL DEFAULT 0
);
