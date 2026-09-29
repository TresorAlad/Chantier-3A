"""Payout requests and settlement state for organizations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from store.store import Store
from store.timeutil import text_to_time, time_to_text


@dataclass
class Payout:
    """Payout."""
    id: str
    event_id: str
    amount_minor: int
    currency: str
    status: str
    created_at: datetime


def list_payouts_for_event(st: Store, event_id: str) -> list[Payout]:
    """List payouts for event."""
    rows = st.fetchall(
        """
        SELECT id, event_id, amount_minor, currency, status, created_at
        FROM payouts WHERE event_id = ?
        ORDER BY created_at DESC, id DESC
        """,
        (event_id,),
    )
    out: list[Payout] = []
    for r in rows:
        if hasattr(r, "keys"):
            out.append(
                Payout(
                    id=r["id"],
                    event_id=r["event_id"],
                    amount_minor=int(r["amount_minor"]),
                    currency=r["currency"],
                    status=r["status"],
                    created_at=text_to_time(r["created_at"]),
                )
            )
        else:
            out.append(
                Payout(
                    id=r[0],
                    event_id=r[1],
                    amount_minor=int(r[2]),
                    currency=r[3],
                    status=r[4],
                    created_at=text_to_time(r[5]),
                )
            )
    return out
