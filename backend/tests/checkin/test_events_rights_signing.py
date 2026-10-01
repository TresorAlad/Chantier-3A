"""GET /api/checkin/events, per-ticket-type scan rights, participant data and the signed snapshot."""

from __future__ import annotations

import base64

import pytest
from checkin_fixtures import applied_schema, checkin_rt, clock, commit_3a, db  # noqa: F401  (fixtures)
from checkin_helpers import add_rule, make_world, scan_body
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from checkin.signing import HEADER, SnapshotSigner

EVENTS = "/api/checkin/events"
SNAP = "/api/checkin/snapshot"
KEY = "/api/checkin/signing-key"
SCAN = "/api/checkin/scan"


@pytest.fixture()
def world(client, db, checkin_rt, commit_3a):
    return make_world(client, db, commit_3a, type_names=("GA", "VIP"), per_type=2)


def snap(client, world, **params):
    return client.get(SNAP, params={"event_id": world.event_id, **params}, headers=world.scanner)


def stations_of(client, world, type_name):
    body = snap(client, world).json()
    return {tuple(e["stations"]) for e in body["entitlements"] if e["ticket_type_id"] == world.type_ids[type_name]}


# ── GET /events ─────────────────────────────────────────────────────────────


def test_events_lists_the_published_events_of_the_agent(client, world):
    r = client.get(EVENTS, headers=world.scanner)
    assert r.status_code == 200, r.text
    events = r.json()["events"]
    assert [e["event_id"] for e in events] == [world.event_id]
    assert events[0]["role"] == "scanner" and events[0]["title"] == "Check-in event"
    assert {"slug", "starts_at", "ends_at", "timezone"} <= set(events[0])
    assert client.get(EVENTS, headers=world.admin).json()["events"][0]["role"] == "owner"


def test_events_is_empty_for_a_user_without_organisation_and_hides_drafts(client, world):
    assert client.get(EVENTS, headers=world.outsider).json() == {"events": []}
    draft = client.post(
        "/api/events",
        json={
            "org_id": world.org_id,
            "slug": "draft-" + world.event_id[-6:].lower(),
            "title": "Draft",
            "starts_at": "2030-01-01T10:00:00Z",
            "ends_at": "2030-01-01T18:00:00Z",
        },
        headers=world.admin,
    )
    assert draft.status_code == 201, draft.text
    ids = [e["event_id"] for e in client.get(EVENTS, headers=world.scanner).json()["events"]]
    assert ids == [world.event_id]


def test_events_requires_authentication(client, world):
    assert client.get(EVENTS).status_code == 401


# ── Scan rights set by the organizer on the ticket type ─────────────────────


def test_default_rights_allow_only_the_main_entrance(client, world):
    assert stations_of(client, world, "GA") == {("EVENT_ENTRY",)}
    ga = client.get(f"/api/events/{world.event_id}/ticket-types", headers=world.admin).json()
    rights = [t["scan_rights"] for t in ga["ticket_types"]]
    assert all(r == {"event_entry": True, "food_access": False, "merch_pickup": False, "after_entry": False} for r in rights)


def test_organizer_flag_enables_a_station_in_snapshot_and_scan(client, world, checkin_rt):
    ticket = next(t for t in world.tickets if t["type_name"] == "VIP")
    refused = client.post(SCAN, json=scan_body(world, ticket, world.terminal(), "FOOD_ACCESS"), headers=world.scanner)
    assert refused.json()["server_decision"] == "not_authorized"

    patch = client.patch(f"/api/ticket-types/{world.type_ids['VIP']}", json={"name": "VIP", "access_food": True}, headers=world.admin)
    assert patch.status_code == 200, patch.text
    assert patch.json()["ticket_type"]["scan_rights"]["food_access"] is True
    client.cookies.clear()

    ok = client.post(SCAN, json=scan_body(world, ticket, world.terminal(), "FOOD_ACCESS"), headers=world.scanner)
    assert ok.json()["server_decision"] == "valid", ok.text
    # the snapshot recomputes at most every snapshot_ttl_seconds: force it for the test
    with checkin_rt.pool.connection() as conn:
        conn.execute("UPDATE checkin_snapshot_meta SET refreshed_at = now() - interval '1 hour'")
        conn.commit()
    assert stations_of(client, world, "VIP") == {("EVENT_ENTRY", "FOOD_ACCESS")}
    assert stations_of(client, world, "GA") == {("EVENT_ENTRY",)}


def test_explicit_rule_overrides_the_flag(client, db, world):
    off = client.patch(f"/api/ticket-types/{world.type_ids['GA']}", json={"name": "GA", "access_event": False}, headers=world.admin)
    assert off.status_code == 200 and off.json()["ticket_type"]["scan_rights"]["event_entry"] is False, off.text
    client.cookies.clear()
    ticket = next(t for t in world.tickets if t["type_name"] == "GA")
    blocked = client.post(SCAN, json=scan_body(world, ticket, world.terminal()), headers=world.scanner)
    assert blocked.json()["server_decision"] == "not_authorized"
    add_rule(db, world, "GA", "EVENT_ENTRY", 1)  # explicit row wins over the flag
    ok = client.post(SCAN, json=scan_body(world, ticket, world.terminal()), headers=world.scanner)
    assert ok.json()["server_decision"] == "valid"


def test_rights_must_be_booleans(client, world):
    r = client.patch(f"/api/ticket-types/{world.type_ids['GA']}", json={"access_food": "yes"}, headers=world.admin)
    assert r.status_code == 400


# ── Participant data ────────────────────────────────────────────────────────


def test_online_scan_returns_name_and_pass_type_only(client, world):
    ticket = world.tickets[0]
    body = client.post(SCAN, json=scan_body(world, ticket, world.terminal()), headers=world.scanner).json()
    assert body["participant"]["holder_name"] == "Buyer" and body["participant"]["pass_type"] == "GA"
    assert set(body["participant"]) == {"holder_name", "pass_type"}


def test_ticket_of_another_event_gets_no_participant(client, db, world, commit_3a):
    other = make_world(client, db, commit_3a)
    body = client.post(SCAN, json=scan_body(world, other.tickets[0], world.terminal()), headers=world.scanner).json()
    assert body["server_decision"] == "wrong_event" and body["participant"] is None


# ── Signed snapshot ─────────────────────────────────────────────────────────


def parse(header: str) -> tuple[str, bytes]:
    alg, kid, sig = (part.split("=", 1)[-1].strip() for part in header.split(";"))
    assert alg == "Ed25519"
    return kid, base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4))


def pinned_key(client, world) -> Ed25519PublicKey:
    info = client.get(KEY).json()
    raw = base64.urlsafe_b64decode(info["public_key"] + "=" * (-len(info["public_key"]) % 4))
    return Ed25519PublicKey.from_public_bytes(raw)


def test_snapshot_is_signed_and_the_signature_verifies_with_the_pinned_key(client, world, checkin_rt):
    checkin_rt.signer = SnapshotSigner.generate()
    r = snap(client, world)
    kid, sig = parse(r.headers[HEADER])
    assert kid == client.get(KEY).json()["kid"] == r.json()["signing_key_id"]
    pinned_key(client, world).verify(sig, r.content)  # raises on failure


def test_any_change_of_rights_or_uses_breaks_the_signature(client, world, checkin_rt):
    checkin_rt.signer = SnapshotSigner.generate()
    r = snap(client, world)
    _kid, sig = parse(r.headers[HEADER])
    key = pinned_key(client, world)
    forged = r.content.replace(b'"stations":["EVENT_ENTRY"]', b'"stations":["EVENT_ENTRY","FOOD_ACCESS"]', 1)
    assert forged != r.content
    with pytest.raises(InvalidSignature):
        key.verify(sig, forged)
    forged_uses = r.content.replace(b'"uses":{}', b'"uses":{"EVENT_ENTRY":0,"X":1}', 1)
    with pytest.raises(InvalidSignature):
        key.verify(sig, forged_uses)


def test_signature_covers_the_uncompressed_body_and_survives_gzip_and_304(client, world, checkin_rt):
    checkin_rt.signer = SnapshotSigner.generate()
    plain = snap(client, world)
    zipped = client.get(
        SNAP, params={"event_id": world.event_id}, headers={**world.scanner, "Accept-Encoding": "gzip"}
    )
    assert zipped.headers.get(HEADER) == plain.headers[HEADER]
    assert zipped.headers.get("content-encoding") == "gzip" and zipped.content == plain.content  # client un-gzips
    again = client.get(SNAP, params={"event_id": world.event_id}, headers={**world.scanner, "If-None-Match": plain.headers["ETag"]})
    assert again.status_code == 304 and again.headers.get(HEADER) == plain.headers[HEADER]


def test_pages_of_a_paginated_snapshot_are_each_signed(client, world, checkin_rt):
    checkin_rt.signer = SnapshotSigner.generate()
    first = snap(client, world, limit=1)
    assert first.json()["has_more"] is True
    second = snap(client, world, limit=1, cursor=first.json()["next_cursor"])
    key = pinned_key(client, world)
    for page in (first, second):
        key.verify(parse(page.headers[HEADER])[1], page.content)
    assert first.headers[HEADER] != second.headers[HEADER]


def test_without_a_signing_key_the_snapshot_is_unsigned_and_the_key_endpoint_says_so(client, world, checkin_rt):
    checkin_rt.signer = None
    r = snap(client, world)
    assert HEADER not in r.headers and r.json()["signing_key_id"] is None
    assert client.get(KEY).status_code == 404


def test_a_malformed_signing_key_fails_at_startup():
    with pytest.raises(ValueError):
        SnapshotSigner.from_text("not-a-valid-key")
    with pytest.raises(ValueError):
        SnapshotSigner.from_text(base64.urlsafe_b64encode(b"short").decode())


def test_the_signing_key_is_never_in_the_repr_or_the_public_description():
    signer = SnapshotSigner.generate()
    seed = base64.urlsafe_b64encode(signer.seed).decode().rstrip("=")
    assert seed not in repr(signer) and seed not in str(signer.describe())
