"""Record ticket scans and admission decisions at the door."""

from __future__ import annotations

from datetime import datetime

from store.store import Store, new_ulid
from store.timeutil import time_to_text


def list_admitted_ticket_ids(st: Store, event_id: str) -> list[str]:
    """List admitted ticket ids."""
    rows = st.fetchall(
        """
        SELECT ticket_id FROM admissions
        WHERE event_id = ? AND result = 'admitted'
        ORDER BY ticket_id ASC
        """,
        (event_id,),
    )
    out: list[str] = []
    for row in rows:
        out.append(row["ticket_id"] if hasattr(row, "keys") else row[0])
    return out


def try_insert_admitted(
    st: Store,
    *,
    ticket_id: str,
    event_id: str,
    gate_id: str,
    device_id: str,
    scanned_by: str | None,
    scanned_at: datetime,
) -> bool:
    """Try insert admitted."""
    try:
        st.execute(
            """
            INSERT INTO admissions (id, ticket_id, event_id, gate_id, scanned_by, device_id,
                scanned_at, result, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'admitted', '')
            """,
            (
                new_ulid(),
                ticket_id,
                event_id,
                gate_id,
                scanned_by,
                device_id,
                time_to_text(scanned_at),
            ),
        )
        return True
    except Exception as err:
        msg = str(err).lower()
        if "unique" in msg or "duplicate" in msg:
            return False
        raise
