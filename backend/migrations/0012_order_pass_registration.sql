-- Pass application details (student pass checkout form).
ALTER TABLE orders ADD COLUMN buyer_first_name TEXT NOT NULL DEFAULT '';
ALTER TABLE orders ADD COLUMN buyer_last_name TEXT NOT NULL DEFAULT '';
ALTER TABLE orders ADD COLUMN school_name TEXT NOT NULL DEFAULT '';
ALTER TABLE orders ADD COLUMN motivation TEXT NOT NULL DEFAULT '';
ALTER TABLE orders ADD COLUMN wish TEXT NOT NULL DEFAULT '';
