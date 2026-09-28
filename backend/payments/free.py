"""Zero-amount checkout (e.g. free student pass)."""

from __future__ import annotations

import threading
from datetime import datetime, timezone

from payments import types as pt


class FreeProvider:
    """Confirms orders whose total is zero without an external payment step."""

    def __init__(self) -> None:
        """Initialize settled-result cache."""
        self._settled: dict[str, pt.Result] = {}
        self._mu = threading.Lock()

    def name(self) -> str:
        """Name on ``FreeProvider``."""
        return pt.PROVIDER_NAME_FREE

    def capabilities(self) -> pt.Capabilities:
        """Capabilities on ``FreeProvider``."""
        return pt.Capabilities(flow=pt.Flow.INLINE, webhooks=False)

    def begin(self, order: pt.Order) -> pt.Charge:
        """Begin on ``FreeProvider``."""
        ref = order.reference.strip()
        if not ref:
            raise ValueError("order id is required")
        if order.amount_minor != 0:
            raise ValueError("free provider only supports zero-amount orders")
        currency = order.currency.strip().upper()
        result = pt.Result(
            provider=self.name(),
            reference=ref,
            event_id=f"free-{ref}",
            status=pt.Status.PAID,
            amount_minor=0,
            currency=currency,
            paid_at=datetime.now(timezone.utc),
        )
        with self._mu:
            self._settled[ref] = result
        return pt.Charge(
            provider=self.name(),
            reference=ref,
            instructions="Gratuit : votre billet sera émis après confirmation.",
        )

    def verify(self, reference: str) -> pt.Result:
        """Verify on ``FreeProvider``."""
        reference = reference.strip()
        with self._mu:
            result = self._settled.get(reference)
        if result is None:
            raise ValueError(f"unknown reference {reference}")
        return result

    def webhook(self, body: bytes, headers: dict[str, str]) -> pt.Result:
        """Webhook on ``FreeProvider``."""
        raise ValueError("free provider does not accept webhooks")
