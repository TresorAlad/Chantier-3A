"""Atomic pass reference counter per calendar year."""

from __future__ import annotations

from store.rebind import rebind_query
from store.store import Store
from tickets.pass_ref import format_pass_ref


def next_pass_ref(st: Store, conn, year: int) -> str:
    """Allocate the next TDEV-YYYY-NNNN inside an open order settlement transaction."""
    q = rebind_query(
        """
        INSERT INTO pass_serial_counters (year, last_seq) VALUES (?, 1)
        ON CONFLICT (year) DO UPDATE
            SET last_seq = pass_serial_counters.last_seq + 1
        RETURNING last_seq
        """
    )
    row = conn.execute(q, (year,)).fetchone()
    seq = int(row[0] if not hasattr(row, "keys") else row["last_seq"])
    return format_pass_ref(year, seq)
