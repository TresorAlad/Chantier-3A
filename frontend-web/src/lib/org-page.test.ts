import assert from 'node:assert/strict';
import test from 'node:test';

import { orgPageHref } from './org-page.ts';
import { orgHref } from './host.ts';

const bijou = { id: 'org_1', name: 'The Bijou', slug: 'the-bijou' };

test('an organisation links to its own page by slug', () => {
    assert.equal(orgPageHref(bijou), '/o/the-bijou');
});

test('an organisation with no slug falls back to its id, which /o/ also accepts', () => {
    assert.equal(orgPageHref({ id: 'org_1', name: 'The Bijou' }), '/o/org_1');
});

test('there is no organisation page for no organisation', () => {
    // Null, not a fallback URL: a guessed organisation page is a 404, and a
    // caller that renders a link to it has shipped a dead link.
    assert.equal(orgPageHref(null), null);
    assert.equal(orgPageHref(undefined), null);
    assert.equal(orgPageHref({}), null);
    assert.equal(orgPageHref({ name: 'no slug, no id' }), null);
});

test('a reference is encoded into one path segment', () => {
    // /o/{ref} is a single chi path parameter. A reference carrying a slash,
    // a query or a fragment must not rewrite the URL around it.
    assert.equal(orgPageHref({ slug: 'a b/c?d#e' }), '/o/a%20b%2Fc%3Fd%23e');
});

test('the organisation PAGE and the organisation LABEL are different destinations', () => {
    // Guards against the two being quietly collapsed later. `orgHref` narrows
    // the in-app listing and keeps the visitor's filters; `orgPageHref` is the
    // publisher's own standalone page, which is what a link from outside the
    // app — or from another operator's box — has to point at.
    assert.notEqual(orgPageHref(bijou), orgHref(bijou));
    assert.equal(orgHref(bijou), '/events?host=the-bijou');
});
