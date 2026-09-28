-- Host-authored event pages (see docs/HOST-PAGES.md).
--
-- One row per event, holding the host's page document as validated JSON.
--
-- Why event_id is the PRIMARY KEY, and there is no page id
-- ────────────────────────────────────────────────────────
-- Multi-tenancy here is structural rather than enforced by a WHERE clause a
-- future handler might forget. A page has no identity of its own: it cannot be
-- addressed except through an event, an event belongs to exactly one org, and
-- so the RBAC check every route already runs (auth.CanManageEvent, which
-- resolves the event's org itself) is automatically the right check for the
-- page too. There is no /api/pages/{id} route that could be reached without
-- naming an event, because there is no page id to put in one.
--
-- The alternative — a `pages` table with its own ULID and an event_id column —
-- would have created exactly the class of bug this schema shape forecloses: a
-- flat route that looks up a page by id and forgets to re-derive the org.
-- internal/httpapi already carries two such lookups for ticket types and
-- images (see dbutil.go's ticketTypeEventID) precisely because those tables
-- were shaped that way. This one is not.
--
-- ON DELETE CASCADE: deleting an event deletes its page. A page is not a
-- record of anything that happened — unlike an admission or an order, nothing
-- is lost or made unauditable by it going away with the event it describes.
--
-- `document` is TEXT holding JSON, never a blob and never the host's own
-- bytes: internal/httpapi stores pages.Document.Canonical(), which is a
-- re-marshalling of a parsed, validated Go struct. Anything the decoder did
-- not understand cannot reach this column even in principle.
--
-- `version` duplicates the document's own "version" field into a column so a
-- future migration can find every page of a given format version without
-- parsing JSON in SQL.
CREATE TABLE event_pages (
    event_id   TEXT PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
    version    INTEGER NOT NULL,
    document   TEXT NOT NULL,
    updated_by TEXT REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
