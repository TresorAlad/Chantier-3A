"""Check-in module configuration: environment variables only, cautious defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import timedelta

from checkin.domain import ClockThresholds

DEFAULT_STATIONS = ("EVENT_ENTRY", "FOOD_ACCESS", "MERCH_PICKUP", "AFTER_ENTRY")


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


@dataclass(frozen=True)
class CheckinConfig:
    """Runtime settings of the check-in module (all overridable via ``CHECKIN_*``)."""

    database_url: str = ""
    pool_min: int = 2
    pool_max: int = 10
    stations: tuple[str, ...] = DEFAULT_STATIONS
    sync_max_batch: int = 500
    snapshot_ttl_seconds: int = 15
    stats_ttl_seconds: int = 2
    keys_ttl_seconds: int = 30
    auth_cache_seconds: int = 0
    snapshot_page_default: int = 2000
    snapshot_page_max: int = 5000
    lock_timeout_ms: int = 2000
    rate_limit_per_terminal: int = 600
    clock: ClockThresholds = field(default_factory=ClockThresholds)

    @classmethod
    def from_env(cls, database_url: str = "") -> CheckinConfig:
        """Build the configuration from ``CHECKIN_*`` variables (see ``backend/.env.example``)."""
        stations_raw = os.environ.get("CHECKIN_STATIONS", "").strip()
        stations = (
            tuple(s.strip().upper() for s in stations_raw.split(",") if s.strip())
            if stations_raw
            else DEFAULT_STATIONS
        )
        return cls(
            database_url=(
                os.environ.get("CHECKIN_DATABASE_URL", "").strip()
                or database_url
                or os.environ.get("CHANTIER3A_DATABASE_URL", "").strip()
            ),
            pool_min=_int("CHECKIN_DB_POOL_MIN", 2),
            pool_max=_int("CHECKIN_DB_POOL_MAX", 10),
            stations=stations,
            sync_max_batch=_int("CHECKIN_SYNC_MAX_BATCH", 500),
            snapshot_ttl_seconds=_int("CHECKIN_SNAPSHOT_TTL_SECONDS", 15),
            stats_ttl_seconds=_int("CHECKIN_STATS_TTL_SECONDS", 2),
            keys_ttl_seconds=_int("CHECKIN_KEYS_TTL_SECONDS", 30),
            auth_cache_seconds=_int("CHECKIN_AUTH_CACHE_SECONDS", 0),
            lock_timeout_ms=_int("CHECKIN_LOCK_TIMEOUT_MS", 2000),
            rate_limit_per_terminal=_int("CHECKIN_RATE_LIMIT_PER_TERMINAL", 600),
            clock=ClockThresholds(
                offset_max=timedelta(seconds=_int("CHECKIN_CLOCK_OFFSET_MAX_SECONDS", 300)),
                future_tolerance=timedelta(seconds=_int("CHECKIN_CLOCK_FUTURE_TOLERANCE_SECONDS", 60)),
                max_age=timedelta(hours=_int("CHECKIN_MAX_OPERATION_AGE_HOURS", 72)),
            ),
        )
