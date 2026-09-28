// lib/capability.js
//
// Browser-side mirror of internal/tickets/capability.go's Verify(). This is
// the piece that makes offline gate scanning possible: it is PURE (no
// network, no IndexedDB, no wall-clock access beyond an injected `now`) so it
// can run entirely inside the scanner page with the device unplugged from
// the network.
//
// Wire format: chantier3a.<base64url(payload_json)>.<base64url(ed25519_sig)>
// The signature covers the raw decoded payload bytes, verified with the
// event's Ed25519 public key pinned ahead of time from the scan bundle.
//
// This file and internal/tickets/capability.go must agree on every accept and
// every reject. docs/ticket-format-vectors.json is the shared corpus that
// holds them to it, run here by capability.conformance.test.js and in Go by
// internal/tickets/conformance_test.go. Anything this verifier accepts that Go
// rejects is a hole at the gate, so the strictness below (base64url alphabet,
// unknown payload fields, field types) is deliberate and load-bearing, not
// defensive noise — see docs/TICKET-FORMAT.md.

import { ed25519 } from '@noble/curves/ed25519';

export const CURRENT_VERSION = 1;
const TOKEN_PREFIX = 'chantier3a';

export const CapabilityErrorCode = {
    MALFORMED: 'malformed',
    UNSUPPORTED_VERSION: 'unsupported_version',
    BAD_SIGNATURE: 'bad_signature',
    NOT_YET_VALID: 'not_yet_valid',
    EXPIRED: 'expired',
    UNKNOWN_KID: 'unknown_kid',
} as const;

export type CapabilityErrorCodeValue = (typeof CapabilityErrorCode)[keyof typeof CapabilityErrorCode];

export class CapabilityError extends Error {
    code: CapabilityErrorCodeValue;

    constructor(code: CapabilityErrorCodeValue, message: string) {
        super(message);
        this.name = 'CapabilityError';
        this.code = code;
    }
}

/** The decoded, verified capability payload — see docs/TICKET-FORMAT.md. */
export interface CapabilityPayload {
    v: number;
    tid: string;
    eid: string;
    tt: string;
    kid: string;
    sub: string;
    nm: string;
    iat: number;
    nbf?: number;
    exp?: number;
    seat?: string;
}

/** kid -> pinned Ed25519 public key bytes, as delivered in a scan bundle. */
export type KeyRing = Record<string, Uint8Array>;

// Only the RFC 4648 base64url alphabet, with padding omitted. `=` (padding),
// `+` and `/` (the standard alphabet) are all rejected rather than quietly
// re-mapped, matching Go's base64.RawURLEncoding — a token encoded the wrong
// way is malformed, not something to guess at.
const BASE64URL_RE = /^[A-Za-z0-9_-]*$/;

function base64UrlToBytes(b64url: string): Uint8Array {
    if (!BASE64URL_RE.test(b64url)) {
        throw new CapabilityError(
            CapabilityErrorCode.MALFORMED,
            'segment is not unpadded base64url (RFC 4648 §5)',
        );
    }
    let base64 = b64url.replace(/-/g, '+').replace(/_/g, '/');
    const pad = base64.length % 4;
    if (pad === 2) base64 += '==';
    else if (pad === 3) base64 += '=';
    else if (pad !== 0) throw new CapabilityError(CapabilityErrorCode.MALFORMED, 'invalid base64url length');

    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return bytes;
}

// The complete set of payload fields, and the JSON type each must have.
// Anything outside this map is rejected outright rather than ignored, so a
// token cannot smuggle a field that some later code might trust without it
// ever having been validated here. This mirrors Go's
// json.Decoder.DisallowUnknownFields plus its typed decode into Payload.
const PAYLOAD_FIELDS: Record<string, 'int' | 'string'> = {
    v: 'int',
    tid: 'string',
    eid: 'string',
    tt: 'string',
    kid: 'string',
    sub: 'string',
    nm: 'string',
    iat: 'int',
    nbf: 'int',
    exp: 'int',
    seat: 'string',
};

/**
 * Structural validation of a parsed payload, mirroring what Go's typed
 * decode enforces for free. `null` is treated as absent, because that is what
 * encoding/json does when unmarshalling null into a string or int field.
 */
function validatePayloadShape(payload: unknown): asserts payload is CapabilityPayload {
    if (payload === null || typeof payload !== 'object' || Array.isArray(payload)) {
        throw new CapabilityError(CapabilityErrorCode.MALFORMED, 'payload is not a JSON object');
    }
    for (const [key, value] of Object.entries(payload)) {
        const want = PAYLOAD_FIELDS[key];
        if (!want) {
            throw new CapabilityError(CapabilityErrorCode.MALFORMED, `unknown payload field "${key}"`);
        }
        if (value === null) continue; // absent, per encoding/json
        if (want === 'string' && typeof value !== 'string') {
            throw new CapabilityError(CapabilityErrorCode.MALFORMED, `payload field "${key}" must be a string`);
        }
        if (want === 'int' && !Number.isInteger(value)) {
            throw new CapabilityError(CapabilityErrorCode.MALFORMED, `payload field "${key}" must be an integer`);
        }
    }
}

function bytesToUtf8(bytes: Uint8Array): string {
    return new TextDecoder('utf-8', { fatal: true }).decode(bytes);
}

function hexToBytes(hex: string): Uint8Array {
    const clean = hex.trim();
    const bytes = new Uint8Array(clean.length / 2);
    for (let i = 0; i < bytes.length; i++) {
        bytes[i] = parseInt(clean.substr(i * 2, 2), 16);
    }
    return bytes;
}

/**
 * Normalises a pinned public key (as delivered in a scan bundle's
 * `issuer_keys.keys[kid]`, a map of key id to base64url-encoded public key —
 * see tickets.KeyRing.MarshalJSON on the backend) into raw bytes. Also
 * tolerates hex or standard base64 in case that encoding ever changes.
 */
export function publicKeyToBytes(encoded: unknown): Uint8Array {
    if (encoded instanceof Uint8Array) return encoded;
    if (typeof encoded !== 'string') {
        throw new CapabilityError(CapabilityErrorCode.MALFORMED, 'public key must be a string or byte array');
    }
    // hex is exactly 64 chars for a 32-byte Ed25519 key and only contains hex digits
    if (/^[0-9a-fA-F]{64}$/.test(encoded)) {
        return hexToBytes(encoded);
    }
    try {
        return base64UrlToBytes(encoded.replace(/=+$/, ''));
    } catch {
        // fall through to standard base64 (with padding, +/ alphabet)
    }
    const binary = atob(encoded);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return bytes;
}

/**
 * Verify a capability token against a pinned Ed25519 public key.
 *
 * @param {string} token
 * @param {Uint8Array} publicKey - 32-byte Ed25519 public key
 * @param {Date} [now] - defaults to `new Date()`; pass explicitly in tests
 * @returns {{v:number,tid:string,eid:string,tt:string,kid:string,sub:string,nm:string,iat:number,nbf?:number,exp?:number,seat?:string}}
 */
export function verifyCapability(token: unknown, publicKey: unknown, now = new Date()): CapabilityPayload {
    // Key size first, exactly like Go's Verify: a caller that pinned a broken
    // key should hear about it regardless of what was scanned.
    if (!(publicKey instanceof Uint8Array) || publicKey.length !== 32) {
        const length = (publicKey as { length?: unknown } | null | undefined)?.length;
        const shown = typeof length === 'number' || typeof length === 'string' ? length : typeof publicKey;
        throw new CapabilityError(CapabilityErrorCode.MALFORMED, `invalid public key length ${shown}`);
    }
    if (typeof token !== 'string') {
        throw new CapabilityError(CapabilityErrorCode.MALFORMED, 'token must be a string');
    }
    const parts = token.split('.');
    if (parts.length !== 3) {
        throw new CapabilityError(CapabilityErrorCode.MALFORMED, `expected 3 dot-separated segments, got ${parts.length}`);
    }
    // parts.length === 3 was just checked above (and threw otherwise), so
    // all three indices are populated — these assertions narrow past
    // noUncheckedIndexedAccess, not around a real gap.
    const [prefix, encPayload, encSig] = parts as [string, string, string];
    if (prefix !== TOKEN_PREFIX) {
        throw new CapabilityError(CapabilityErrorCode.MALFORMED, `bad prefix "${prefix}"`);
    }

    let body: Uint8Array;
    let sig: Uint8Array;
    try {
        body = base64UrlToBytes(encPayload);
        sig = base64UrlToBytes(encSig);
    } catch (err) {
        throw new CapabilityError(CapabilityErrorCode.MALFORMED, `bad base64: ${(err as Error).message}`);
    }
    if (sig.length !== 64) {
        throw new CapabilityError(CapabilityErrorCode.MALFORMED, `invalid signature length ${sig.length}`);
    }

    let ok = false;
    try {
        ok = ed25519.verify(sig, body, publicKey);
    } catch {
        ok = false;
    }
    if (!ok) {
        throw new CapabilityError(CapabilityErrorCode.BAD_SIGNATURE, 'signature verification failed');
    }

    let payload: unknown;
    try {
        payload = JSON.parse(bytesToUtf8(body));
    } catch (err) {
        throw new CapabilityError(CapabilityErrorCode.MALFORMED, `bad payload json: ${(err as Error).message}`);
    }
    // Shape before version, matching Go: a structurally broken payload is
    // malformed even if it also claims a version we do not support.
    validatePayloadShape(payload);

    if (payload.v !== CURRENT_VERSION) {
        throw new CapabilityError(CapabilityErrorCode.UNSUPPORTED_VERSION, `got version ${payload.v}, want ${CURRENT_VERSION}`);
    }

    const nowUnix = Math.floor(now.getTime() / 1000);
    if (payload.nbf && nowUnix < payload.nbf) {
        throw new CapabilityError(CapabilityErrorCode.NOT_YET_VALID, 'ticket not yet valid');
    }
    if (payload.exp && nowUnix >= payload.exp) {
        throw new CapabilityError(CapabilityErrorCode.EXPIRED, 'ticket expired');
    }

    return payload;
}

/** Read the `kid` field without verifying the signature — used only to pick
 * which pinned key to verify against, exactly like reading an unverified JWT
 * header. Never trust this for anything beyond a map lookup. */
export function peekKid(token: unknown): string | undefined {
    const parts = typeof token === 'string' ? token.split('.') : [];
    if (parts.length !== 3 || parts[0] !== TOKEN_PREFIX) {
        throw new CapabilityError(CapabilityErrorCode.MALFORMED, 'malformed token');
    }
    let partial: unknown;
    try {
        // parts.length === 3 was just checked above, so index 1 exists.
        partial = JSON.parse(bytesToUtf8(base64UrlToBytes(parts[1] as string)));
    } catch (err) {
        throw new CapabilityError(CapabilityErrorCode.MALFORMED, `bad payload json: ${(err as Error).message}`);
    }
    // Go's peekKID unmarshals into a struct, so a non-object payload or a
    // non-string kid is an error there rather than a missing key. Match it,
    // or a malformed token would surface as unknown_kid instead.
    if (partial === null || typeof partial !== 'object' || Array.isArray(partial)) {
        throw new CapabilityError(CapabilityErrorCode.MALFORMED, 'payload is not a JSON object');
    }
    const obj = partial as Record<string, unknown>;
    if (obj.kid !== undefined && obj.kid !== null && typeof obj.kid !== 'string') {
        throw new CapabilityError(CapabilityErrorCode.MALFORMED, 'payload field "kid" must be a string');
    }
    return obj.kid as string | undefined;
}

/**
 * Verify a token against a KeyRing (kid -> public key bytes), mirroring
 * Go's VerifyWithRing.
 */
export function verifyWithRing(token: unknown, keyRing: KeyRing, now = new Date()): CapabilityPayload {
    const kid = peekKid(token);
    const pub = kid !== undefined ? keyRing[kid] : undefined;
    if (!pub) {
        throw new CapabilityError(CapabilityErrorCode.UNKNOWN_KID, `unknown key id "${kid}"`);
    }
    return verifyCapability(token, pub, now);
}
