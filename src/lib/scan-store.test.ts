// The order a gate uploads its offline scan queue in.
//
// This is the queue that actually runs. Every phone at every door records
// scans into this IndexedDB store while the venue has no network, and
// `getPendingSync` produces the array that becomes POST /api/scan/sync's
// `admissions` body. The server (internal/httpapi/scan_handlers.go,
// dbSyncSink.Apply) walks that array IN ORDER and the FIRST 'admitted' claim
// for a ticket is the one that keeps 'admitted'; every later claim for the
// same ticket is rewritten to 'duplicate' with the device's own verdict
// preserved in reported_result. So the order this file pins down is the order
// in which a partitioned gate's claims compete for a contested ticket.
//
// Nothing here is stubbed that matters. `fake-indexeddb` is a real
// implementation of the IndexedDB specification, so `getAllFromIndex` sorts
// exactly the way Chrome and Safari sort: by index key, and then by PRIMARY
// key. That second clause is the whole defect — the primary key is a random
// UUID v4 — and modelling it by hand would have meant testing my own model of
// the bug rather than the bug.
//
// Determinism, since the defect is probabilistic:
//   * `withScriptedIDs` replaces crypto.randomUUID with a fixed script whose
//     ids DESCEND lexicographically as the scans ASCEND chronologically, so
//     primary-key order is the exact reverse of the right answer. There is no
//     ordering of a random draw involved: it fails, or the ordering is real.
//   * `TestUploadOrder_ManyRecordsRealUUIDs` does the same over 60 genuinely
//     random ids, where passing by luck is 1/60! — a backstop in case the
//     scripted ids ever stopped being representative.

import 'fake-indexeddb/auto';
import test from 'node:test';
import assert from 'node:assert/strict';

import { recordScan, getPendingSync, markSynced, orderForUpload } from './scan-store.ts';

// ── Scripted ids ────────────────────────────────────────────────────────────

/**
 * Run `fn` with crypto.randomUUID handing out ids in DESCENDING lexicographic
 * order — 'f...', 'e...', 'd...' — so that the n-th scan recorded gets an id
 * that sorts BEFORE none of its predecessors and AFTER all of them is
 * impossible. Any implementation that leans on primary-key order (which is
 * what IndexedDB gives you for free) returns these exactly backwards.
 *
 * The ids are still well-formed v4 UUIDs: same length, same version and
 * variant nibbles, so nothing downstream can tell them from real ones.
 */
let scriptBatch = 0;
async function withScriptedIDs<T>(count: number, fn: (ids: string[]) => Promise<T>): Promise<T> {
    const alphabet = 'fedcba9876543210';
    assert.ok(count <= alphabet.length * alphabet.length, 'scripted id space exhausted');
    // Every test in this file shares one database, so the ids have to be
    // unique ACROSS calls too or the second call collides on the primary key.
    // The batch tag lives in the LAST field, which no comparison in this file
    // reaches: the descending first field still decides the order within a
    // batch, which is the whole point of scripting them.
    const tag = String(scriptBatch++).padStart(12, '0');
    const ids: string[] = [];
    for (let i = 0; i < count; i++) {
        const hi = alphabet[Math.floor(i / alphabet.length)];
        const lo = alphabet[i % alphabet.length];
        ids.push(`${hi}${lo}000000-0000-4000-8000-${tag}`);
    }
    let next = 0;
    const original = Object.getOwnPropertyDescriptor(globalThis, 'crypto');
    Object.defineProperty(globalThis, 'crypto', {
        configurable: true,
        value: {
            randomUUID: () => {
                assert.ok(next < ids.length, 'more ids requested than were scripted');
                return ids[next++];
            },
        },
    });
    try {
        return await fn(ids);
    } finally {
        if (original) Object.defineProperty(globalThis, 'crypto', original);
        else delete (globalThis as { crypto?: unknown }).crypto;
    }
}

let eventCounter = 0;
function freshEventID(name: string) {
    eventCounter += 1;
    return `evt_${name}_${eventCounter}`;
}

/** Record `count` scans, one per ticket, in the given chronological order. */
async function recordSeries(
    eventID: string,
    { count, at, gateId = 'North', deviceId = 'device-A' }: { count: number; at: (i: number) => string; gateId?: string; deviceId?: string },
) {
    const recorded = [];
    for (let i = 0; i < count; i++) {
        // Sequential on purpose: the order these are awaited in IS the order
        // under test, so they must not be started concurrently.
        recorded.push(
            await recordScan({
                eventId: eventID,
                ticketId: `tkt_${String(i).padStart(3, '0')}`,
                deviceId,
                gateId,
                result: 'admitted',
                scannedAt: at(i),
            }),
        );
    }
    return recorded;
}

const isoAt = (ms: number) => new Date(ms).toISOString();

// ── The defect ──────────────────────────────────────────────────────────────

// A gate scans eight tickets in a known order, one second apart. The batch it
// uploads must be that order. Against the unfixed store it is the reverse of
// it, because the scripted ids descend and IndexedDB hands index results back
// in primary-key order.
test('the upload batch is in the order the scans happened', async () => {
    const eventID = freshEventID('order');
    await withScriptedIDs(8, async () => {
        await recordSeries(eventID, { count: 8, at: (i) => isoAt(Date.UTC(2026, 6, 31, 19, 0, i)) });
    });

    const pending = await getPendingSync(eventID);
    assert.equal(pending.length, 8, 'all eight scans are queued');
    assert.deepEqual(
        pending.map((p) => p.ticket_id),
        Array.from({ length: 8 }, (_, i) => `tkt_${String(i).padStart(3, '0')}`),
        'the batch must be ordered by when the scan happened, not by its random primary key',
    );
});

// The luck-proof restatement of the same property, over ids drawn from the
// real generator. Sixty records: one chance in 60! that a random order is the
// right one.
test('the upload batch order holds for 60 records with real random ids', async () => {
    const eventID = freshEventID('manyreal');
    const count = 60;
    await recordSeries(eventID, { count, at: (i) => isoAt(Date.UTC(2026, 6, 31, 20, 0, 0) + i * 1000) });

    const pending = await getPendingSync(eventID);
    assert.equal(pending.length, count, 'all sixty scans are queued');
    const ids = pending.map((p) => p.id);
    assert.equal(new Set(ids).size, count, 'ids are distinct, so this is a real permutation test');
    assert.deepEqual(
        pending.map((p) => p.ticket_id),
        Array.from({ length: count }, (_, i) => `tkt_${String(i).padStart(3, '0')}`),
        'sixty records cannot come back in the right order by chance',
    );
});

// Every scan carries the SAME scanned_at — a plausible thing on a device whose
// clock has one-second resolution, and the case a timestamp order has no
// answer for. The batch must still be the order the scans happened in.
//
// This test also refuses the wrong fix: ordering on `scanned_at` alone leaves
// these eight tied, and a stable sort over IndexedDB's primary-key order then
// returns them in id order — which the scripted ids make the exact reverse of
// the truth.
test('scans sharing one timestamp keep the order they were recorded in', async () => {
    const eventID = freshEventID('tie');
    const sameInstant = isoAt(Date.UTC(2026, 6, 31, 21, 0, 0));
    await withScriptedIDs(8, async () => {
        await recordSeries(eventID, { count: 8, at: () => sameInstant });
    });

    const pending = await getPendingSync(eventID);
    assert.equal(pending.length, 8, 'all eight tied scans are queued');
    assert.deepEqual(
        pending.map((p) => p.ticket_id),
        Array.from({ length: 8 }, (_, i) => `tkt_${String(i).padStart(3, '0')}`),
        'equal timestamps must not be free to reorder the batch',
    );
});

// A gate device's clock is not monotonic. An NTP correction, or an operator
// setting the time by hand mid-shift, stamps a LATER scan with an EARLIER
// scanned_at. The batch order must be the order the scans were recorded — what
// actually happened at the door — and must not walk backwards with the clock.
//
// This is the test that decides the ordering field. It is red for `seq`
// missing, and it is red for any implementation that orders on scanned_at.
test('a clock that jumps backwards does not reorder the batch', async () => {
    const eventID = freshEventID('skew');
    // Recorded in this order; the wall clock lurches about underneath.
    const stamps = [
        Date.UTC(2026, 6, 31, 22, 0, 0),
        Date.UTC(2026, 6, 31, 21, 30, 0), // clock corrected backwards
        Date.UTC(2026, 6, 31, 23, 0, 0),
        Date.UTC(2026, 6, 31, 20, 0, 0), // and again, further back
        Date.UTC(2026, 6, 31, 22, 15, 0),
    ];
    await withScriptedIDs(stamps.length, async () => {
        await recordSeries(eventID, {
            count: stamps.length,
            at: (i) => {
                const ms = stamps[i];
                // `at` is only ever called for i in [0, count), and count is
                // stamps.length, so this index is always populated.
                if (ms === undefined) throw new Error(`no stamp at index ${i}`);
                return isoAt(ms);
            },
        });
    });

    const pending = await getPendingSync(eventID);
    assert.deepEqual(
        pending.map((p) => p.ticket_id),
        ['tkt_000', 'tkt_001', 'tkt_002', 'tkt_003', 'tkt_004'],
        'the order is the order the scans were taken, not the order the clock claims',
    );
});

// A device with a deliberately backdated clock must not be able to move its
// own claims to the front of its own batch. Scan the contested ticket LAST but
// stamp it a day earlier than everything else: it must still be uploaded last,
// behind the scans that genuinely came first.
test('a backdated scan does not jump the queue', async () => {
    const eventID = freshEventID('backdate');
    await withScriptedIDs(4, async () => {
        await recordScan({ eventId: eventID, ticketId: 'tkt_a', deviceId: 'd', gateId: 'g', result: 'admitted', scannedAt: isoAt(Date.UTC(2026, 6, 31, 18, 0, 0)) });
        await recordScan({ eventId: eventID, ticketId: 'tkt_b', deviceId: 'd', gateId: 'g', result: 'admitted', scannedAt: isoAt(Date.UTC(2026, 6, 31, 18, 0, 1)) });
        await recordScan({ eventId: eventID, ticketId: 'tkt_c', deviceId: 'd', gateId: 'g', result: 'admitted', scannedAt: isoAt(Date.UTC(2026, 6, 31, 18, 0, 2)) });
        // The lie: recorded fourth, stamped a day before the first.
        await recordScan({ eventId: eventID, ticketId: 'tkt_contested', deviceId: 'd', gateId: 'g', result: 'admitted', scannedAt: isoAt(Date.UTC(2026, 6, 30, 18, 0, 0)) });
    });

    const pending = await getPendingSync(eventID);
    assert.deepEqual(
        pending.map((p) => p.ticket_id),
        ['tkt_a', 'tkt_b', 'tkt_c', 'tkt_contested'],
        'a backdated scanned_at must not buy a place at the front of the batch',
    );
});

// Syncing part of a queue must not disturb the order of what is left. A flaky
// connection that uploads the first few and then drops has to resume with a
// prefix of the same sequence, not a reshuffle of it.
test('marking part of the queue synced leaves the rest in order', async () => {
    const eventID = freshEventID('partial');
    await withScriptedIDs(10, async () => {
        await recordSeries(eventID, { count: 10, at: (i) => isoAt(Date.UTC(2026, 6, 31, 17, 0, i)) });
    });

    const first = await getPendingSync(eventID);
    assert.equal(first.length, 10, 'ten queued');
    await markSynced(first.slice(0, 4).map((p) => p.id));

    const rest = await getPendingSync(eventID);
    assert.deepEqual(
        rest.map((p) => p.ticket_id),
        ['tkt_004', 'tkt_005', 'tkt_006', 'tkt_007', 'tkt_008', 'tkt_009'],
        'the remaining queue is the tail of the same sequence',
    );
});

// ── orderForUpload as a total order ─────────────────────────────────────────
//
// The tests above all feed the sort an array IndexedDB already handed back in
// primary-key order, which hides whether the ordering is TOTAL — a comparator
// missing its final tiebreaker still looks right there, because Array.sort is
// stable and the input order happens to be the tiebreaker's answer. These
// exercise the comparator directly, over every permutation, which is the only
// way the tiebreaker is observable.

/** Every permutation of `xs` (small n only). */
function permutations<T>(xs: T[]): T[][] {
    if (xs.length <= 1) return [xs];
    const out: T[][] = [];
    for (let i = 0; i < xs.length; i++) {
        // i < xs.length by the loop condition above, so this index is always populated.
        const item = xs[i] as T;
        const rest = [...xs.slice(0, i), ...xs.slice(i + 1)];
        for (const p of permutations(rest)) out.push([item, ...p]);
    }
    return out;
}

test('orderForUpload is a total order: every permutation sorts identically', () => {
    // Deliberately degenerate: two rows share a seq, two more share a
    // scanned_at with no seq at all. Only a comparator with a final tiebreaker
    // on the primary key can answer the same way for every input order.
    const rows = [
        { id: 'ccc', seq: 2, scanned_at: '2026-07-31T10:00:02.000Z' },
        { id: 'aaa', seq: 2, scanned_at: '2026-07-31T10:00:09.000Z' },
        { id: 'bbb', seq: 5, scanned_at: '2026-07-31T10:00:01.000Z' },
        { id: 'zzz', scanned_at: '2026-07-31T09:00:00.000Z' },
        { id: 'kkk', scanned_at: '2026-07-31T09:00:00.000Z' },
    ];
    const perms = permutations(rows);
    assert.equal(perms.length, 120, 'all 5! = 120 input orders are exercised');

    const expected = orderForUpload(rows).map((r) => r.id);
    assert.deepEqual(expected, ['kkk', 'zzz', 'aaa', 'ccc', 'bbb'],
        'records with no seq come first (they predate the migration), then seq, then id');

    for (const perm of perms) {
        assert.deepEqual(orderForUpload(perm).map((r) => r.id), expected,
            `permutation ${perm.map((r) => r.id).join(',')} must sort to the same total order`);
    }
});

test('orderForUpload does not mutate its input', () => {
    const rows = [{ id: 'b', seq: 2 }, { id: 'a', seq: 1 }];
    const before = rows.map((r) => r.id);
    orderForUpload(rows);
    assert.deepEqual(rows.map((r) => r.id), before, 'the caller\'s array is left alone');
});

// The runtime fallback, tested where it is reachable: a record with no `seq`
// is ordered by its wall clock and then its id, and sorts ahead of every
// record that has one. Nothing is dropped and nothing is left unordered.
//
// This is defence behind the migration, not instead of it — see
// scan-store.upgrade.test.js, which asserts the migration actually backfills.
test('records with no seq are ordered deterministically and come first', () => {
    const rows = [
        { id: 'n2', scanned_at: '2026-07-31T08:00:05.000Z' },
        { id: 'has-seq', seq: 1, scanned_at: '2026-07-31T07:00:00.000Z' },
        { id: 'n1', scanned_at: '2026-07-31T08:00:01.000Z' },
        { id: 'n3', scanned_at: '2026-07-31T08:00:05.000Z' },
    ];
    assert.deepEqual(
        orderForUpload(rows).map((r) => r.id),
        ['n1', 'n2', 'n3', 'has-seq'],
        'legacy records sort by (scanned_at, id) and ahead of anything sequenced after the upgrade',
    );
});

// An unparseable or missing scanned_at must not throw and must not scatter the
// record randomly through the batch. It sorts last among the unsequenced,
// deterministically, and is still uploaded.
test('a record with an unusable timestamp is still ordered and still uploaded', () => {
    const rows = [
        { id: 'b', scanned_at: 'not-a-date' },
        { id: 'a', scanned_at: '2026-07-31T08:00:00.000Z' },
        { id: 'c' },
    ];
    const out = orderForUpload(rows);
    assert.equal(out.length, 3, 'nothing is dropped');
    assert.deepEqual(out.map((r) => r.id), ['a', 'b', 'c'],
        'usable timestamps first, then the unusable ones by id');
});
