// The gate's decision, exercised end to end without a browser.
//
// `decideAdmission` is the function that decides whether a person walks
// through a door while the venue has no network. Every branch is covered
// here, including the two that only occur when something is broken — a
// signature that does not verify, and a local dedupe store that throws — since
// those are exactly the paths where "fail closed" either holds or does not.
//
// The two effects are injected, so these tests use a real capability token
// signed with a real Ed25519 key (via lib/capability.js, the same code the
// scanner runs) over a fake dedupe store. Nothing is stubbed that matters: the
// signature checking is the genuine article.

import test from 'node:test';
import assert from 'node:assert/strict';
import { ed25519 } from '@noble/curves/ed25519';

import { decideAdmission, describeError, RESULT, type DecideAdmissionArgs } from './scan-decision.ts';
import { verifyWithRing, type KeyRing } from './capability.ts';

// ── Fixtures ────────────────────────────────────────────────────────────────

const EVENT_ID = 'evt_glastonbury';
const KID = 'k1';

function b64url(bytes: Uint8Array) {
    return Buffer.from(bytes).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

const secretKey = ed25519.utils.randomPrivateKey();
const publicKey = ed25519.getPublicKey(secretKey);
const keyRing: KeyRing = { [KID]: publicKey };

interface MintTicketOptions {
    tid?: string;
    eid?: string;
    nm?: string | null;
    iat?: number;
    exp?: number;
    nbf?: number;
    kid?: string;
    signer?: Uint8Array;
}

interface RawPayload {
    v: number;
    tid: string;
    eid: string;
    nm?: string | null;
    iat: number;
    exp: number;
    kid: string;
    nbf?: number;
}

/**
 * mintTicket produces a genuinely signed tdev capability token, the same
 * shape internal/tickets issues. Signed with `signer` so a test can also mint
 * one signed by the WRONG key.
 */
function mintTicket({
    tid = 'tkt_001',
    eid = EVENT_ID,
    nm = 'Ada Lovelace',
    iat = Math.floor(Date.now() / 1000) - 60,
    exp = Math.floor(Date.now() / 1000) + 3600,
    nbf,
    kid = KID,
    signer = secretKey,
}: MintTicketOptions = {}) {
    const payload: RawPayload = { v: 1, tid, eid, nm, iat, exp, kid };
    // `nm: null` means "mint a ticket with no holder name". A default
    // parameter cannot express that — passing `undefined` just re-selects the
    // default — so null is the omission signal and is deleted here.
    if (payload.nm === null) delete payload.nm;
    if (nbf !== undefined) payload.nbf = nbf;
    const payloadBytes = new TextEncoder().encode(JSON.stringify(payload));
    // Signed over the DECODED payload bytes, not the base64url text —
    // matching verifyCapability, which verifies against `body`. Signing the
    // encoded string instead produces a token that looks structurally perfect
    // and fails every signature check, which is a confusing way to discover
    // one's fixture is wrong.
    const sig = ed25519.sign(payloadBytes, signer);
    return `chantier3a.${b64url(payloadBytes)}.${b64url(sig)}`;
}

/** A decideAdmission call with sensible defaults; override per test. */
function decide(overrides: Partial<DecideAdmissionArgs> = {}) {
    return decideAdmission({
        token: overrides.token ?? mintTicket(),
        eventId: EVENT_ID,
        keyRing,
        ticketIndexSet: new Set(['tkt_001']),
        ticketIndexPresent: true,
        admittedIndexSet: new Set(),
        verify: verifyWithRing,
        wasAdmitted: () => Promise.resolve(false),
        ...overrides,
    });
}

// ── The happy path ──────────────────────────────────────────────────────────

test('a valid ticket at the right gate is admitted', async (t) => {
    await t.test('admits, and carries the holder through for the door staff to read', async () => {
        const out = await decide();
        assert.equal(out.result, RESULT.ADMITTED);
        assert.equal(out.ticketId, 'tkt_001');
        assert.equal(out.holderName, 'Ada Lovelace');
        assert.equal(out.note, null);
    });

    await t.test('needs no network, no server and no clock authority beyond `now`', async () => {
        // The whole claim of the product. If this test ever needs a fetch
        // stub, the offline guarantee has been broken.
        const out = await decideAdmission({
            token: mintTicket(),
            eventId: EVENT_ID,
            keyRing,
            ticketIndexSet: new Set(['tkt_001']),
            ticketIndexPresent: true,
            admittedIndexSet: new Set(),
            verify: verifyWithRing,
            wasAdmitted: () => Promise.resolve(false),
            now: new Date(),
        });
        assert.equal(out.result, RESULT.ADMITTED);
    });

    await t.test('a ticket with no holder name still admits', async () => {
        const out = await decide({ token: mintTicket({ nm: null }) });
        assert.equal(out.result, RESULT.ADMITTED);
        assert.equal(out.holderName, null);
    });
});

// ── Refusals ────────────────────────────────────────────────────────────────

test('a ticket that does not verify is refused', async (t) => {
    await t.test('signed by a key that is not in the ring', async () => {
        const other = ed25519.utils.randomPrivateKey();
        const out = await decide({ token: mintTicket({ signer: other }) });
        assert.equal(out.result, RESULT.INVALID);
        assert.match(out.note!, /signature/i);
    });

    await t.test('a kid the ring has never heard of', async () => {
        const out = await decide({ token: mintTicket({ kid: 'k-unknown' }) });
        assert.equal(out.result, RESULT.INVALID);
        assert.equal(out.note, 'Unknown signing key');
    });

    await t.test('a tampered payload', async () => {
        const good = mintTicket();
        const [prefix, payload, sig] = good.split('.');
        if (!prefix || !payload || !sig) throw new Error('mintTicket() must produce a 3-part token');
        const decoded = JSON.parse(Buffer.from(payload, 'base64url').toString()) as Record<string, unknown>;
        decoded.tid = 'tkt_forged';
        const tampered = b64url(new TextEncoder().encode(JSON.stringify(decoded)));
        const out = await decide({ token: `${prefix}.${tampered}.${sig}` });
        assert.equal(out.result, RESULT.INVALID);
    });

    await t.test('garbage that is not a token at all', async () => {
        const out = await decide({ token: 'https://example.com/not-a-ticket' });
        assert.equal(out.result, RESULT.INVALID);
    });

    await t.test('an expired ticket', async () => {
        const past = Math.floor(Date.now() / 1000) - 10;
        const out = await decide({ token: mintTicket({ iat: past - 100, exp: past }) });
        assert.equal(out.result, RESULT.INVALID);
        assert.equal(out.note, 'Ticket expired');
    });

    await t.test('refusal NEVER records a ticket id from an unverified token', async () => {
        // An id parsed out of a token that failed verification is
        // attacker-chosen text. It must not reach the admission log.
        const other = ed25519.utils.randomPrivateKey();
        const out = await decide({ token: mintTicket({ tid: 'tkt_attacker', signer: other }) });
        assert.equal(out.result, RESULT.INVALID);
        assert.equal(out.ticketId, null);
        assert.equal(out.holderName, null);
    });
});

test('a valid ticket for a different event is its own verdict', async () => {
    // Distinct from `invalid`: the guest is at the wrong door, not holding a
    // bad ticket, and the door staff need to be told which.
    const out = await decide({ token: mintTicket({ eid: 'evt_somewhere_else' }) });
    assert.equal(out.result, RESULT.WRONG_EVENT);
    assert.equal(out.ticketId, 'tkt_001');
    assert.match(out.note!, /different event/i);
});

// ── The authoritative index ─────────────────────────────────────────────────

test('the ticket index decides what a signature cannot', async (t) => {
    await t.test('a refunded ticket verifies but is refused', async () => {
        // Nothing about the signature changes when a ticket is refunded. The
        // index is the only thing that can catch this.
        const out = await decide({ ticketIndexSet: new Set(['tkt_someone_else']) });
        assert.equal(out.result, RESULT.INVALID);
        assert.match(out.note!, /revoked or not issued/i);
        assert.equal(out.ticketId, null);
    });

    await t.test('an EMPTY authoritative index admits nobody', async () => {
        // The subtle one, and the reason ticketIndexPresent exists as a
        // separate flag. A cancelled event ships an empty-but-authoritative
        // index; reading "empty" as "no data" would re-admit every ticket
        // anybody still had in their pocket.
        const out = await decide({ ticketIndexSet: new Set(), ticketIndexPresent: true });
        assert.equal(out.result, RESULT.INVALID);
    });

    await t.test('an empty NON-authoritative index falls back to signature-only', async () => {
        // A legacy bundle without the flag. Absence of data is not evidence of
        // revocation, so the signature is allowed to stand on its own.
        const out = await decide({ ticketIndexSet: new Set(), ticketIndexPresent: false });
        assert.equal(out.result, RESULT.ADMITTED);
    });

    await t.test('authority is read from the flag, never inferred from length', async () => {
        // Same empty set, opposite answers, decided purely by the flag.
        const authoritative = await decide({ ticketIndexSet: new Set(), ticketIndexPresent: true });
        const legacy = await decide({ ticketIndexSet: new Set(), ticketIndexPresent: false });
        assert.notEqual(authoritative.result, legacy.result);
    });
});

// ── Duplicates: detected, never prevented ───────────────────────────────────

test('duplicates are detected and distinguished by where they happened', async (t) => {
    await t.test('a second scan on THIS device is a duplicate', async () => {
        const out = await decide({ wasAdmitted: () => Promise.resolve(true) });
        assert.equal(out.result, RESULT.DUPLICATE);
        assert.equal(out.ticketId, 'tkt_001');
        assert.match(out.note!, /this gate/i);
    });

    await t.test('a ticket admitted at ANOTHER gate is a duplicate with a different note', async () => {
        // The only channel by which a disconnected gate learns about another
        // gate's admission: the bundle it last pulled.
        const out = await decide({ admittedIndexSet: new Set(['tkt_001']) });
        assert.equal(out.result, RESULT.DUPLICATE);
        assert.match(out.note!, /another gate/i);
    });

    await t.test('the two duplicate notes are distinguishable to the operator', async () => {
        const local = await decide({ wasAdmitted: () => Promise.resolve(true) });
        const remote = await decide({ admittedIndexSet: new Set(['tkt_001']) });
        assert.notEqual(local.note, remote.note);
    });

    await t.test('the other gate is only known if the bundle knew — this is not prevention', async () => {
        // With an admittedIndex that predates the other gate's scan, this gate
        // admits, and SO DOES the other one. That is the documented,
        // unavoidable behaviour of two partitioned gates, and this test pins
        // it so nobody "fixes" it into a false promise.
        const out = await decide({ admittedIndexSet: new Set(), wasAdmitted: () => Promise.resolve(false) });
        assert.equal(out.result, RESULT.ADMITTED);
    });

    await t.test('a stale admittedIndex is consulted before the local log', async () => {
        // Cross-gate knowledge wins over a clean local log: the ticket is
        // reported as already inside even though this device never saw it.
        const out = await decide({
            admittedIndexSet: new Set(['tkt_001']),
            wasAdmitted: () => Promise.reject(new Error('local store must not be consulted once the bundle already answered')),
        });
        assert.equal(out.result, RESULT.DUPLICATE);
    });
});

// ── Fail closed ─────────────────────────────────────────────────────────────

test('a broken local store refuses rather than guesses', async (t) => {
    await t.test('a throwing dedupe lookup yields invalid, never admitted', async () => {
        // Storage evicted, over quota, or a private mode that pretends
        // IndexedDB works. Admitting here would turn one broken phone into an
        // unbounded number of duplicate entries.
        const out = await decide({
            wasAdmitted: () => Promise.reject(new Error('QuotaExceededError')),
        });
        assert.equal(out.result, RESULT.INVALID);
        assert.match(out.note!, /dedupe check failed/i);
        assert.match(out.note!, /QuotaExceededError/);
    });

    await t.test('the fail-closed path records no ticket id either', async () => {
        const out = await decide({
            wasAdmitted: () => Promise.reject(new Error('boom')),
        });
        assert.equal(out.ticketId, null);
    });

    await t.test('a verifier that throws a bare value does not crash the gate', async () => {
        const out = await decide({
            verify: () => {
                // Deliberately not an Error — this test's entire point is
                // that decideAdmission survives a badly-behaved verify
                // callback throwing a bare value, not just a well-formed one.
                // eslint-disable-next-line @typescript-eslint/only-throw-error
                throw 'not an Error object';
            },
        });
        assert.equal(out.result, RESULT.INVALID);
        assert.ok(typeof out.note === 'string' && out.note.length > 0);
    });
});

// ── Check ordering is part of the contract ──────────────────────────────────

test('checks run in the documented order', async (t) => {
    await t.test('wrong event beats a missing ticket index entry', async () => {
        // A ticket for another event should say so, rather than being reported
        // as revoked here — which is what checking the index first would do.
        const out = await decide({
            token: mintTicket({ eid: 'evt_other' }),
            ticketIndexSet: new Set(),
            ticketIndexPresent: true,
        });
        assert.equal(out.result, RESULT.WRONG_EVENT);
    });

    await t.test('revocation beats the admitted index', async () => {
        // A refunded ticket that somebody already got in on is still reported
        // as invalid: the refund is the more important fact at the door.
        const out = await decide({
            ticketIndexSet: new Set(),
            ticketIndexPresent: true,
            admittedIndexSet: new Set(['tkt_001']),
        });
        assert.equal(out.result, RESULT.INVALID);
    });

    await t.test('a bad signature beats everything', async () => {
        const other = ed25519.utils.randomPrivateKey();
        const out = await decide({
            token: mintTicket({ eid: 'evt_other', signer: other }),
            ticketIndexSet: new Set(),
            ticketIndexPresent: true,
        });
        assert.equal(out.result, RESULT.INVALID);
    });
});

// ── Error copy ──────────────────────────────────────────────────────────────

test('describeError maps every capability code to door-side language', async (t) => {
    const cases = [
        ['malformed', /malformed/i],
        ['unsupported_version', /version/i],
        ['bad_signature', /signature/i],
        ['not_yet_valid', /not valid yet/i],
        ['expired', /expired/i],
        ['unknown_kid', /signing key/i],
    ] as Array<[string, RegExp]>;
    for (const [code, pattern] of cases) {
        await t.test(code, () => {
            assert.match(describeError({ code }), pattern);
        });
    }

    await t.test('an unknown code still produces something sayable', () => {
        assert.equal(describeError({ code: 'wat', message: 'the reader is upside down' }), 'the reader is upside down');
        assert.equal(describeError(undefined), 'Invalid ticket');
    });
});
