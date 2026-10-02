"""Pure-domain tests (no database): rules, clock, ranking, conflicts, capability vectors."""

from __future__ import annotations

import base64
import itertools
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from checkin import domain
from checkin.domain import Claim, ClockThresholds, TicketFacts
from checkin.service import verify_capability
from tickets import capability as cap

T0 = datetime(2026, 10, 3, 8, 0, 0, tzinfo=timezone.utc)
VECTORS = Path(__file__).resolve().parents[2] / "docs" / "pass-format-vectors.json"


# ── Vocabulary ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("eventEntry", "EVENT_ENTRY"),
        ("EVENT_ENTRY", "EVENT_ENTRY"),
        ("foodAccess", "FOOD_ACCESS"),
        ("merchPickup", "MERCH_PICKUP"),
        ("afterEntry", "AFTER_ENTRY"),
        ("  afterEntry ", "AFTER_ENTRY"),
        ("", None),
        ("x", None),
        ("bad station!", None),
        (None, None),
        ("1ABC", None),
    ],
)
def test_normalize_station(raw, expected):
    assert domain.normalize_station(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("valid", "valid"),
        ("alreadyScanned", "already_scanned"),
        ("ALREADY_SCANNED", "already_scanned"),
        ("notAuthorized", "not_authorized"),
        ("NOT_AUTHORIZED", "not_authorized"),
        ("expired", "expired"),
        ("unknown", "unknown"),
        ("invalid", "invalid"),
        ("nonsense", None),
        (None, None),
    ],
)
def test_normalize_decision(raw, expected):
    assert domain.normalize_decision(raw) == expected


def test_default_rule_only_event_entry_is_allowed():
    assert domain.allowed_max_uses("EVENT_ENTRY", {}) == 1
    for station in ("FOOD_ACCESS", "MERCH_PICKUP", "AFTER_ENTRY"):
        assert domain.allowed_max_uses(station, {}) == 0
    assert domain.allowed_max_uses("FOOD_ACCESS", {"FOOD_ACCESS": 2}) == 2
    assert domain.allowed_max_uses("EVENT_ENTRY", {"EVENT_ENTRY": 0}) == 0  # explicit deny
    assert domain.allowed_max_uses("EVENT_ENTRY", {"EVENT_ENTRY": 3}) == 3


# ── Eligibility ─────────────────────────────────────────────────────────────


def _ticket(**kw) -> TicketFacts:
    base = dict(ticket_id="t1", event_id="e1", ticket_type_id="tt1", status="valid", serial="TDEV-2026-0001")
    base.update(kw)
    return TicketFacts(**base)


def _elig(ticket, station="EVENT_ENTRY", rules=None, at=T0, verified=True, event="e1"):
    return domain.check_eligibility(
        ticket=ticket, event_id=event, station=station, explicit_rules=rules or {}, at=at, capability_verified=verified
    )


def test_eligible_default_entry():
    e = _elig(_ticket())
    assert e.eligible and e.decision == domain.VALID and e.max_uses == 1


def test_unknown_ticket():
    e = _elig(None)
    assert not e.eligible and e.decision == domain.UNKNOWN
    assert e.conflict_type == domain.NOT_AUTHORIZED_SERVER_SIDE


def test_wrong_event():
    e = _elig(_ticket(event_id="other"))
    assert not e.eligible and e.decision == domain.WRONG_EVENT


def test_forged_capability_is_not_eligible():
    e = _elig(_ticket(), verified=False)
    assert not e.eligible and e.decision == domain.INVALID


def test_station_not_allowed_without_rule():
    e = _elig(_ticket(), station="FOOD_ACCESS")
    assert not e.eligible and e.decision == domain.NOT_AUTHORIZED
    assert _elig(_ticket(), station="FOOD_ACCESS", rules={"FOOD_ACCESS": 1}).eligible


def test_revoked_before_scan_vs_after_scan():
    voided_before = _ticket(status="void", voided_at=T0 - timedelta(minutes=1))
    e = _elig(voided_before)
    assert not e.eligible and e.decision == domain.REVOKED and e.conflict_type == domain.LATE_REVOKED
    voided_after = _ticket(status="void", voided_at=T0 + timedelta(minutes=1))
    assert _elig(voided_after).eligible  # the scan happened while the ticket was still valid
    unknown_date = _ticket(status="refunded", voided_at=None)
    assert not _elig(unknown_date).eligible  # cautious default: revoked before the scan


# ── Clock ───────────────────────────────────────────────────────────────────

TH = ClockThresholds(timedelta(seconds=300), timedelta(seconds=60), timedelta(hours=72))


def test_clock_online_has_no_offset():
    c = domain.correct_clock(device_evaluated_at=None, device_sent_at=None, received_at=T0, thresholds=TH)
    assert c.offset_ms == 0 and c.corrected_at == T0 and not c.suspect


def test_clock_offset_is_per_batch():
    # the phone runs 40 s slow: it says 08:14:20 when the server says 08:15:00
    sent = T0 + timedelta(minutes=14, seconds=20)
    received = T0 + timedelta(minutes=15)
    scanned = T0 + timedelta(minutes=1)
    c = domain.correct_clock(device_evaluated_at=scanned, device_sent_at=sent, received_at=received, thresholds=TH)
    assert c.offset_ms == 40_000
    assert c.corrected_at == scanned + timedelta(seconds=40)
    assert not c.suspect


def test_clock_suspect_cases():
    received = T0 + timedelta(hours=1)
    big_offset = domain.correct_clock(
        device_evaluated_at=received - timedelta(minutes=30),
        device_sent_at=received - timedelta(hours=2),
        received_at=received,
        thresholds=TH,
    )
    assert big_offset.suspect and "offset_too_large" in big_offset.reason
    future = domain.correct_clock(
        device_evaluated_at=received + timedelta(minutes=10),
        device_sent_at=received,
        received_at=received,
        thresholds=TH,
    )
    assert future.suspect and "in_the_future" in future.reason
    old = domain.correct_clock(
        device_evaluated_at=received - timedelta(days=5),
        device_sent_at=received,
        received_at=received,
        thresholds=TH,
    )
    assert old.suspect and "too_old" in old.reason


# ── Ranking, winner, conflicts ──────────────────────────────────────────────


def claim(op: str, term: str, seconds: float, suspect: bool = False) -> Claim:
    return Claim(operation_id=op, terminal_id=term, corrected_at=T0 + timedelta(seconds=seconds), suspect=suspect)


def test_oldest_corrected_time_wins_and_loser_is_cross_terminal():
    res = domain.resolve([claim("b", "T2", 2), claim("a", "T1", 1)], 1)
    assert [c.operation_id for c in res.assigned] == ["a"]
    assert [c.operation_id for c in res.losers] == ["b"]
    assert res.conflicts[0].type == domain.CROSS_TERMINAL_DOUBLE_ADMISSION
    assert res.conflicts[0].winning_operation_id == "a"


def test_same_terminal_is_benign_replay():
    res = domain.resolve([claim("a", "T1", 1), claim("b", "T1", 2)], 1)
    assert res.conflicts[0].type == domain.SAME_TERMINAL_REPLAY


def test_tie_is_broken_by_operation_id():
    res = domain.resolve([claim("b", "T2", 1), claim("a", "T1", 1)], 1)
    assert res.assigned[0].operation_id == "a"


def test_suspect_clock_never_beats_a_plausible_scan():
    # the suspect one claims to be way earlier, but ranks after every non-suspect claim
    res = domain.resolve([claim("fraud", "T9", -10_000, suspect=True), claim("ok", "T1", 50)], 1)
    assert res.assigned[0].operation_id == "ok"
    assert res.conflicts[0].clock_suspect is True


def test_lone_suspect_claim_is_accepted_and_flagged():
    res = domain.resolve([claim("x", "T1", 5, suspect=True)], 1)
    assert res.assigned[0].operation_id == "x"
    assert [(c.type, c.winning_operation_id) for c in res.conflicts] == [(domain.CLOCK_SUSPECT, None)]


def test_max_uses_two_allows_two_entries():
    res = domain.resolve([claim("a", "T1", 1), claim("b", "T2", 2), claim("c", "T3", 3)], 2)
    assert [res.use_index_of(o) for o in ("a", "b", "c")] == [0, 1, None]
    assert [c.losing_operation_id for c in res.conflicts] == ["c"]


def test_duplicate_operation_ids_are_collapsed():
    res = domain.resolve([claim("a", "T1", 1), claim("a", "T1", 1)], 1)
    assert len(res.ranking) == 1 and not res.losers


def test_result_does_not_depend_on_arrival_order():
    claims = [
        claim("a", "T1", 3),
        claim("b", "T2", 1),
        claim("c", "T3", 1),
        claim("d", "T2", 7, suspect=True),
        claim("e", "T1", 2),
    ]
    outcomes = set()
    for perm in itertools.permutations(claims):
        res = domain.resolve(list(perm), 2)
        outcomes.add(
            (
                tuple(c.operation_id for c in res.assigned),
                tuple(sorted((s.losing_operation_id, s.winning_operation_id, s.type) for s in res.conflicts)),
            )
        )
    assert len(outcomes) == 1


def test_adding_a_claim_never_improves_anyone_rank():
    base = [claim("a", "T1", 2), claim("b", "T2", 3)]
    before = domain.resolve(base, 1)
    after = domain.resolve(base + [claim("z", "T3", 1)], 1)
    assert after.use_index_of("z") == 0
    assert before.use_index_of("a") == 0 and after.use_index_of("a") is None  # a winner may lose its place
    assert before.use_index_of("b") is None and after.use_index_of("b") is None  # a loser stays a loser


def test_payload_hash_is_stable_and_field_sensitive():
    h1 = domain.payload_hash({"a": 1, "b": "x"})
    assert h1 == domain.payload_hash({"b": "x", "a": 1})
    assert h1 != domain.payload_hash({"a": 2, "b": "x"})


# ── Capability verification against the 3A conformance vectors ──────────────


@pytest.fixture(scope="module")
def vectors():
    return json.loads(VECTORS.read_text(encoding="utf-8"))


_EXPECTED = {
    None: (domain.VALID, ""),
    "malformed": (domain.INVALID, "malformed"),
    "unsupported_version": (domain.INVALID, "unsupported_version"),
    "bad_signature": (domain.INVALID, "bad_signature"),
    "not_yet_valid": (domain.NOT_YET_VALID, "not_yet_valid"),
    "expired": (domain.EXPIRED, "expired"),
    "unknown_kid": (domain.INVALID, "unknown_kid"),
}


def test_verify_capability_matches_3a_vectors(vectors):
    for vec in vectors["verify"]:
        pub = base64.urlsafe_b64decode(vectors["keys"][vec["key"]]["public_key_b64url"] + "==")
        now = datetime.fromtimestamp(vec["now_unix"], tz=timezone.utc)

        def keys_for(_event, vec=vec, pub=pub):
            if vec.get("error") == "unknown_kid":
                return {}
            try:
                return {cap.peek_kid(vec["token"]): pub}
            except Exception:
                return {}

        payload, decision, reason, _sig, _tid = verify_capability(vec["token"], keys_for_event=keys_for, now=now)
        expected_decision, expected_reason = _EXPECTED[vec.get("error")]
        assert (decision, reason) == (expected_decision, expected_reason), vec["name"]
        if vec["result"] == "ok":
            assert payload is not None and payload.tid == vec["tid"], vec["name"]
        else:
            assert payload is None


def test_verify_capability_never_returns_an_id_for_a_forged_token(vectors):
    forged = next(v for v in vectors["verify"] if v.get("error") == "bad_signature")
    pub = base64.urlsafe_b64decode(vectors["keys"][forged["key"]]["public_key_b64url"] + "==")
    now = datetime.fromtimestamp(forged["now_unix"], tz=timezone.utc)
    _p, decision, _r, sig_ok, audit_tid = verify_capability(
        forged["token"], keys_for_event=lambda _e: {cap.peek_kid(forged["token"]): pub}, now=now
    )
    assert decision == domain.INVALID and sig_ok is False and audit_tid is None


def test_garbage_tokens_are_malformed():
    for token in ("", "abc", "a.b.c", "chantier3a.!!!.###", "chantier3a.e30.e30"):
        _p, decision, reason, _s, tid = verify_capability(token, keys_for_event=lambda _e: {}, now=T0)
        assert decision == domain.INVALID and tid is None, token
        assert reason in ("malformed", "unknown_kid"), (token, reason)
