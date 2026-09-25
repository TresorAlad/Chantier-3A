-- Audit trail for the compensating-payment (refund) flow — see
-- internal/payments/compensating.go and the sibling patala repo's
-- docs/compensating-payments.md.
--
-- Chantier 3A never holds funds and never reverses a settled payment on a rail
-- that cannot support it (patala_core::PaymentRail::refund stays
-- Error::Unsupported on NonCustodialFinal rails, deliberately). Paying a
-- customer back there is a SECOND, independent payment ("compensating
-- payment") to a destination the CUSTOMER supplies — never inferred, never
-- the address the original payment came from — and it ALWAYS requires an
-- explicit human to confirm it, with no automatic or batch-approved path.
--
-- This table is the durable record of every destination-validation
-- DECISION on that path, refused or not — "customer supplied address X for
-- order Y, it was refused because Z" is exactly as much an audit fact as an
-- approved payout, so a row exists for both. There is deliberately no
-- separate "approvals" table: approved_by/approved_at/executed being NULL
-- on a row already tells the whole refusal story.
--
-- No foreign key to orders(id): compensating payments exist on the
-- payments-provider seam (internal/payments), which is storage-agnostic by
-- design (see RecordStore/SeenStore/OrderLookup in provider.go) and does not
-- assume every original_reference names a row in THIS database's orders
-- table — a self-hoster's own OrderLookup implementation owns that.
CREATE TABLE compensating_payment_audits (
    id                     TEXT PRIMARY KEY,
    original_reference     TEXT NOT NULL,
    payout_reference       TEXT NOT NULL DEFAULT '',
    rail_id                TEXT NOT NULL,
    destination            TEXT NOT NULL,
    sender_address_known   INTEGER NOT NULL DEFAULT 0,
    sender_address         TEXT NOT NULL DEFAULT '',
    status                 TEXT NOT NULL,
    reason                 TEXT NOT NULL DEFAULT '',
    is_refusal             INTEGER NOT NULL DEFAULT 0,
    same_as_sender_address INTEGER NOT NULL DEFAULT 0,
    refused                INTEGER NOT NULL DEFAULT 0,
    approved_by            TEXT NOT NULL DEFAULT '',
    approved_at            TEXT,
    executed               INTEGER NOT NULL DEFAULT 0,
    amount_minor           INTEGER NOT NULL,
    currency               TEXT NOT NULL,
    created_at             TEXT NOT NULL
);
CREATE INDEX idx_compensating_payment_audits_original_reference ON compensating_payment_audits(original_reference);
