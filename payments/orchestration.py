"""Coordinate charge begin, verify, and webhook handling across providers."""

from __future__ import annotations

from typing import Protocol

from payments import types as pt


class SeenStore(Protocol):
    """Dedupe paid webhook notifications by provider and provider event id."""

    def mark_seen(self, provider: str, event_id: str) -> bool: ...


class OrderLookup(Protocol):
    """Resolve expected order amount and currency for payment reconciliation."""

    def lookup(self, reference: str) -> pt.OrderRef: ...


def handle_verify(provider: pt.Provider, reference: str, lookup: OrderLookup | None) -> pt.Result:
    """Poll provider status and optionally reconcile against the local order."""
    result = provider.verify(reference)
    if lookup is not None:
        want = lookup.lookup(result.reference)
        pt.reconcile(result, want)
    return result


def handle_webhook(
    provider: pt.Provider,
    body: bytes,
    headers: dict[str, str],
    seen: SeenStore | None,
    lookup: OrderLookup | None,
) -> pt.Result:
    """Verify webhook signature, reject replays, and reconcile with the local order."""
    result = provider.webhook(body, headers)
    _check_replay(seen, provider.name(), result)
    if lookup is not None:
        want = lookup.lookup(result.reference)
        pt.reconcile(result, want)
    return result


def _check_replay(seen: SeenStore | None, provider: str, result: pt.Result) -> None:
    """Reject duplicate paid webhooks sharing the same provider event id."""
    if seen is None or result.status != pt.Status.PAID:
        return
    if not (result.event_id or "").strip():
        raise ValueError("paid webhook without event_id")
    # mark_seen returns False when this paid event was already processed.
    if not seen.mark_seen(provider, result.event_id):
        raise pt.ErrReplayed
