// lib/scan-decision.js
//
// The decision a gate makes about one presented ticket.
//
// This is lifted out of `use-scan-engine.ts` unchanged in behaviour, for one
// reason: it is the most consequential logic in the product and it was only
// reachable through a React hook, a camera and IndexedDB. Nothing that decides
// whether a person walks through a door should be that hard to test. Here it
// is an ordinary async function with its two effects injected, so every branch
// — including the ones that only happen when storage is broken — is covered by
// `scan-decision.test.js` under plain `node --test`.
//
// # What this mirrors
//
// Go's `scan.DecideWithBundle` (internal/scan/admission.go). The ORDER of the
// checks below is part of the contract, not an implementation detail, and it
// matches that function step for step.
//
// # What it does NOT do
//
// It does not prevent a cross-gate double-scan, and it cannot. Two gates
// partitioned from each other have no way to coordinate, so the same ticket
// presented at both IS admitted at both. What narrows the window is a fresher
// bundle (`admittedIndex` below); what finds what still slipped through is
// GET /api/events/{id}/admission-conflicts, after the fact. See
// docs/OFFLINE-GATES.md.
//
// # Fail closed
//
// Where this function cannot get an answer it refuses. A dedupe lookup that
// throws yields `invalid`, never `admitted` — refusing a legitimate guest is
// recoverable by a human at the door, and silently admitting a duplicate
// because storage was broken is not.

import type { CapabilityPayload, KeyRing } from './capability.ts';

/** The four verdicts, matching internal/scan's Status values. */
export const RESULT = Object.freeze({
    ADMITTED: 'admitted',
    DUPLICATE: 'duplicate',
    INVALID: 'invalid',
    WRONG_EVENT: 'wrong_event',
});

export type ResultValue = (typeof RESULT)[keyof typeof RESULT];

export interface Decision {
    result: ResultValue;
    note: string | null;
    ticketId: string | null;
    holderName: string | null;
}

/**
 * describeError turns a capability-verification failure into something a
 * person standing at a gate can act on. The codes come from lib/capability.js.
 */
export function describeError(err: unknown): string {
    const shaped = err as { code?: unknown; message?: unknown } | null | undefined;
    switch (shaped?.code) {
        case 'malformed':
            return 'Malformed ticket';
        case 'unsupported_version':
            return 'Unsupported ticket version';
        case 'bad_signature':
            return 'Invalid signature — tampered or wrong event';
        case 'not_yet_valid':
            return 'Ticket not valid yet';
        case 'expired':
            return 'Ticket expired';
        case 'unknown_kid':
            return 'Unknown signing key';
        default:
            return (typeof shaped?.message === 'string' && shaped.message) || 'Invalid ticket';
    }
}

export interface DecideAdmissionArgs {
    /** the raw `tdev.<payload>.<sig>` string */
    token: string;
    /** the event this gate is admitting for */
    eventId: string;
    /** kid -> public key */
    keyRing: KeyRing;
    /** authoritative valid-ticket ids */
    ticketIndexSet: Set<string>;
    /** whether that set is authoritative */
    ticketIndexPresent: boolean;
    /** ids already admitted elsewhere as of when the bundle was built */
    admittedIndexSet: Set<string>;
    verify: (token: string, ring: KeyRing, now: Date) => CapabilityPayload;
    wasAdmitted: (eventId: string, ticketId: string) => Promise<boolean>;
    now?: Date;
}

/**
 * decideAdmission verifies a presented capability token and decides what the
 * gate should do about it.
 *
 * Everything it needs is passed in; it touches no network, no camera and no
 * global. `verify` and `wasAdmitted` are injected so the caller supplies the
 * real Ed25519 verifier and the real IndexedDB lookup while a test supplies
 * fakes — including fakes that throw, which is how the fail-closed paths get
 * covered at all.
 *
 * A note on what is returned when a ticket is refused: an `invalid` verdict
 * carries `ticketId: null` even when a ticket id was parsed out of the token.
 * That is deliberate and matches the Go side — an id from a token that failed
 * verification is an unauthenticated string, and recording it would put
 * attacker-chosen data in the admission log.
 */
export async function decideAdmission({
    token,
    eventId,
    keyRing,
    ticketIndexSet,
    ticketIndexPresent,
    admittedIndexSet,
    verify,
    wasAdmitted,
    now = new Date(),
}: DecideAdmissionArgs): Promise<Decision> {
    let payload: CapabilityPayload;
    try {
        payload = verify(token, keyRing, now);
    } catch (err) {
        // The signature is the whole basis of admission. If it does not check
        // out there is nothing else worth asking.
        return { result: RESULT.INVALID, note: describeError(err), ticketId: null, holderName: null };
    }

    if (payload.eid !== eventId) {
        // Genuinely signed, but for a different event — a distinct verdict
        // from `invalid` because it means the guest is at the wrong door, not
        // holding a bad ticket. The id is safe to record: it verified.
        return {
            result: RESULT.WRONG_EVENT,
            note: 'Ticket belongs to a different event',
            ticketId: payload.tid,
            holderName: payload.nm ?? null,
        };
    }

    if (ticketIndexPresent && !ticketIndexSet.has(payload.tid)) {
        // Signature verifies, right event — but absent from the authoritative
        // index this gate downloaded, e.g. refunded after issuance.
        //
        // `ticketIndexPresent` is the crux and is checked INSTEAD OF the set's
        // size: a server-built bundle always sets the flag, so an empty
        // authoritative index means "admit nobody" (every ticket revoked, or
        // none issued). Inferring authority from length would silently
        // re-admit every physically-held ticket for a cancelled event.
        return {
            result: RESULT.INVALID,
            note: 'Ticket revoked or not issued for this event',
            ticketId: null,
            holderName: null,
        };
    }

    if (admittedIndexSet.has(payload.tid)) {
        // The server already had an admission for this ticket when the bundle
        // was built — i.e. another gate let it through. This is the ONLY
        // channel by which a disconnected gate ever learns that, and it is why
        // re-pulling a bundle between waves narrows the double-entry window.
        return {
            result: RESULT.DUPLICATE,
            note: 'Ticket already admitted at another gate',
            ticketId: payload.tid,
            holderName: payload.nm ?? null,
        };
    }

    try {
        const already = await wasAdmitted(eventId, payload.tid);
        return {
            result: already ? RESULT.DUPLICATE : RESULT.ADMITTED,
            note: already ? 'Already scanned at this gate' : null,
            ticketId: payload.tid,
            holderName: payload.nm ?? null,
        };
    } catch (err) {
        // The local dedupe store itself failed — evicted, over quota, or a
        // browser in a private mode that pretends IndexedDB exists. Refuse.
        // Guessing in the admitting direction here is how one broken phone
        // turns into an unbounded number of duplicate entries.
        const reason = err instanceof Error ? err.message : String(err);
        return {
            result: RESULT.INVALID,
            note: `Local dedupe check failed: ${reason}`,
            ticketId: null,
            holderName: null,
        };
    }
}

export default decideAdmission;
