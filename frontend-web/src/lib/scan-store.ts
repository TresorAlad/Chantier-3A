// lib/scan-store.js
//
// IndexedDB-backed local state for the offline gate scanner. Everything here
// must work with zero network access: the scan bundle is cached once while
// online (see `saveBundle`), and every scan after that is verified and
// recorded purely against this local database. Sync back to the server is a
// best-effort background step, never a precondition for admission.

import { openDB, type DBSchema, type IDBPDatabase, type IDBPTransaction } from 'idb';
// Extension included deliberately: Vite resolves './utils' either way, but
// node:test (which is what `npm test` runs) resolves ESM specifiers by the
// spec and does not, so without it this module cannot be tested at all.
import { uuid } from './utils.ts';

/** A cached scan bundle — see internal/scan/bundle.go; passed through opaquely. */
export interface BundleRecord {
    event_id: string;
    cached_at: string;
    [key: string]: unknown;
}

/** One recorded scan attempt. Append-only — see `recordScan`. */
export interface AdmissionRecord {
    id: string;
    event_id: string;
    ticket_id: string | null;
    device_id: string;
    gate_id: string;
    scanned_at: string;
    /** 'admitted' | 'duplicate' | 'invalid' | 'wrong_event' */
    result: string;
    note: string | null;
    holder_name: string | null;
    synced: 0 | 1;
    /** Absent on rows written before the v2 upgrade backfilled it. */
    seq?: number;
}

export interface ScanDB extends DBSchema {
    bundles: {
        key: string;
        value: BundleRecord;
    };
    admissions: {
        key: string;
        value: AdmissionRecord;
        indexes: {
            by_event: string;
            by_ticket: string;
            by_event_ticket: [string, string];
            by_synced: number;
            by_seq: number;
        };
    };
}

const DB_NAME = 'tdev-scanner';
// v1 → v2 adds `seq` to every admission row and the `by_seq` index over it.
// See `upgrade` below for exactly what happens to rows already queued on a
// device in the field, and `orderForUpload` for why the column exists.
const DB_VERSION = 2;
const STORE_BUNDLES = 'bundles';
const STORE_ADMISSIONS = 'admissions';
const IDX_SEQ = 'by_seq';

let dbPromise: Promise<IDBPDatabase<ScanDB>> | undefined;

function getDB(): Promise<IDBPDatabase<ScanDB>> {
    if (!dbPromise) {
        dbPromise = openDB(DB_NAME, DB_VERSION, {
            // idb's own .d.ts types `upgrade` as `(...) => void`, so
            // no-misused-promises flags this as a Promise-returning function
            // handed to a void-expecting property — but idb's actual
            // behaviour (not just its types) supports an async upgrade:
            // every await below is on an IDB request promise from the SAME
            // versionchange transaction (`tx`/`store`), which is exactly
            // what keeps that transaction alive across the awaits, not a
            // network call or timer that would let it auto-commit early.
            // The v1→v2 migration this enables is exercised end to end by
            // scan-store.upgrade.test.ts.
            // eslint-disable-next-line @typescript-eslint/no-misused-promises
            async upgrade(db, oldVersion, newVersion, tx) {
                if (!db.objectStoreNames.contains(STORE_BUNDLES)) {
                    db.createObjectStore(STORE_BUNDLES, { keyPath: 'event_id' });
                }
                if (!db.objectStoreNames.contains(STORE_ADMISSIONS)) {
                    const store = db.createObjectStore(STORE_ADMISSIONS, { keyPath: 'id' });
                    store.createIndex('by_event', 'event_id');
                    store.createIndex('by_ticket', 'ticket_id');
                    store.createIndex('by_event_ticket', ['event_id', 'ticket_id']);
                    store.createIndex('by_synced', 'synced');
                    store.createIndex(IDX_SEQ, 'seq');
                    return; // brand new database: there is nothing to migrate
                }

                // --- v1 → v2 -------------------------------------------------
                //
                // A device that has been scanning at a door already has rows in
                // here with no `seq`. NOTHING IS DELETED AND NOTHING IS
                // REWRITTEN except to add the field: every queued scan is still
                // queued, still unsynced, and still carries the same id,
                // result, note and scanned_at it was recorded with.
                //
                // The only question the migration has to answer is what order
                // those legacy rows go in, and the honest answer is that the
                // information to reconstruct the true one was never written
                // down. `seq` did not exist when they were enqueued; the only
                // ordering fact on the row is `scanned_at`, the device's wall
                // clock. So they are backfilled in (scanned_at, id) order —
                // chronological by the best evidence available, with the
                // primary key as a total tiebreaker so the result is the same
                // whichever order IndexedDB hands them back in.
                //
                // That is strictly better than what they had, which was random,
                // and it is bounded: it is a one-off reconstruction of scans
                // taken BEFORE the upgrade, and every scan taken after it is
                // sequenced properly at enqueue time. Backfilled rows occupy
                // seq 1..N, so they all sort ahead of everything recorded after
                // the upgrade — which is correct, because they all happened
                // first, whatever their clock said at the time.
                const store = tx.objectStore(STORE_ADMISSIONS);
                if (!store.indexNames.contains(IDX_SEQ)) {
                    store.createIndex(IDX_SEQ, 'seq');
                }
                if (oldVersion < 2) {
                    const rows = await store.getAll();
                    rows.sort(compareLegacy);
                    for (const [i, row] of rows.entries()) {
                        // 1..N, assigned unconditionally: at v1 no row can
                        // already carry a seq, so these are distinct by
                        // construction and no row can collide with another.
                        row.seq = i + 1;
                        await store.put(row);
                    }
                }
            },
        });
    }
    return dbPromise;
}

// --- Batch order ------------------------------------------------------------
//
// WHY THIS EXISTS. The server applies an uploaded batch IN ARRAY ORDER
// (internal/httpapi/scan_handlers.go, dbSyncSink.Apply): the first 'admitted'
// claim it sees for a ticket keeps 'admitted', and every later claim for that
// same ticket is rewritten to 'duplicate' with the device's own verdict kept in
// reported_result. Batch order is therefore the winner rule for a contested
// ticket, and it must not be an accident.
//
// It was an accident. Admissions are keyed on a random UUID v4 and read back
// through `getAllFromIndex('by_event', ...)`, and IndexedDB returns index
// results ordered by index key and then by PRIMARY key — so the batch a gate
// uploaded was ordered by a random number. Two scans a minute apart could
// arrive in either order, every upload rolling the dice again.
//
// WHICH FIELD. `seq` — a local counter assigned when the scan is written,
// taken from the highest seq already in the store rather than from any clock.
// The alternative was `scanned_at`, and it is rejected for three reasons that
// bite in the order given:
//
//  1. A gate device's clock is not monotonic. An NTP correction, or an
//     operator fixing the time mid-shift, stamps a LATER scan with an EARLIER
//     scanned_at, and any order that trusts the column walks backwards with it.
//  2. Timestamps tie. Two scans inside one clock tick have no order at all
//     under a timestamp comparison, and a stable sort then silently falls back
//     to whatever IndexedDB happened to hand over — the random order again.
//  3. THE THREAT MODEL. scanned_at is the wall clock of the device at the
//     door, and the device controls it. Ordering the batch on it hands a phone
//     with a skewed — or deliberately backdated — clock a lever over which
//     gate wins a contested ticket: set the clock back, and your claims sort
//     to the front of your own upload. `seq` is assigned by this store at
//     enqueue time, cannot be moved by changing the clock, and can only
//     increase. scanned_at stays on the row, unchanged, as a diagnostic and as
//     the sync idempotency key — it is simply not an order.
//
// This mirrors internal/scan's SQLiteQueue.Pending, which orders by rowid for
// the same three reasons, so the reference queue and the queue that actually
// runs on the hardware answer the same way.
//
// WHAT THIS IS NOT. Making the batch order deterministic decides which of ONE
// device's claims competes first. It changes nothing about two gates that were
// offline from each other: a cross-gate double-scan is still DETECTED, never
// PREVENTED, because two doors that cannot see each other cannot agree at the
// moment of the scan. See docs/OFFLINE-GATES.md.

/**
 * The minimal shape every ordering helper below needs. `orderForUpload` is
 * exercised directly (scan-store.test.js) over bare fixtures that carry only
 * these fields, as well as over full `AdmissionRecord`s in production — so
 * the helpers are generic over anything with at least this shape, rather
 * than tied to the full record type.
 */
export interface SortableRow {
    id: string;
    seq?: number;
    scanned_at?: string;
}

/** Milliseconds for a stored scanned_at, or null if it cannot be read as one. */
function scannedAtMillis(row: SortableRow): number | null {
    const t = Date.parse(row?.scanned_at ?? '');
    return Number.isNaN(t) ? null : t;
}

function compareIDs(a: SortableRow, b: SortableRow): number {
    const x = String(a?.id ?? '');
    const y = String(b?.id ?? '');
    return x < y ? -1 : x > y ? 1 : 0;
}

/**
 * Order for rows that have no `seq`: written before the v2 upgrade, so the
 * only ordering evidence on them is the wall clock. Chronological, with the
 * primary key as a total tiebreaker; a row whose scanned_at cannot be parsed
 * sorts after every row whose can, rather than anywhere at all.
 *
 * Used twice: by the v1 → v2 migration to decide the backfill order, and by
 * `orderForUpload` as a runtime backstop in case a row without a seq is ever
 * seen anyway. The migration is the mechanism; this is the belt.
 */
function compareLegacy(a: SortableRow, b: SortableRow): number {
    const ta = scannedAtMillis(a);
    const tb = scannedAtMillis(b);
    if (ta === null && tb !== null) return 1;
    if (ta !== null && tb === null) return -1;
    if (ta !== null && tb !== null && ta !== tb) return ta - tb;
    return compareIDs(a, b);
}

/**
 * The total order an uploaded batch is sent in: unsequenced rows first (they
 * predate the upgrade, so they genuinely happened before anything sequenced),
 * then by `seq`, then by primary key.
 *
 * The final `id` comparison is what makes this TOTAL. Without it two rows with
 * an equal key are left in whatever order the caller passed them, which for
 * `getPendingSync` is IndexedDB's primary-key order and for anything else is
 * unspecified — the same batch could be uploaded in two different orders.
 * `seq` values are distinct in practice, so the tiebreaker is defence rather
 * than daily traffic; it is tested at the comparator, over every permutation
 * of a degenerate input, because that is the only place it is observable.
 *
 * Pure, and does not mutate its argument.
 */
export function orderForUpload<T extends SortableRow>(rows: T[]): T[] {
    return [...rows].sort((a, b) => {
        const sa = typeof a?.seq === 'number' ? a.seq : null;
        const sb = typeof b?.seq === 'number' ? b.seq : null;
        if (sa === null && sb === null) return compareLegacy(a, b);
        if (sa === null) return -1;
        if (sb === null) return 1;
        if (sa !== sb) return sa - sb;
        return compareIDs(a, b);
    });
}

/**
 * The next local sequence number, read inside the caller's readwrite
 * transaction so that read-max-then-insert is atomic — IndexedDB serialises
 * transactions with overlapping scope, so two scans cannot be handed the same
 * number even from two tabs.
 *
 * Derived from the store rather than kept in a counter row: there is then no
 * second piece of state that can disagree with the rows themselves, and the
 * migration's backfill is picked up for free. Rows with no `seq` are absent
 * from the index, which is why they must be backfilled — and why they sort
 * first if they somehow are not.
 *
 * Deleting every admission (deleteBundle for the last cached event) restarts
 * the counter at 1. That is harmless: the batch is ordered within one event's
 * pending rows, so a number reused by a later, unrelated event can never
 * interleave with a live queue — and `compareIDs` keeps the order total even
 * if it did.
 */
async function nextSeq(store: IDBPTransaction<ScanDB, ['admissions'], 'readwrite'>['store']): Promise<number> {
    const cursor = await store.index(IDX_SEQ).openKeyCursor(null, 'prev');
    const highest = cursor && typeof cursor.key === 'number' ? cursor.key : 0;
    return highest + 1;
}

/**
 * Cache a scan bundle fetched from GET /api/events/:id/scan-bundle. Shape:
 * { event, issuer_keys, ticket_index[], ticket_index_present,
 * admitted_index[], allocation, issued_at } — see internal/scan/bundle.go and
 * docs/OFFLINE-GATES.md.
 * `ticket_index_present` is the one that decides whether an EMPTY index means
 * "admit nothing" or "no data, fall back to signature-only".
 * `admitted_index` is the tickets already admitted anywhere as of the
 * bundle's issued_at — the channel by which re-pulling a bundle carries other
 * gates' admissions down to this device; `allocation` is always null today
 * (unbuilt delegated issuance).
 */
export async function saveBundle(eventId: string, bundle: Record<string, unknown>): Promise<void> {
    const db = await getDB();
    await db.put(STORE_BUNDLES, {
        event_id: eventId,
        ...bundle,
        cached_at: new Date().toISOString(),
    });
}

export async function getBundle(eventId: string) {
    const db = await getDB();
    return db.get(STORE_BUNDLES, eventId);
}

export async function listCachedBundles() {
    const db = await getDB();
    return db.getAll(STORE_BUNDLES);
}

export async function deleteBundle(eventId: string): Promise<void> {
    const db = await getDB();
    const tx = db.transaction([STORE_BUNDLES, STORE_ADMISSIONS], 'readwrite');
    await tx.objectStore(STORE_BUNDLES).delete(eventId);
    const admissionsStore = tx.objectStore(STORE_ADMISSIONS);
    const idx = admissionsStore.index('by_event');
    let cursor = await idx.openCursor(IDBKeyRange.only(eventId));
    while (cursor) {
        await cursor.delete();
        cursor = await cursor.continue();
    }
    await tx.done;
}

/** True if this ticket already has an 'admitted' row for this event. */
export async function wasAdmitted(eventId: string, ticketId: string): Promise<boolean> {
    const db = await getDB();
    const idx = db.transaction(STORE_ADMISSIONS).store.index('by_event_ticket');
    const rows = await idx.getAll(IDBKeyRange.only([eventId, ticketId]));
    return rows.some((r) => r.result === 'admitted');
}

/**
 * Append-only insert of a scan attempt. Never overwrites — duplicates get
 * their own row, mirroring internal/scan's server-side design so the local
 * mirror and the eventual server state agree once synced.
 */
export async function recordScan({
    eventId,
    ticketId,
    deviceId,
    gateId,
    result,
    note = null,
    holderName = null,
    scannedAt,
}: {
    eventId: string;
    ticketId?: string | null;
    deviceId: string;
    gateId: string;
    result: string;
    note?: string | null;
    holderName?: string | null;
    scannedAt?: string;
}): Promise<AdmissionRecord> {
    const db = await getDB();
    const record: AdmissionRecord = {
        id: uuid(),
        event_id: eventId,
        ticket_id: ticketId ?? null,
        device_id: deviceId,
        gate_id: gateId,
        scanned_at: scannedAt || new Date().toISOString(),
        result, // 'admitted' | 'duplicate' | 'invalid' | 'wrong_event'
        note,
        holder_name: holderName,
        synced: 0,
    };
    // seq is read and written inside ONE readwrite transaction, so the number
    // this row gets cannot be handed to another scan as well. It is what
    // `getPendingSync` orders the upload batch by — see the "Batch order"
    // note above for why it is a local counter and not the wall clock.
    const tx = db.transaction(STORE_ADMISSIONS, 'readwrite');
    record.seq = await nextSeq(tx.store);
    await tx.store.add(record);
    await tx.done;
    return record;
}

export async function getAdmissionsForEvent(eventId: string) {
    const db = await getDB();
    return db.getAllFromIndex(STORE_ADMISSIONS, 'by_event', eventId);
}

/** getTally's return shape: named counts a caller can read without an
 * indexed lookup (a plain `Record<string, number>` would make even
 * `tally.admitted` read as `number | undefined` under
 * noUncheckedIndexedAccess). */
export interface Tally {
    admitted: number;
    duplicate: number;
    invalid: number;
    wrong_event: number;
    total: number;
}

export async function getTally(eventId: string): Promise<Tally> {
    const rows = await getAdmissionsForEvent(eventId);
    const tally: Tally = { admitted: 0, duplicate: 0, invalid: 0, wrong_event: 0, total: rows.length };
    for (const row of rows) {
        // `result` is a plain `string` on the record (not the RESULT union),
        // so branch explicitly rather than index into `tally` by it — an
        // unrecognised value is silently not counted, same as before.
        if (row.result === 'admitted') tally.admitted++;
        else if (row.result === 'duplicate') tally.duplicate++;
        else if (row.result === 'invalid') tally.invalid++;
        else if (row.result === 'wrong_event') tally.wrong_event++;
    }
    return tally;
}

/**
 * The batch to upload, OLDEST SCAN FIRST — and that is a contract, not a
 * convenience. `getAllFromIndex` returns rows ordered by index key and then by
 * primary key, and the primary key here is a random UUID, so the raw result is
 * in random order; the server decides a contested ticket by array position.
 * `orderForUpload` is what makes the position mean something. See its note.
 */
export async function getPendingSync(eventId: string) {
    const db = await getDB();
    const rows = await db.getAllFromIndex(STORE_ADMISSIONS, 'by_event', eventId);
    return orderForUpload(rows.filter((r) => !r.synced));
}

export async function markSynced(ids: string[]): Promise<void> {
    if (!ids.length) return;
    const db = await getDB();
    const tx = db.transaction(STORE_ADMISSIONS, 'readwrite');
    for (const id of ids) {
        const row = await tx.store.get(id);
        if (row) {
            row.synced = 1;
            await tx.store.put(row);
        }
    }
    await tx.done;
}
