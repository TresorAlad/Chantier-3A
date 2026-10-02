-- Explicit scan rights configured per ticket type (design shared with the mobile team's PR #3).
-- Safe defaults grant only the main entrance; the other controls are enabled by an organizer.
-- The check-in module reads these flags; a row in checkin_station_rules still overrides them.
ALTER TABLE ticket_types ADD COLUMN access_event BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE ticket_types ADD COLUMN access_food BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE ticket_types ADD COLUMN access_merch BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE ticket_types ADD COLUMN access_after BOOLEAN NOT NULL DEFAULT FALSE;
