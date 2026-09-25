-- Pass tier for festival passes (student / standard / VIP).
ALTER TABLE ticket_types ADD COLUMN pass_tier TEXT
    CHECK (pass_tier IS NULL OR pass_tier IN ('student', 'standard', 'vip'));
