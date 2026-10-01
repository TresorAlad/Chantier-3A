"""Dedicated PostgreSQL connection pool for the check-in module.

Separate from the single shared connection of the 3A ``Store`` (store/store.py), so a failed
statement here can never poison, nor be poisoned by, the rest of the 3A application.
"""

from __future__ import annotations

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from checkin.config import CheckinConfig


def open_pool(cfg: CheckinConfig) -> ConnectionPool:
    """Open a pool of dict-row connections; one pool per process."""
    if not cfg.database_url:
        raise RuntimeError("CHECKIN_DATABASE_URL or CHANTIER3A_DATABASE_URL is required")
    pool = ConnectionPool(
        cfg.database_url,
        min_size=cfg.pool_min,
        max_size=cfg.pool_max,
        kwargs={"row_factory": dict_row},
        open=False,
        name="checkin",
    )
    pool.open(wait=True, timeout=10)
    return pool
