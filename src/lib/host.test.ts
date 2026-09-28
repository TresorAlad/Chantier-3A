import assert from 'node:assert/strict';
import test from 'node:test';

import {
    EMPTY_HEADING,
    emptyDescription,
    hostHeading,
    hostName,
    hostOrgs,
    hostSubheading,
    orgForEvent,
    orgHref,
    showsOrgLabels,
    showsPeerEvents,
} from './host.ts';

const bijou = { id: 'org_1', name: 'The Bijou', slug: 'the-bijou' };
const nightMarket = { id: 'org_2', name: 'Night Market', slug: 'night-market' };

test('an unnamed host is not given a name', () => {
    const host = { scope: 'own', organisations: [], multi_org: false, peers_included: false };
    assert.equal(hostName(host), '');
    assert.equal(hostHeading(host), "What's on");
    assert.equal(emptyDescription(host), 'There are no tickets on sale at the moment.');
});

test('a named host is named', () => {
    const host = { scope: 'single', name: 'The Bijou', organisations: [bijou], multi_org: false };
    assert.equal(hostHeading(host), "What's on at The Bijou");
    assert.equal(hostSubheading(host), 'Tickets sold by The Bijou.');
    assert.equal(emptyDescription(host), 'The Bijou has no tickets on sale at the moment.');
});

test('a single-organisation box shows no organisation labels', () => {
    const host = { scope: 'own', organisations: [bijou], multi_org: false };
    assert.equal(showsOrgLabels(host), false);
});

test('a multi-organisation box labels each event and links the label to that organisation', () => {
    const host = { scope: 'own', organisations: [bijou, nightMarket], multi_org: true };
    assert.equal(showsOrgLabels(host), true);
    assert.equal(hostSubheading(host), 'Tickets for 2 organisations on this site.');

    const org = orgForEvent(host, { id: 'ev_1', org_id: 'org_2' });
    assert.deepEqual(org, nightMarket);
    assert.equal(orgHref(org), '/events?host=night-market');
});

test('an event whose organisation the envelope does not name is not labelled', () => {
    const host = { scope: 'own', organisations: [bijou], multi_org: true };
    assert.equal(orgForEvent(host, { id: 'ev_1', org_id: 'org_unknown' }), null);
    assert.equal(orgForEvent(host, { id: 'ev_1' }), null);
});

test('a narrowed listing says which organisation it is showing', () => {
    const host = { scope: 'own', organisations: [bijou, nightMarket], multi_org: true, org: nightMarket };
    assert.equal(hostHeading(host), 'Events from Night Market');
    assert.equal(hostSubheading(host), 'Tickets sold by Night Market.');
    assert.equal(emptyDescription(host), 'Night Market has no tickets on sale at the moment.');
});

test('an org slug is URL-encoded, never interpolated raw', () => {
    assert.equal(orgHref({ id: 'x', name: 'x', slug: 'a b/c?d' }), '/events?host=a%20b%2Fc%3Fd');
    assert.equal(orgHref(null), '/events');
    assert.equal(orgHref({ id: 'x', name: 'x' }), '/events');
});

// The degradation rule: no envelope at all must produce the honest,
// name-free, label-free single-tenant page — never marketplace copy.
test('a missing or malformed envelope degrades to the single-tenant presentation', () => {
    for (const host of [undefined, null, {}, { organisations: 'nope', multi_org: 'yes' }]) {
        assert.equal(showsOrgLabels(host), host?.multi_org === 'yes');
        assert.deepEqual(hostOrgs(host), []);
        assert.equal(hostName(host), '');
        assert.equal(orgForEvent(host, { org_id: 'org_1' }), null);
    }
    assert.equal(hostHeading(undefined), "What's on");
    assert.equal(emptyDescription(undefined), 'There are no tickets on sale at the moment.');
    assert.equal(EMPTY_HEADING, 'Nothing on sale right now');
});

// ── borrowed listings: does this host display another organiser's events ────

test('a host says so before another organiser\'s events are shown on its page', () => {
    assert.equal(showsPeerEvents({ scope: 'peers', organisations: [bijou], peers_included: true }), true);
});

test('the default scope does not put another organiser\'s events on this page', () => {
    assert.equal(showsPeerEvents({ scope: 'own', organisations: [bijou], peers_included: false }), false);
    assert.equal(showsPeerEvents({ scope: 'single', name: 'The Bijou', organisations: [bijou], peers_included: false }), false);
});

// The unsafe direction is publishing somebody else's programme on an
// operator's page without being told to. So anything that is not an explicit
// true — a missing envelope, an older server that never sends the field, a
// failed request, a truthy string — resolves to showing nothing.
test('a missing, malformed or merely truthy envelope shows no borrowed listings', () => {
    const notTrue = [
        undefined,
        null,
        {},
        { scope: 'peers' },
        { peers_included: false },
        { peers_included: 'true' },
        { peers_included: 1 },
        { peers_included: null },
        { peers_included: [] },
    ];
    for (const host of notTrue) {
        assert.equal(showsPeerEvents(host), false, `expected false for ${JSON.stringify(host)}`);
    }
});
