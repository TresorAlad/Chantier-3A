-- Public pass serial counter (TDEV-YYYY-NNNN) and void pre-format tickets.
CREATE TABLE pass_serial_counters (
    year     INTEGER NOT NULL PRIMARY KEY,
    last_seq INTEGER NOT NULL DEFAULT 0
);

UPDATE tickets
SET status = 'void',
    voided_at = COALESCE(voided_at, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
WHERE status = 'valid';
