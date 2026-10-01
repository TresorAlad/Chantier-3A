"""Pure check-in rules: no database, no FastAPI (see docs/checkin/ADR-001-conflits.md)."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable

from tickets import capability as cap

# ── Vocabulary ──────────────────────────────────────────────────────────────

DEFAULT_STATION = "EVENT_ENTRY"
STATION_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,31}$")

VALID = "valid"
ALREADY_SCANNED = "already_scanned"
NOT_AUTHORIZED = "not_authorized"
INVALID = "invalid"
EXPIRED = "expired"
NOT_YET_VALID = "not_yet_valid"
UNKNOWN = "unknown"
WRONG_EVENT = "wrong_event"
REVOKED = "revoked"

SERVER_DECISIONS = frozenset(
    {VALID, ALREADY_SCANNED, NOT_AUTHORIZED, INVALID, EXPIRED, NOT_YET_VALID, UNKNOWN, WRONG_EVENT, REVOKED}
)

CROSS_TERMINAL_DOUBLE_ADMISSION = "CROSS_TERMINAL_DOUBLE_ADMISSION"
SAME_TERMINAL_REPLAY = "SAME_TERMINAL_REPLAY"
LATE_REVOKED = "LATE_REVOKED"
NOT_AUTHORIZED_SERVER_SIDE = "NOT_AUTHORIZED_SERVER_SIDE"
CLOCK_SUSPECT = "CLOCK_SUSPECT"

_DECISION_ALIASES = {
    "valid": VALID,
    "alreadyscanned": ALREADY_SCANNED,
    "already_scanned": ALREADY_SCANNED,
    "invalid": INVALID,
    "notauthorized": NOT_AUTHORIZED,
    "not_authorized": NOT_AUTHORIZED,
    "expired": EXPIRED,
    "unknown": UNKNOWN,
}

_CAP_ERROR_DECISION = {
    cap.ErrExpired: (EXPIRED, "expired"),
    cap.ErrNotYetValid: (NOT_YET_VALID, "not_yet_valid"),
    cap.ErrBadSignature: (INVALID, "bad_signature"),
    cap.ErrUnknownKID: (INVALID, "unknown_kid"),
    cap.ErrUnsupportedVersion: (INVALID, "unsupported_version"),
    cap.ErrMalformed: (INVALID, "malformed"),
}


def normalize_station(raw: str | None) -> str | None:
    """Return the canonical ``UPPER_SNAKE`` station or ``None`` when malformed.

    Accepts the camelCase Dart enum names sent by the 3B app (``eventEntry``) as well as
    ``EVENT_ENTRY``.
    """
    if not isinstance(raw, str) or not raw.strip():
        return None
    s = raw.strip()
    if "_" not in s and not s.isupper():
        s = re.sub(r"(?<!^)(?=[A-Z])", "_", s)
    s = s.upper()
    return s if STATION_RE.match(s) else None


def normalize_decision(raw: str | None) -> str | None:
    """Map a terminal decision (camelCase or snake/UPPER) to its canonical snake_case form."""
    if not isinstance(raw, str):
        return None
    return _DECISION_ALIASES.get(raw.strip().replace("-", "_").lower())


def classify_capability_error(err: cap.CapabilityError) -> tuple[str, str]:
    """Return ``(server_decision, reason)`` for a capability verification failure."""
    for klass, out in _CAP_ERROR_DECISION.items():
        if isinstance(err, klass):
            return out
    return INVALID, "malformed"


# ── Station rules ───────────────────────────────────────────────────────────


def allowed_max_uses(station: str, explicit_rules: dict[str, int]) -> int:
    """Return how many times ``station`` may be consumed for a ticket type.

    ``explicit_rules`` maps station -> ``max_uses`` for the ticket type. Without a row, only
    ``EVENT_ENTRY`` is allowed (once): the most cautious default (docs/checkin/DESIGN.md §1.2).
    """
    if station in explicit_rules:
        return explicit_rules[station]
    return 1 if station == DEFAULT_STATION else 0


@dataclass(frozen=True)
class TicketFacts:
    """The 3A ticket attributes the decision needs."""

    ticket_id: str
    event_id: str
    ticket_type_id: str
    status: str
    serial: str = ""
    voided_at: datetime | None = None


@dataclass(frozen=True)
class Eligibility:
    """Operation-intrinsic eligibility; never depends on current consumption state."""

    eligible: bool
    decision: str  # server decision when not eligible, VALID when eligible
    reason: str = ""
    max_uses: int = 0
    conflict_type: str | None = None  # LATE_REVOKED / NOT_AUTHORIZED_SERVER_SIDE when it applies


def check_eligibility(
    *,
    ticket: TicketFacts | None,
    event_id: str,
    station: str,
    explicit_rules: dict[str, int],
    at: datetime,
    capability_verified: bool | None = None,
) -> Eligibility:
    """Decide whether an operation may *claim* a consumption (ADR-001 §2)."""
    if ticket is None:
        return Eligibility(False, UNKNOWN, "ticket_not_found", conflict_type=NOT_AUTHORIZED_SERVER_SIDE)
    if ticket.event_id != event_id:
        return Eligibility(False, WRONG_EVENT, "wrong_event", conflict_type=NOT_AUTHORIZED_SERVER_SIDE)
    if capability_verified is False:
        return Eligibility(False, INVALID, "signature_invalid", conflict_type=NOT_AUTHORIZED_SERVER_SIDE)
    if ticket.status != "valid":
        # Unknown void date => treated as revoked before the scan (cautious default).
        if ticket.voided_at is None or ticket.voided_at <= at:
            return Eligibility(False, REVOKED, "ticket_revoked", conflict_type=LATE_REVOKED)
    max_uses = allowed_max_uses(station, explicit_rules)
    if max_uses <= 0:
        return Eligibility(False, NOT_AUTHORIZED, "station_not_allowed", conflict_type=NOT_AUTHORIZED_SERVER_SIDE)
    return Eligibility(True, VALID, "", max_uses=max_uses)


# ── Clock correction ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ClockThresholds:
    """Technical safety thresholds (configurable; not business rules)."""

    offset_max: timedelta = timedelta(seconds=300)
    future_tolerance: timedelta = timedelta(seconds=60)
    max_age: timedelta = timedelta(hours=72)


@dataclass(frozen=True)
class ClockInfo:
    """Clock correction figures frozen into each log row."""

    offset_ms: int
    corrected_at: datetime
    suspect: bool
    reason: str = ""


def _ms(delta: timedelta) -> int:
    return int(delta.total_seconds() * 1000)


def correct_clock(
    *,
    device_evaluated_at: datetime | None,
    device_sent_at: datetime | None,
    received_at: datetime,
    thresholds: ClockThresholds,
) -> ClockInfo:
    """Per-batch correction: ``offset = received_at - device_sent_at`` (never smoothed).

    Online scans (no device times) get offset 0 and ``corrected_at = received_at``.
    """
    if device_evaluated_at is None or device_sent_at is None:
        return ClockInfo(0, device_evaluated_at or received_at, False)
    offset = received_at - device_sent_at
    corrected = device_evaluated_at + offset
    reasons: list[str] = []
    if abs(offset) > thresholds.offset_max:
        reasons.append("offset_too_large")
    if corrected > received_at + thresholds.future_tolerance:
        reasons.append("in_the_future")
    if corrected < received_at - thresholds.max_age:
        reasons.append("too_old")
    return ClockInfo(_ms(offset), corrected, bool(reasons), ",".join(reasons))


# ── Claims, ranking and conflicts ───────────────────────────────────────────


@dataclass(frozen=True)
class Claim:
    """A claimant for one (ticket, station) consumption."""

    operation_id: str
    terminal_id: str
    corrected_at: datetime
    suspect: bool = False
    log_id: int | None = None

    @property
    def sort_key(self) -> tuple[bool, datetime, str]:
        """Total order of ADR-001 §1: non-suspect first, then oldest, then operation_id."""
        return (self.suspect, self.corrected_at, self.operation_id)


@dataclass(frozen=True)
class ConflictSpec:
    """A conflict row to (up)sert for ``losing_operation_id``."""

    losing_operation_id: str
    winning_operation_id: str | None
    type: str
    clock_suspect: bool = False


@dataclass
class Resolution:
    """Result of ranking one (ticket, station) group."""

    ranking: list[Claim]
    assigned: list[Claim]  # assigned[i] holds use_index i
    losers: list[Claim]
    conflicts: list[ConflictSpec] = field(default_factory=list)

    def use_index_of(self, operation_id: str) -> int | None:
        """Return the use_index held by ``operation_id`` or ``None`` if it lost."""
        for i, c in enumerate(self.assigned):
            if c.operation_id == operation_id:
                return i
        return None


def classify_loser(loser: Claim, winner: Claim) -> str:
    """Type of the conflict for a claimant that lost to ``winner`` (ADR-001 §4, rows 3-4)."""
    if loser.terminal_id == winner.terminal_id:
        return SAME_TERMINAL_REPLAY
    return CROSS_TERMINAL_DOUBLE_ADMISSION


def resolve(claims: Iterable[Claim], max_uses: int) -> Resolution:
    """Rank claimants and assign the first ``max_uses`` of them a ``use_index``.

    The outcome depends only on the *set* of claims, never on the order they are supplied in
    (total order with ``operation_id`` as the last tie-breaker), hence convergence.
    """
    unique: dict[str, Claim] = {}
    for c in claims:
        unique.setdefault(c.operation_id, c)
    ranking = sorted(unique.values(), key=lambda c: c.sort_key)
    assigned = ranking[: max(max_uses, 0)]
    losers = ranking[len(assigned):]
    conflicts: list[ConflictSpec] = []
    if assigned:
        reference = assigned[-1]  # the holder of the last slot: the one the loser was beaten by
        for loser in losers:
            ctype = classify_loser(loser, reference)
            conflicts.append(
                ConflictSpec(
                    loser.operation_id,
                    reference.operation_id,
                    ctype,
                    clock_suspect=loser.suspect or reference.suspect,
                )
            )
        if not losers:
            for c in assigned:
                if c.suspect:
                    conflicts.append(ConflictSpec(c.operation_id, None, CLOCK_SUSPECT, True))
    return Resolution(ranking, assigned, losers, conflicts)


# ── Idempotency ─────────────────────────────────────────────────────────────


def payload_hash(fields: dict) -> bytes:
    """SHA-256 of the canonical JSON of the contract fields (detects operation_id reuse).

    The raw capability (QR) is never part of ``fields``.
    """
    blob = json.dumps(fields, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(blob).digest()
