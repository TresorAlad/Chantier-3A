"""Manual/offline payment provider for bank transfer instructions."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from payments import types as pt
from store import payment_records as payment_records_repo
from store.store import Store


ErrManualNoWebhook = Exception("payments: manual: does not support webhooks")


class ManualProvider:
    """Manualprovider."""
    def __init__(
        self,
        store: Store | None = None,
        instructions_fn: Callable[[pt.Order], str] | None = None,
    ) -> None:
        """Initialize ``ManualProvider``."""
        self._store = store
        self._instructions = instructions_fn or _default_instructions
        self._records: dict[str, _Rec] = {}
        self._mu = threading.Lock()
        if store:
            self._warm_load()

    def _warm_load(self) -> None:
        """Warm load on ``ManualProvider``."""
        rows = payment_records_repo.list_payment_records(self._store, pt.PROVIDER_NAME_MANUAL)
        for r in rows:
            self._records[r.reference] = _Rec(
                reference=r.reference,
                amount_minor=r.amount_minor,
                currency=r.currency,
                status=pt.Status(r.status),
                instructions=r.instructions,
                marked_by=r.marked_by,
                marked_at=r.marked_at,
                created_at=r.created_at,
            )

    def name(self) -> str:
        """Name on ``ManualProvider``."""
        return pt.PROVIDER_NAME_MANUAL

    def capabilities(self) -> pt.Capabilities:
        """Capabilities on ``ManualProvider``."""
        return pt.Capabilities(flow=pt.Flow.MANUAL, webhooks=False)

    def begin(self, order: pt.Order) -> pt.Charge:
        """Begin on ``ManualProvider``."""
        ref = order.reference.strip()
        if not ref:
            raise ValueError("order id is required")
        if order.amount_minor <= 0:
            raise ValueError("amount must be positive")
        currency = order.currency.strip().upper()
        with self._mu:
            if existing := self._records.get(ref):
                return pt.Charge(
                    provider=self.name(),
                    reference=existing.reference,
                    instructions=existing.instructions,
                )
            text = self._instructions(order)
            rec = _Rec(
                reference=ref,
                amount_minor=order.amount_minor,
                currency=currency,
                status=pt.Status.PENDING,
                instructions=text,
                created_at=datetime.now(timezone.utc),
            )
            self._persist_locked(rec)
            self._records[ref] = rec
            return pt.Charge(provider=self.name(), reference=ref, instructions=text)

    def mark_paid(self, reference: str, marked_by: str) -> pt.Result:
        """Mark paid on ``ManualProvider``."""
        return self._mark(reference, marked_by, pt.Status.PAID)

    def mark_failed(self, reference: str, marked_by: str) -> pt.Result:
        """Mark failed on ``ManualProvider``."""
        return self._mark(reference, marked_by, pt.Status.FAILED)

    def _mark(self, reference: str, marked_by: str, status: pt.Status) -> pt.Result:
        """Mark on ``ManualProvider``."""
        reference = reference.strip()
        marked_by = marked_by.strip()
        if not reference or not marked_by:
            raise ValueError("reference and marked_by required")
        with self._mu:
            rec = self._records.get(reference)
            if rec is None:
                raise ValueError(f"unknown reference {reference}")
            if status == pt.Status.PAID and rec.status == pt.Status.PAID:
                return self._result_locked(rec)
            rec.status = status
            rec.marked_by = marked_by
            rec.marked_at = datetime.now(timezone.utc)
            self._persist_locked(rec)
            return self._result_locked(rec)

    def verify(self, reference: str) -> pt.Result:
        """Verify on ``ManualProvider``."""
        reference = reference.strip()
        with self._mu:
            rec = self._records.get(reference)
            if rec is None:
                raise ValueError(f"unknown reference {reference}")
            return self._result_locked(rec)

    def webhook(self, body: bytes, headers: dict[str, str]) -> pt.Result:
        """Webhook on ``ManualProvider``."""
        raise ErrManualNoWebhook

    def record(self, reference: str) -> tuple[dict, bool]:
        """Record on ``ManualProvider``."""
        with self._mu:
            rec = self._records.get(reference.strip())
            if rec is None:
                return {}, False
            return {
                "reference": rec.reference,
                "marked_by": rec.marked_by,
                "marked_at": rec.marked_at,
            }, True

    def _persist_locked(self, rec: "_Rec") -> None:
        """Persist locked on ``ManualProvider``."""
        if self._store is None:
            return
        updated = rec.marked_at or rec.created_at
        payment_records_repo.put_payment_record(
            self._store,
            payment_records_repo.PaymentRecord(
                provider=pt.PROVIDER_NAME_MANUAL,
                reference=rec.reference,
                amount_minor=rec.amount_minor,
                currency=rec.currency,
                status=rec.status.value,
                instructions=rec.instructions,
                marked_by=rec.marked_by,
                marked_at=rec.marked_at,
                created_at=rec.created_at,
                updated_at=updated,
            ),
        )

    def _result_locked(self, rec: "_Rec") -> pt.Result:
        """Result locked on ``ManualProvider``."""
        res = pt.Result(
            provider=self.name(),
            reference=rec.reference,
            status=rec.status,
            amount_minor=rec.amount_minor,
            currency=rec.currency,
        )
        if rec.status == pt.Status.PAID and rec.marked_at:
            res.paid_at = rec.marked_at
            res.event_id = f"manual-{rec.reference}-{rec.marked_at.timestamp():.0f}"
        return res


@dataclass
class _Rec:
    """Internal: Rec."""
    reference: str
    amount_minor: int
    currency: str
    status: pt.Status
    instructions: str
    created_at: datetime
    marked_by: str = ""
    marked_at: datetime | None = None


def _default_instructions(order: pt.Order) -> str:
    """Internal: default instructions."""
    from money import currency as money

    try:
        amount_text = money.format_minor_amount(order.amount_minor, order.currency)
    except money.CurrencyError:
        amount_text = f"{order.amount_minor} {order.currency}"
    return (
        f"Pay {amount_text}, quoting order reference {order.reference}. "
        "Ask the organiser to confirm and mark this order paid once they have received it."
    )
