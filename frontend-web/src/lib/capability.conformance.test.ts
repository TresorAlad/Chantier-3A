// Conformance vectors: the browser verifier, held to the same wire format.
//
// docs/ticket-format-vectors.json is a frozen corpus of issued tokens and
// verification outcomes. internal/tickets/conformance_test.go runs it against
// the Go implementation; this file runs the SAME file against the JavaScript
// one that actually ships to a gate device. Two implementations that both
// pass this corpus cannot disagree about whether a ticket is admissible,
// which is the whole reason the corpus exists.
//
// Uses node:test — Node's built-in runner — deliberately: the gate verifier is
// the last thing that should acquire a new dependency, and a test harness that
// only runs when an npm install succeeded is a test harness that skips.
//
// Run with: npm test   (from web/)

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import {
    verifyCapability,
    verifyWithRing,
    publicKeyToBytes,
    CURRENT_VERSION,
    CapabilityError,
    type CapabilityPayload,
    type KeyRing,
} from './capability.ts';

interface IssueVector {
    name: string;
    token: string;
    payload: CapabilityPayload;
    payload_json: string;
}

interface VerifyVector {
    name: string;
    key: string;
    now_unix: number;
    result: string;
    token: string;
    tid?: string;
    error?: string;
}

interface VerifyWithRingVector {
    name: string;
    ring: Record<string, string>;
    now_unix: number;
    result: string;
    token: string;
    error?: string;
}

interface Vectors {
    format: string;
    payload_version: number;
    keys: Record<string, { public_key_b64url: string }>;
    issue: IssueVector[];
    verify: VerifyVector[];
    verify_with_ring: VerifyWithRingVector[];
    error_codes: string[];
}

const here = dirname(fileURLToPath(import.meta.url));
const vectorsPath = resolve(here, '../../../backend-python/docs/pass-format-vectors.json');

// A trusted, repo-local fixture (not external input) — cast through unknown
// rather than left as JSON.parse's bare `any`, so this is an explicit,
// visible "we trust this file's shape" rather than an unverified assignment.
// The MIN_ISSUE/MIN_VERIFY/MIN_RING floors below are the actual guard
// against a truncated or mis-shaped corpus passing silently.
const vectors = JSON.parse(readFileSync(vectorsPath, 'utf8')) as unknown as Vectors;

// Floors, not targets. They exist so a truncated or mis-parsed vectors file
// fails loudly instead of passing by running nothing. Raise them when the
// corpus grows; they are mirrored in internal/tickets/conformance_test.go.
const MIN_ISSUE = 3;
const MIN_VERIFY = 25;
const MIN_RING = 5;

const keyBytes = (name: string) => {
    const k = vectors.keys[name];
    assert.ok(k, `vectors reference unknown key "${name}"`);
    return publicKeyToBytes(k.public_key_b64url);
};

test('vectors file is the corpus this build expects', () => {
    assert.equal(vectors.format, 'chantier3a-capability-token');
    assert.equal(
        vectors.payload_version,
        CURRENT_VERSION,
        'vectors declare a different payload version than this build verifies',
    );
    assert.ok(
        vectors.issue.length >= MIN_ISSUE,
        `only ${vectors.issue.length} issue vectors, want at least ${MIN_ISSUE}`,
    );
    assert.ok(
        vectors.verify.length >= MIN_VERIFY,
        `only ${vectors.verify.length} verify vectors, want at least ${MIN_VERIFY}`,
    );
    assert.ok(
        vectors.verify_with_ring.length >= MIN_RING,
        `only ${vectors.verify_with_ring.length} ring vectors, want at least ${MIN_RING}`,
    );

    // Every documented error code must be produced by at least one vector,
    // so a rejection path cannot quietly stop being tested.
    const exercised = new Set(
        [...vectors.verify, ...vectors.verify_with_ring].map((v) => v.error).filter(Boolean),
    );
    for (const code of vectors.error_codes) {
        assert.ok(exercised.has(code), `error code "${code}" is documented but no vector exercises it`);
    }
});

test('frozen tokens verify against the published issuer key', (t) => {
    const pub = keyBytes('issuer');
    let ran = 0;
    for (const vec of vectors.issue) {
        t.test(vec.name, () => {
            const payload = verifyCapability(vec.token, pub, new Date(vec.payload.iat * 1000));
            assert.deepEqual(payload, vec.payload, 'decoded payload differs from the vector');
            // The payload_json field is what an implementer reads to see the
            // exact signed bytes; it must round-trip to the same object.
            assert.deepEqual(JSON.parse(vec.payload_json), vec.payload);
        });
        ran++;
    }
    assert.equal(ran, vectors.issue.length);
});

test('verify vectors', (t) => {
    let ran = 0;
    for (const vec of vectors.verify) {
        t.test(vec.name, () => {
            const pub = keyBytes(vec.key);
            const now = new Date(vec.now_unix * 1000);

            if (vec.result === 'ok') {
                const payload = verifyCapability(vec.token, pub, now);
                if (vec.tid) assert.equal(payload.tid, vec.tid);
                return;
            }
            assert.equal(vec.result, 'error', `unknown vector result "${vec.result}"`);

            let thrown: unknown;
            try {
                verifyCapability(vec.token, pub, now);
            } catch (err) {
                thrown = err;
            }
            assert.ok(thrown, `expected error "${vec.error}", got success`);
            assert.ok(
                thrown instanceof CapabilityError,
                `expected a CapabilityError, got ${(thrown as Error | undefined)?.name}: ${(thrown as Error | undefined)?.message}`,
            );
            assert.equal(
                thrown.code,
                vec.error,
                `expected code "${vec.error}", got "${thrown.code}" (${thrown.message})`,
            );
        });
        ran++;
    }
    assert.equal(ran, vectors.verify.length);
});

test('verify_with_ring vectors', (t) => {
    let ran = 0;
    for (const vec of vectors.verify_with_ring) {
        t.test(vec.name, () => {
            const ring: KeyRing = {};
            for (const [kid, encoded] of Object.entries(vec.ring)) {
                ring[kid] = publicKeyToBytes(encoded);
            }
            const now = new Date(vec.now_unix * 1000);

            if (vec.result === 'ok') {
                const payload = verifyWithRing(vec.token, ring, now);
                assert.ok(payload, 'expected a payload on success');
                return;
            }
            assert.equal(vec.result, 'error', `unknown vector result "${vec.result}"`);

            let thrown: unknown;
            try {
                verifyWithRing(vec.token, ring, now);
            } catch (err) {
                thrown = err;
            }
            assert.ok(thrown, `expected error "${vec.error}", got success`);
            assert.ok(
                thrown instanceof CapabilityError,
                `expected a CapabilityError, got ${(thrown as Error | undefined)?.name}: ${(thrown as Error | undefined)?.message}`,
            );
            assert.equal(
                thrown.code,
                vec.error,
                `expected code "${vec.error}", got "${thrown.code}" (${thrown.message})`,
            );
        });
        ran++;
    }
    assert.equal(ran, vectors.verify_with_ring.length);
});
