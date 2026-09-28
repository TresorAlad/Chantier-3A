"""Unique public pass reference TDEV-YYYY-NNNN (suffixe aleatoire)."""

from __future__ import annotations

from store.rebind import rebind_query
from store.store import Store
from tickets.pass_ref import format_pass_ref, random_pass_suffix

_MAX_ATTEMPTS = 128


def next_pass_ref(st: Store, conn, year: int) -> str:
    """Allocate a unique TDEV-YYYY-NNNN inside an open order settlement transaction."""
    del st  # kept for API compatibility with callers
    exists_q = rebind_query("SELECT 1 FROM tickets WHERE serial = ? LIMIT 1")
    for _ in range(_MAX_ATTEMPTS):
        ref = format_pass_ref(year, random_pass_suffix())
        row = conn.execute(exists_q, (ref,)).fetchone()
        if row is None:
            return ref
    raise RuntimeError("could not allocate a unique pass reference")

