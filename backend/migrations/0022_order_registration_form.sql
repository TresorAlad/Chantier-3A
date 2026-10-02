-- Full participant form (TDEV Festival 2026, V1) stored as JSON text.
ALTER TABLE orders ADD COLUMN registration_form TEXT NOT NULL DEFAULT '{}';
