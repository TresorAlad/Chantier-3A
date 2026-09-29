"""Payment attempt and settlement records per order."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from store.store import NotFoundError, Store
from store.timeutil import text_to_null_time, text_to_time, time_to_text


@dataclass
class PaymentRecord:
    """Paymentrecord."""
    provider: str
    reference: str
    amount_minor: int
    currency: str
    status: str
    instructions: str
    marked_by: str
    marked_at: datetime | None
    created_at: datetime
    updated_at: datetime


def _scan(row) -> PaymentRecord:
    """Internal: scan."""
    if hasattr(row, "keys"):
        return PaymentRecord(
            provider=row["provider"],
            reference=row["reference"],
            amount_minor=int(row["amount_minor"]),
            currency=row["currency"],
            status=row["status"],
            instructions=row["instructions"] or "",
            marked_by=row["marked_by"] or "",
            marked_at=text_to_null_time(row["marked_at"]),
            created_at=text_to_time(row["created_at"]),
            updated_at=text_to_time(row["updated_at"]),
        )
    return PaymentRecord(
        provider=row[0],
        reference=row[1],
        amount_minor=int(row[2]),
        currency=row[3],
        status=row[4],
        instructions=row[5] or "",
        marked_by=row[6] or "",
        marked_at=text_to_null_time(row[7]),
        created_at=text_to_time(row[8]),
        updated_at=text_to_time(row[9]),
    )


def put_payment_record(st: Store, rec: PaymentRecord) -> None:
    """Put payment record."""
    if not rec.created_at:
        from datetime import timezone

        rec.created_at = datetime.now(timezone.utc)
    if not rec.updated_at:
        rec.updated_at = rec.created_at
    st.execute(
        """
        INSERT INTO payment_records
            (provider, reference, amount_minor, currency, status, instructions,
             marked_by, marked_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (provider, reference) DO UPDATE SET
            amount_minor = excluded.amount_minor,
            currency = excluded.currency,
            status = excluded.status,
            instructions = excluded.instructions,
            marked_by = excluded.marked_by,
            marked_at = excluded.marked_at,
            updated_at = excluded.updated_at
        """,
        (
            rec.provider,
            rec.reference,
            rec.amount_minor,
            rec.currency,
            rec.status,
            rec.instructions,
            rec.marked_by,
            time_to_text(rec.marked_at) if rec.marked_at else None,
            time_to_text(rec.created_at),
            time_to_text(rec.updated_at),
        ),
    )


def list_payment_records(st: Store, provider: str) -> list[PaymentRecord]:
    """List payment records."""
    rows = st.fetchall(
        """
        SELECT provider, reference, amount_minor, currency, status, instructions,
               marked_by, marked_at, created_at, updated_at
        FROM payment_records WHERE provider = ?
        """,
        (provider,),
    )
    return [_scan(r) for r in rows]


def get_payment_record(st: Store, provider: str, reference: str) -> PaymentRecord:
    """Get payment record."""
    row = st.fetchone(
        """
        SELECT provider, reference, amount_minor, currency, status, instructions,
               marked_by, marked_at, created_at, updated_at
        FROM payment_records WHERE provider = ? AND reference = ?
        """,
        (provider, reference),
    )
    if row is None:
        raise NotFoundError()
    return _scan(row)
