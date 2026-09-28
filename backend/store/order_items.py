"""Line items on orders (ticket types and quantities)."""

from __future__ import annotations

from dataclasses import dataclass

from store.store import NotFoundError, Store
from store.timeutil import text_to_time


@dataclass
class OrderItem:
    """Orderitem."""
    id: str
    order_id: str
    ticket_type_id: str
    quantity: int
    unit_price_minor: int


def list_order_items_for_order(st: Store, order_id: str) -> list[OrderItem]:
    """List order items for order."""
    rows = st.fetchall(
        """
        SELECT id, order_id, ticket_type_id, quantity, unit_price_minor
        FROM order_items WHERE order_id = ? ORDER BY id ASC
        """,
        (order_id,),
    )
    out: list[OrderItem] = []
    for row in rows:
        if hasattr(row, "keys"):
            out.append(
                OrderItem(
                    id=row["id"],
                    order_id=row["order_id"],
                    ticket_type_id=row["ticket_type_id"],
                    quantity=int(row["quantity"]),
                    unit_price_minor=int(row["unit_price_minor"]),
                )
            )
        else:
            out.append(
                OrderItem(
                    id=row[0],
                    order_id=row[1],
                    ticket_type_id=row[2],
                    quantity=int(row[3]),
                    unit_price_minor=int(row[4]),
                )
            )
    return out
