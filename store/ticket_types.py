"""Ticket product definitions, inventory, and sales windows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from store.store import NotFoundError, Store
from store.timeutil import text_to_null_time, text_to_time

PRODUCT_KIND_TICKET = "ticket"


@dataclass
class TicketType:
    """Tickettype."""
    id: str
    event_id: str
    name: str
    description: str
    price_minor: int
    quantity_total: int
    quantity_sold: int
    sales_start: datetime | None
    sales_end: datetime | None
    max_per_order: int
    status: str
    sort_order: int
    product_kind: str


def get_ticket_type_by_id(st: Store, ticket_type_id: str) -> TicketType:
    """Get ticket type by id."""
    row = st.fetchone(
        """
        SELECT id, event_id, name, description, price_minor, quantity_total,
               quantity_sold, sales_start, sales_end, max_per_order, status,
               sort_order, product_kind
        FROM ticket_types WHERE id = ?
        """,
        (ticket_type_id,),
    )
    if row is None:
        raise NotFoundError()
    if hasattr(row, "keys"):
        return TicketType(
            id=row["id"],
            event_id=row["event_id"],
            name=row["name"],
            description=row["description"] or "",
            price_minor=int(row["price_minor"]),
            quantity_total=int(row["quantity_total"]),
            quantity_sold=int(row["quantity_sold"]),
            sales_start=text_to_null_time(row["sales_start"]),
            sales_end=text_to_null_time(row["sales_end"]),
            max_per_order=int(row["max_per_order"]),
            status=row["status"],
            sort_order=int(row["sort_order"]),
            product_kind=row["product_kind"] or PRODUCT_KIND_TICKET,
        )
    return TicketType(
        id=row[0],
        event_id=row[1],
        name=row[2],
        description=row[3] or "",
        price_minor=int(row[4]),
        quantity_total=int(row[5]),
        quantity_sold=int(row[6]),
        sales_start=text_to_null_time(row[7]),
        sales_end=text_to_null_time(row[8]),
        max_per_order=int(row[9]),
        status=row[10],
        sort_order=int(row[11]),
        product_kind=row[12] or PRODUCT_KIND_TICKET,
    )


def _row_ticket_type(row) -> TicketType:
    """Internal: row ticket type."""
    if hasattr(row, "keys"):
        return TicketType(
            id=row["id"],
            event_id=row["event_id"],
            name=row["name"],
            description=row["description"] or "",
            price_minor=int(row["price_minor"]),
            quantity_total=int(row["quantity_total"]),
            quantity_sold=int(row["quantity_sold"]),
            sales_start=text_to_null_time(row["sales_start"]),
            sales_end=text_to_null_time(row["sales_end"]),
            max_per_order=int(row["max_per_order"]),
            status=row["status"],
            sort_order=int(row["sort_order"]),
            product_kind=row["product_kind"] or PRODUCT_KIND_TICKET,
        )
    return TicketType(
        id=row[0],
        event_id=row[1],
        name=row[2],
        description=row[3] or "",
        price_minor=int(row[4]),
        quantity_total=int(row[5]),
        quantity_sold=int(row[6]),
        sales_start=text_to_null_time(row[7]),
        sales_end=text_to_null_time(row[8]),
        max_per_order=int(row[9]),
        status=row[10],
        sort_order=int(row[11]),
        product_kind=row[12] or PRODUCT_KIND_TICKET,
    )


def list_ticket_types_for_event(st: Store, event_id: str) -> list[TicketType]:
    """List ticket types for event."""
    rows = st.fetchall(
        """
        SELECT id, event_id, name, description, price_minor, quantity_total,
               quantity_sold, sales_start, sales_end, max_per_order, status,
               sort_order, product_kind
        FROM ticket_types WHERE event_id = ?
        ORDER BY sort_order ASC, id ASC
        """,
        (event_id,),
    )
    return [_row_ticket_type(r) for r in rows]


def create_ticket_type(st: Store, tt: TicketType) -> None:
    """Create ticket type."""
    from store.timeutil import time_to_text

    st.execute(
        """
        INSERT INTO ticket_types (
            id, event_id, name, description, price_minor, quantity_total, quantity_sold,
            sales_start, sales_end, max_per_order, status, sort_order, product_kind
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tt.id,
            tt.event_id,
            tt.name,
            tt.description,
            tt.price_minor,
            tt.quantity_total,
            tt.quantity_sold,
            time_to_text(tt.sales_start) if tt.sales_start else None,
            time_to_text(tt.sales_end) if tt.sales_end else None,
            tt.max_per_order,
            tt.status,
            tt.sort_order,
            tt.product_kind,
        ),
    )


def update_ticket_type(st: Store, tt: TicketType) -> None:
    """Update ticket type."""
    from store.timeutil import time_to_text

    n = st.execute_rowcount(
        """
        UPDATE ticket_types SET
            name = ?, description = ?, price_minor = ?, quantity_total = ?,
            sales_start = ?, sales_end = ?, max_per_order = ?, status = ?,
            sort_order = ?, product_kind = ?
        WHERE id = ?
        """,
        (
            tt.name,
            tt.description,
            tt.price_minor,
            tt.quantity_total,
            time_to_text(tt.sales_start) if tt.sales_start else None,
            time_to_text(tt.sales_end) if tt.sales_end else None,
            tt.max_per_order,
            tt.status,
            tt.sort_order,
            tt.product_kind,
            tt.id,
        ),
    )
    if n == 0:
        raise NotFoundError()


def delete_ticket_type(st: Store, ticket_type_id: str) -> None:
    """Delete ticket type."""
    n = st.execute_rowcount("DELETE FROM ticket_types WHERE id = ?", (ticket_type_id,))
    if n == 0:
        raise NotFoundError()
