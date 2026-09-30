-- One active registration (pending or paid) per buyer email per event.
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_event_buyer_email_active
    ON orders (event_id, lower(buyer_email))
    WHERE status IN ('pending', 'paid');
