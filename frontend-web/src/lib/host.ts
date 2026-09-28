/**
 * The `host` envelope on `GET /api/events`, turned into the words and the
 * decisions a page needs.
 *
 * # Why this file exists
 *
 * Tdev Festival is self-hosted. Somebody installed it on their own machine to sell
 * tickets to their own events. A page headed "Browse all events" describes a
 * marketplace with everybody's events in it, and there is no such thing —
 * there is one box, belonging to one operator, with their events on it. The
 * listing API now says whose events it is returning (see
 * internal/httpapi/host_scope.go); this is the one place the app turns that
 * into copy, so the answer cannot drift page to page.
 *
 * Two rules are enforced here rather than left to each caller:
 *
 *  1. **A name is never invented.** If the operator has not named their host
 *     (`TDEV_HOST_NAME`, or the organisation's own name under `single`
 *     scope), the heading carries no name at all. It does not fall back to
 *     "Tdev Festival", to the hostname, or to anything else. The page belongs to a
 *     person; naming it for them would be a small lie on the most prominent
 *     line of the site.
 *  2. **A single-organisation box is never dressed up as a directory.**
 *     `multi_org` is the only switch for per-event organisation labels, and
 *     it comes from the host itself, not from counting the events currently
 *     on screen — a search that happens to match one organisation must not
 *     make a box present as a single venue.
 *
 * Every function tolerates a missing or malformed envelope by degrading to
 * the honest, name-free, label-free single-tenant presentation, so an older
 * server or a failed request can never produce marketplace copy.
 *
 * The envelope arrives over the wire, so nothing in it is trusted at its
 * declared type — every field below is `unknown` and narrowed by hand at the
 * point of use, exactly as the runtime checks already did before this file
 * had types.
 */

export interface HostOrgRef {
    id?: unknown;
    name?: unknown;
    slug?: unknown;
}

export interface HostEnvelope {
    scope?: unknown;
    name?: unknown;
    multi_org?: unknown;
    peers_included?: unknown;
    organisations?: unknown;
    org?: HostOrgRef;
}

export type MaybeHost = HostEnvelope | null | undefined;

export interface EventOrgRef {
    id?: unknown;
    org_id?: unknown;
}

/**
 * True when this box hosts more than one organisation and events should
 * therefore be labelled with the organisation they belong to.
 */
export function showsOrgLabels(host: MaybeHost) {
    return Boolean(host?.multi_org);
}

/**
 * True when this host displays BORROWED LISTINGS — events belonging to
 * another organiser, which this box pulled from a publisher its operator
 * enrolled by hand.
 *
 * Two switches stand between an operator and a borrowed listing on their
 * front page, and they answer two different questions:
 *
 *  1. Per publisher, on the server: does this box PULL that organiser's
 *     programme at all? (`feed_subscribe`, off until the operator says so.)
 *  2. This one: is what was pulled shown to the PUBLIC? That is
 *     `TDEV_HOST_SCOPE=peers`, and the envelope carries the answer as
 *     `peers_included`.
 *
 * Both are off by default, so an operator who has enrolled an organiser and
 * fetched their events still shows nobody else's programme on their own front
 * page until they ask for it. Reading someone's feed and publishing it are
 * separate decisions; this is the second one.
 *
 * Strictly `=== true`. A missing envelope, an older server that never sends
 * the field, a failed request, a truthy-but-not-true value — every one of them
 * resolves to NOT showing another organiser's events on this operator's page.
 * The unsafe direction here is showing something the operator did not publish,
 * so absence of an answer is never taken as yes.
 */
export function showsPeerEvents(host: MaybeHost) {
    return host?.peers_included === true;
}

/** Every organisation this listing can contain. Always an array. */
export function hostOrgs(host: MaybeHost): HostOrgRef[] {
    // Array.isArray narrows to any[] (a known imprecision in TS's own
    // Array.isArray typing, not something local to this file), so returning
    // it directly as HostOrgRef[] would be an unverified cast. Filtering to
    // non-null objects is the real (if loose) guarantee HostOrgRef asks
    // for — every field on it is optional, so any plain object structurally
    // satisfies it, and this at least rejects a malformed element that
    // isn't an object at all (a string, a number, null).
    if (!Array.isArray(host?.organisations)) return [];
    return host.organisations.filter((o: unknown): o is HostOrgRef => typeof o === 'object' && o !== null);
}

/** The organisation's own name, or '' when absent or not actually a string —
 * every field on the wire envelope is `unknown` (see the file doc comment),
 * so this is the one place that turns `org.name` into text, and it never
 * hands back anything but a string a visitor could read. */
function orgName(org: HostOrgRef | null | undefined): string {
    return typeof org?.name === 'string' ? org.name : '';
}

/**
 * The organisation an event belongs to, or null when the envelope does not
 * name it. Null means "say nothing" — never "guess".
 */
export function orgForEvent(host: MaybeHost, event: EventOrgRef | null | undefined) {
    if (!event?.org_id) return null;
    return hostOrgs(host).find((o) => o.id === event.org_id) || null;
}

/**
 * Where an organisation's label links to: this same listing, narrowed to
 * that organisation.
 *
 * It is not a separate page. An organisation's own page does now exist —
 * `/o/{slug}`, behind `orgPageHref()` in `@/lib/org-page` — but this is the
 * LABEL's destination, and a label in a filter row should filter: following
 * it keeps the visitor's search and category, which is exactly what `?host=`
 * is for. Leaving the app to a server-rendered page would throw both away.
 * `org-page.test.js` pins the two as different destinations so they cannot be
 * quietly collapsed into one.
 */
export function orgHref(org: HostOrgRef | null | undefined) {
    const slug = typeof org?.slug === 'string' ? org.slug : '';
    return slug ? `/events?host=${encodeURIComponent(slug)}` : '/events';
}

/** The operator's name for this host, or '' when they have not given one. */
export function hostName(host: MaybeHost) {
    const name = typeof host?.name === 'string' ? host.name.trim() : '';
    return name;
}

/**
 * The listing heading. "What's on at The Bijou" when the host is named,
 * "What's on" when it is not, and "Events from The Bijou" when the visitor
 * has narrowed the listing to one organisation on a box that hosts several.
 */
export function hostHeading(host: MaybeHost) {
    const org = orgName(host?.org);
    if (org) return `Events from ${org}`;
    const name = hostName(host);
    return name ? `What's on at ${name}` : "What's on";
}

/**
 * The line under the heading. It says who is selling, which is the fact a
 * buyer actually needs, and claims nothing about anywhere else.
 */
export function hostSubheading(host: MaybeHost) {
    const org = orgName(host?.org);
    if (org) return `Tickets sold by ${org}.`;
    const orgs = hostOrgs(host);
    if (showsOrgLabels(host)) {
        return `Tickets for ${orgs.length} organisations on this site.`;
    }
    const name = hostName(host) || orgName(orgs[0]);
    return name ? `Tickets sold by ${name}.` : 'Tickets sold direct by the people running these events.';
}

/**
 * What an empty listing says. NOT "check back soon, new events are added all
 * the time" — nobody adds events to somebody else's box, and on a venue
 * between programmes that sentence is simply untrue.
 */
export const EMPTY_HEADING = 'Nothing on sale right now';

export function emptyDescription(host: MaybeHost) {
    const name = orgName(host?.org) || hostName(host) || orgName(hostOrgs(host)[0]);
    return name ? `${name} has no tickets on sale at the moment.` : 'There are no tickets on sale at the moment.';
}
