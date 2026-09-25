-- Community catalog: ticket / goodie / option on the same sale line table.
ALTER TABLE ticket_types ADD COLUMN product_kind TEXT NOT NULL DEFAULT 'ticket'
    CHECK (product_kind IN ('ticket', 'goodie', 'option'));

-- Outbound e-mail queue (idempotent per order + template).
CREATE TABLE IF NOT EXISTS outbound_emails (
    id           TEXT PRIMARY KEY,
    order_id     TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    template     TEXT NOT NULL,
    to_email     TEXT NOT NULL,
    subject      TEXT NOT NULL,
    body_text    TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
    error        TEXT,
    created_at   TEXT NOT NULL,
    sent_at      TEXT,
    UNIQUE (order_id, template)
);
CREATE INDEX IF NOT EXISTS idx_outbound_emails_status ON outbound_emails(status);
