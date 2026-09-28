/**
 * Where an organisation's own page lives.
 *
 * # Why this is not in host.js
 *
 * `orgHref()` in @/lib/host answers a different question: "where does this
 * organisation's LABEL go", and its answer is the same listing narrowed with
 * `?host=` — still the right answer for a chip in a filter row, because
 * following it keeps you in the app with your search and your category intact.
 *
 * This answers "where is everything this organiser has on". That is a page of
 * its own, `GET /o/{slug}`, server-rendered by the box that published the
 * events (internal/httpapi/org_page_handlers.go). It is the address you can
 * give somebody who is not standing in the app: on a poster, in a message, or —
 * the case it was built for — from another operator's box, where a borrowed
 * listing has to link back to the publisher's own site rather than pretend to
 * sell the ticket itself.
 *
 * # What it is NOT
 *
 * It is not a profile, not a directory entry and not a discoverable thing.
 * Nothing indexes these pages (the route serves `X-Robots-Tag: noindex`),
 * nothing lists them, and there is no way to get to one except from a link
 * somebody already had. An organisation gets a page here only if this box
 * already shows its events — the route answers 404 for an organisation outside
 * this host's display scope in exactly the way it answers for one that does not
 * exist, so it cannot be walked to find out who is on a box.
 */

/**
 * The href for an organisation's own page, or null when there is no
 * organisation to link to.
 *
 * Null rather than a fallback URL, and callers must render nothing when they
 * get it: `orgHref()` can fall back to `/events` because a listing with no
 * narrowing is still a truthful page, but there is no such thing as an
 * organisation page for no organisation. A guessed one would 404.
 *
 * The reference is the slug when there is one and the id otherwise — GET
 * /o/{ref} accepts either. The slug is preferred because it is the readable
 * half of a link somebody might type or read aloud.
 */
export function orgPageHref(org: { id?: unknown; slug?: unknown; name?: unknown } | null | undefined) {
    const slug = typeof org?.slug === 'string' ? org.slug : '';
    const id = typeof org?.id === 'string' ? org.id : '';
    const ref = slug || id;
    return ref ? `/o/${encodeURIComponent(ref)}` : null;
}
