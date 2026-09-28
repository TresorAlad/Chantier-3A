// What happens to scans already queued on a device in the field.
//
// The upload order fix adds a `seq` column and a `by_seq` index, which means a
// database version bump — and there are phones out there right now holding
// unsynced admissions written under version 1, with no seq on them. Losing
// those is losing a record of people who were let through a door. Reordering
// them into nonsense is quieter and nearly as bad: the server decides a
// contested ticket by the order the batch arrives in.
//
// So this file opens a genuine version-1 database, populates it the way a
// gate would have, and then hands it to the real store — which upgrades it —
// and checks what came out the other side.
//
// It lives apart from scan-store.test.js because `node --test` runs each file
// in its own process, and the seeding has to happen before scan-store.js opens
// its (module-scoped, cached) connection. Sharing a process would mean racing
// that cache.
//
// The single edit that turns the assertions below red is removing the
// `oldVersion < 2` backfill from scan-store.js's upgrade callback.

import 'fake-indexeddb/auto';
import test from 'node:test';
import assert from 'node:assert/strict';
import { openDB } from 'idb';

import type { AdmissionRecord, ScanDB } from './scan-store.ts';

const DB_NAME = 'tdev-scanner';
const EVENT_ID = 'evt_field_device';

// The version-1 schema, copied verbatim from what shipped: keyPath 'id', four
// indexes, no `seq` and no `by_seq`. Written out rather than imported so this
// test keeps describing the OLD shape even after the current one moves on.
async function seedVersion1(rows: AdmissionRecord[]) {
    const db = await openDB(DB_NAME, 1, {
        upgrade(db) {
            db.createObjectStore('bundles', { keyPath: 'event_id' });
            const store = db.createObjectStore('admissions', { keyPath: 'id' });
            store.createIndex('by_event', 'event_id');
            store.createIndex('by_ticket', 'ticket_id');
            store.createIndex('by_event_ticket', ['event_id', 'ticket_id']);
            store.createIndex('by_synced', 'synced');
        },
    });
    const tx = db.transaction('admissions', 'readwrite');
    for (const row of rows) await tx.store.add(row);
    await tx.done;
    db.close();
}

function legacyRow({
    id,
    ticket,
    at,
    result = 'admitted',
    note = null,
    synced = 0,
}: {
    id: string;
    ticket: string;
    at: string;
    result?: string;
    note?: string | null;
    synced?: 0 | 1;
}): AdmissionRecord {
    return {
        id,
        event_id: EVENT_ID,
        ticket_id: ticket,
        device_id: 'device-in-the-field',
        gate_id: 'North',
        scanned_at: at,
        result,
        note,
        holder_name: 'Nomvula Dlamini',
        synced,
    };
}

// Chronological order is tkt_first → tkt_second → tkt_third → tkt_future.
// The ids are chosen so that PRIMARY KEY order is a different permutation
// entirely (a,b,c,d ascending would be third, first, future, second), which is
// what the unfixed store uploaded and what a migration that ignored
// scanned_at would preserve.
const LEGACY = [
    legacyRow({ id: 'b0000000-0000-4000-8000-000000000000', ticket: 'tkt_first', at: '2026-07-31T18:00:00.000Z' }),
    legacyRow({ id: 'd0000000-0000-4000-8000-000000000000', ticket: 'tkt_second', at: '2026-07-31T18:05:00.000Z', result: 'duplicate', note: 'already scanned here' }),
    legacyRow({ id: 'a0000000-0000-4000-8000-000000000000', ticket: 'tkt_third', at: '2026-07-31T18:10:00.000Z' }),
    // This device's clock is wrong. The scan is real and was taken during the
    // event; the stamp says 2030. It is still the LAST of the legacy scans,
    // and after the upgrade it must still sort before anything scanned later.
    legacyRow({ id: 'c0000000-0000-4000-8000-000000000000', ticket: 'tkt_future', at: '2030-01-01T00:00:00.000Z' }),
    // Already uploaded before the upgrade: must survive, must stay synced, and
    // must not reappear in the pending batch.
    legacyRow({ id: 'e0000000-0000-4000-8000-000000000000', ticket: 'tkt_gone', at: '2026-07-31T17:00:00.000Z', synced: 1 }),
];

await seedVersion1(LEGACY);

// Imported only now, so that the first thing it does is upgrade the database
// that was just seeded.
const { recordScan, getPendingSync, getAdmissionsForEvent, orderForUpload } = await import('./scan-store.ts');

/** Read the store back through a plain connection, not through the module. */
async function rawRows(): Promise<AdmissionRecord[]> {
    // Typed against the CURRENT schema (unlike seedVersion1 above, which
    // deliberately stays untyped/hand-written to keep describing the OLD
    // shape) — this reads the store back AFTER the real module's upgrade
    // has run, so it should conform to what scan-store.ts itself expects.
    const db = await openDB<ScanDB>(DB_NAME);
    const rows = await db.getAll('admissions');
    db.close();
    return rows;
}

test('the upgrade loses nothing that was queued', async () => {
    const rows = await getAdmissionsForEvent(EVENT_ID);
    assert.equal(rows.length, 5, 'all five version-1 records survive the upgrade');

    const byID = new Map(rows.map((r) => [r.id, r]));
    for (const original of LEGACY) {
        const found = byID.get(original.id);
        assert.ok(found, `record ${original.ticket_id} must still be there`);
        for (const field of ['event_id', 'ticket_id', 'device_id', 'gate_id', 'scanned_at', 'result', 'note', 'holder_name', 'synced']) {
            assert.deepEqual(
                (found as unknown as Record<string, unknown>)[field],
                (original as unknown as Record<string, unknown>)[field],
                `${original.ticket_id}.${field} must be untouched by the migration`,
            );
        }
    }
});

test('the upgrade backfills a sequence onto every record already queued', async () => {
    const rows = await rawRows();
    assert.equal(rows.length, 5, 'five records to check');
    for (const row of rows) {
        assert.equal(typeof row.seq, 'number',
            `${row.ticket_id} has no seq: the migration did not run, and every future ` +
            'upload from this device falls back to reconstructing the order from a wall clock');
    }
    const seqs = rows.map((r) => r.seq!).sort((a, b) => a - b);
    assert.deepEqual(seqs, [1, 2, 3, 4, 5], 'the backfill numbers them 1..N, distinct');

    // ...and in the order the evidence on the row supports: chronological by
    // scanned_at. That is all a version-1 row ever recorded — the true enqueue
    // order was never written down — so this is a reconstruction, and the best
    // one available. It is deterministic, which random primary keys were not.
    const seqOf = (ticket: string) => rows.find((r) => r.ticket_id === ticket)!.seq!;
    assert.ok(seqOf('tkt_gone') < seqOf('tkt_first'), 'earliest scan gets the lowest seq');
    assert.ok(seqOf('tkt_first') < seqOf('tkt_second'));
    assert.ok(seqOf('tkt_second') < seqOf('tkt_third'));
    assert.ok(seqOf('tkt_third') < seqOf('tkt_future'));
});

test('the queued batch uploads in chronological order, not primary-key order', async () => {
    const pending = await getPendingSync(EVENT_ID);
    assert.deepEqual(
        pending.map((p) => p.ticket_id),
        ['tkt_first', 'tkt_second', 'tkt_third', 'tkt_future'],
        'the migrated queue is uploaded oldest-first; tkt_gone was already synced',
    );
});

test('scans taken after the upgrade queue behind the ones that were already there', async () => {
    const after = await recordScan({
        eventId: EVENT_ID,
        ticketId: 'tkt_after_upgrade',
        deviceId: 'device-in-the-field',
        gateId: 'North',
        result: 'admitted',
        // Stamped BEFORE every legacy scan, because the clock is still wrong.
        // It happened last, so it uploads last.
        scannedAt: '2020-01-01T00:00:00.000Z',
    });
    assert.equal(typeof after.seq, 'number', 'a new scan is sequenced at enqueue time');
    const legacyMax = Math.max(...(await rawRows()).filter((r) => r.ticket_id !== 'tkt_after_upgrade').map((r) => r.seq!));
    assert.ok(after.seq! > legacyMax,
        `a new scan continues past the backfill (got ${after.seq}, backfill topped out at ${legacyMax})`);

    const pending = await getPendingSync(EVENT_ID);
    assert.deepEqual(
        pending.map((p) => p.ticket_id),
        ['tkt_first', 'tkt_second', 'tkt_third', 'tkt_future', 'tkt_after_upgrade'],
        'the record queued after the upgrade goes to the back regardless of what its clock said',
    );
});

test('the upgrade is idempotent: reopening does not renumber anything', async () => {
    const before = new Map((await rawRows()).map((r) => [r.id, r.seq]));
    // Stated so this cannot pass vacuously by comparing undefined to undefined:
    // there have to be real sequence numbers here for the comparison to mean
    // anything.
    assert.ok(before.size >= 5, 'there are records to renumber in the first place');
    for (const [id, seq] of before) assert.equal(typeof seq, 'number', `${id} must already be sequenced`);

    const db = await openDB(DB_NAME); // opens at the current version, no upgrade
    db.close();
    const after = new Map((await rawRows()).map((r) => [r.id, r.seq]));
    assert.deepEqual([...after.entries()].sort(), [...before.entries()].sort(),
        'a second open must not move a queued scan to a different place in the batch');
});

test('orderForUpload agrees with what came out of the database', async () => {
    // The store's answer and the pure comparator's answer are the same answer;
    // if they ever diverge, the ordering has moved into the query and stopped
    // being testable at the comparator.
    const pending = await getPendingSync(EVENT_ID);
    const shuffled = [...pending].reverse();
    assert.deepEqual(orderForUpload(shuffled).map((r) => r.ticket_id), pending.map((r) => r.ticket_id),
        'the batch order is orderForUpload, whatever order the rows arrive in');
});
