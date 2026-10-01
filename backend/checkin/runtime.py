"""Per-process runtime of the check-in module: config, pool, adapters, clock, rate limiter."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from psycopg_pool import ConnectionPool

from checkin.adapters import CachedAuth, CachedKeySource, Ring3AKeySource, Sessions3AAuth
from checkin.config import CheckinConfig
from checkin.db import open_pool
from checkin.ports import Clock, KeySource, TerminalAuth, utc_now


class RateLimiter:
    """Sliding-window limiter keyed by terminal id (the 3A limiter only covers ``/api/scan*``)."""

    def __init__(self, max_requests: int, window_seconds: float = 60.0) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """Record a hit for ``key``; return ``False`` when over the limit."""
        if self._max <= 0:
            return True
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self._window:
                q.popleft()
            if len(q) >= self._max:
                return False
            q.append(now)
            return True


@dataclass
class Runtime:
    """Everything a request handler needs; built once per process."""

    cfg: CheckinConfig
    pool: ConnectionPool
    auth: TerminalAuth
    keys: KeySource
    clock: Clock = utc_now
    limiter: RateLimiter = field(init=False)

    def __post_init__(self) -> None:
        self.limiter = RateLimiter(self.cfg.rate_limit_per_terminal)

    def close(self) -> None:
        """Close the pool (application shutdown)."""
        self.pool.close()


def build_runtime(
    database_url: str = "",
    session_secret: str = "",
    cfg: CheckinConfig | None = None,
    config3a: Any = None,
    **overrides: Any,
) -> Runtime:
    """Build the default runtime (3A sessions + 3A key ring) from the environment."""
    cfg = cfg or CheckinConfig.from_env(database_url)
    auth = overrides.get("auth") or Sessions3AAuth(session_secret, config3a)
    if cfg.auth_cache_seconds > 0:
        auth = CachedAuth(auth, cfg.auth_cache_seconds)
    keys = overrides.get("keys") or Ring3AKeySource()
    if cfg.keys_ttl_seconds > 0:
        keys = CachedKeySource(keys, cfg.keys_ttl_seconds)
    return Runtime(
        cfg=cfg,
        pool=open_pool(cfg),
        auth=auth,
        keys=keys,
        clock=overrides.get("clock") or utc_now,
    )


_LOCK = threading.Lock()


def get_runtime(app) -> Runtime:
    """Return (lazily creating) the runtime attached to a FastAPI app.

    In the mounted mode the database URL and session secret come from the 3A ``Config``.
    """
    rt = getattr(app.state, "checkin", None)
    if rt is not None:
        return rt
    with _LOCK:
        rt = getattr(app.state, "checkin", None)
        if rt is None:
            cfg3a = getattr(app.state, "config", None)
            rt = build_runtime(
                database_url=getattr(cfg3a, "database_url", "") or "",
                session_secret=getattr(cfg3a, "session_secret", "") or "",
                config3a=cfg3a,
            )
            app.state.checkin = rt
    return rt
