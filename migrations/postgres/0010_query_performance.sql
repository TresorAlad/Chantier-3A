-- Query-oriented indexes for hot paths in internal/store (vitrine, admin
-- orders/attendees, checkout inventory, outbound mail). Safe to re-apply:
-- IF NOT EXISTS on every object.

-- Public listing: status = published, ORDER BY starts_at, id
CREATE INDEX IF NOT EXISTS idx_events_published_starts
    ON events(status, starts_at ASC, id ASC);

-- Admin event list per org: ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_events_org_created
    ON events(org_id, created_at DESC, id DESC);

-- Category chips: published + non-empty category
CREATE INDEX IF NOT EXISTS idx_events_published_category
    ON events(category)
    WHERE status = 'published' AND category != '';

-- Scoped vitrine when HostScope filters org_id
CREATE INDEX IF NOT EXISTS idx_events_org_published_starts
    ON events(org_id, starts_at ASC, id ASC)
    WHERE status = 'published';

-- Organiser orders screen
CREATE INDEX IF NOT EXISTS idx_orders_event_created
    ON orders(event_id, created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_orders_user_created
    ON orders(user_id, created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_orders_event_status
    ON orders(event_id, status);

-- Buyer tickets + attendee roster
CREATE INDEX IF NOT EXISTS idx_tickets_event_status
    ON tickets(event_id, status);

CREATE INDEX IF NOT EXISTS idx_tickets_event_issued
    ON tickets(event_id, issued_at DESC, id DESC);

-- Stats join order_items -> ticket_types
CREATE INDEX IF NOT EXISTS idx_order_items_ticket_type
    ON order_items(ticket_type_id);

-- Catalogue sort on event page
CREATE INDEX IF NOT EXISTS idx_ticket_types_event_sort
    ON ticket_types(event_id, sort_order ASC, name ASC, id ASC);

-- Admission counts and gate lookups
CREATE INDEX IF NOT EXISTS idx_admissions_event_result
    ON admissions(event_id, result);

-- Pending org invites list
CREATE INDEX IF NOT EXISTS idx_org_invites_org_open
    ON org_invites(org_id, created_at DESC, id DESC)
    WHERE accepted_at IS NULL;

-- E-mail worker queue
CREATE INDEX IF NOT EXISTS idx_outbound_emails_pending_created
    ON outbound_emails(created_at ASC)
    WHERE status = 'pending';

-- Refresh planner stats after bulk index creation (PostgreSQL)
ANALYZE;
