-- Sectorized check-in and idempotent mobile outbox ingestion.
ALTER TABLE admissions ADD COLUMN control_type TEXT NOT NULL DEFAULT 'event_entry'
    CHECK (control_type IN ('event_entry', 'food_access', 'merch_pickup', 'after_entry'));
ALTER TABLE admissions ADD COLUMN operation_id TEXT;

DROP INDEX idx_admissions_admitted_once;
CREATE UNIQUE INDEX idx_admissions_admitted_once_per_control
    ON admissions(ticket_id, control_type) WHERE result = 'admitted';
CREATE UNIQUE INDEX idx_admissions_operation_id
    ON admissions(operation_id) WHERE operation_id IS NOT NULL;
CREATE INDEX idx_admissions_event_control_time
    ON admissions(event_id, control_type, scanned_at);
