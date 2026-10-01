-- Explicit scan rights configured per ticket type. Safe defaults grant only the
-- main event entrance; additional controls must be enabled by an organizer.
ALTER TABLE ticket_types ADD COLUMN access_event BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE ticket_types ADD COLUMN access_food BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE ticket_types ADD COLUMN access_merch BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE ticket_types ADD COLUMN access_after BOOLEAN NOT NULL DEFAULT FALSE;
