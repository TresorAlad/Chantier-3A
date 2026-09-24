"""Demo stub provider that auto-succeeds charges in demo mode."""

from __future__ import annotations

import threading
from datetime import datetime, timezone

from payments import types as pt


class StubProvider:
    """Stubprovider."""
    def __init__(self, opt_in: bool) -> None:
        """Initialize ``StubProvider``."""
        if not opt_in:
            raise ValueError("stub requires explicit opt-in")
        self._settled: dict[str, pt.Result] = {}
        self._mu = threading.Lock()

    def name(self) -> str:
        """Name on ``StubProvider``."""
        return pt.PROVIDER_NAME_STUB

    def capabilities(self) -> pt.Capabilities:
        """Capabilities on ``StubProvider``."""
        return pt.Capabilities(flow=pt.Flow.INLINE, webhooks=False)

    def begin(self, order: pt.Order) -> pt.Charge:
        """Begin on ``StubProvider``."""
        ref = order.reference.strip()
        if not ref:
            raise ValueError("order id required")
        currency = order.currency.strip().upper()
        result = pt.Result(
            provider=self.name(),
            reference=ref,
            event_id=f"stub-{ref}",
            status=pt.Status.PAID,
            amount_minor=order.amount_minor,
            currency=currency,
            paid_at=datetime.now(timezone.utc),
        )
        with self._mu:
            self._settled[ref] = result
        return pt.Charge(
            provider=self.name(),
            reference=ref,
            instructions="Demo mode: this order auto-settles instantly. No real payment was taken.",
        )

    def verify(self, reference: str) -> pt.Result:
        """Verify on ``StubProvider``."""
        reference = reference.strip()
        with self._mu:
            result = self._settled.get(reference)
        if result is None:
            raise ValueError(f"unknown reference {reference}")
        return result

    def webhook(self, body: bytes, headers: dict[str, str]) -> pt.Result:
        """Webhook on ``StubProvider``."""
        raise ValueError("stub does not accept webhooks")
