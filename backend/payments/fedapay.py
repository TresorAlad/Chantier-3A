"""FedaPay provider: server-created transactions paid through Checkout.js in the browser."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from payments import types as pt

PROVIDER_NAME_FEDAPAY = "fedapay"

_BASE_URLS = {
    "sandbox": "https://sandbox-api.fedapay.com/v1",
    "live": "https://api.fedapay.com/v1",
}
_WEBHOOK_TOLERANCE_SECONDS = 300
_EVENT_APPROVED = "transaction.approved"
_PAID_STATUSES = {"approved", "transferred"}
_PENDING_STATUSES = {"pending"}


class FedapayProvider:
    """Creates the transaction server-side so the amount can never be chosen by the buyer.

    The browser only receives the transaction id (``Charge.client_token``) and opens the
    Checkout.js widget on it. Settlement is always confirmed against the FedaPay API with the
    secret key, never from a client callback or from webhook payload fields.
    """

    def __init__(
        self,
        *,
        secret_key: str,
        webhook_secret: str = "",
        environment: str = "sandbox",
        timeout: float = 30.0,
        default_callback_url: str = "",
        client: httpx.Client | None = None,
    ) -> None:
        """Initialize ``FedapayProvider``."""
        self._secret_key = secret_key
        self._webhook_secret = webhook_secret
        self._base = _BASE_URLS.get(environment, _BASE_URLS["sandbox"])
        self._timeout = timeout
        self._default_callback_url = default_callback_url
        self._client = client
        self._currency_iso_by_id: dict[str, str] = {}

    def name(self) -> str:
        """Registered provider id stored on orders and used as the webhook path segment."""
        return PROVIDER_NAME_FEDAPAY

    def capabilities(self) -> pt.Capabilities:
        """Inline widget checkout, XOF only, asynchronous webhook confirmation."""
        return pt.Capabilities(currencies=["XOF"], flow=pt.Flow.INLINE, webhooks=True)

    def begin(self, order: pt.Order) -> pt.Charge:
        """Create the FedaPay transaction and hand its id to the browser widget."""
        if not self.capabilities().supports_currency(order.currency):
            raise ValueError(f"fedapay: unsupported currency {order.currency}")
        first, _, last = order.buyer_name.strip().partition(" ")
        payload: dict = {
            "description": f"Commande {order.reference}",
            "amount": order.amount_minor,
            "currency": {"iso": order.currency.upper()},
            "merchant_reference": order.reference,
            "customer": {
                "email": order.buyer_email,
                "firstname": first,
                "lastname": last.strip(),
            },
            "custom_metadata": {"order_id": order.reference, "event_id": order.event_id},
        }
        callback = order.callback_url or self._default_callback_url
        if callback:
            payload["callback_url"] = callback
        resp = self._request("POST", "/transactions", json=payload)
        resp.raise_for_status()
        txn = _unwrap(resp.json())
        txn_id = txn.get("id")
        if txn_id in (None, ""):
            raise ValueError("fedapay: transaction id missing in response")
        return pt.Charge(provider=self.name(), reference=order.reference, client_token=str(txn_id))

    def verify(self, reference: str) -> pt.Result:
        """Fetch the transaction by merchant reference (our order id)."""
        resp = self._request("GET", f"/transactions/merchant/{quote(reference, safe='')}")
        resp.raise_for_status()
        return self._to_result(_unwrap(resp.json()))

    def webhook(self, body: bytes, headers: dict[str, str]) -> pt.Result:
        """Authenticate the webhook, then re-read the transaction from the API."""
        lowered = {k.lower(): v for k, v in headers.items()}
        if not self._verify_signature(body, lowered.get("x-fedapay-signature", "")):
            raise ValueError("invalid webhook signature")
        event = json.loads(body.decode())
        if event.get("name") != _EVENT_APPROVED:
            raise pt.ErrUnhandledEvent
        entity = event.get("entity") if isinstance(event.get("entity"), dict) else {}
        if txn_id := entity.get("id"):
            resp = self._request("GET", f"/transactions/{quote(str(txn_id), safe='')}")
        elif ref := entity.get("merchant_reference"):
            resp = self._request("GET", f"/transactions/merchant/{quote(str(ref), safe='')}")
        else:
            raise ValueError("webhook without transaction identifier")
        resp.raise_for_status()
        result = self._to_result(_unwrap(resp.json()))
        result.event_id = f"{_EVENT_APPROVED}:{result.event_id}"
        return result

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Authenticated request against the FedaPay API."""
        headers = {"Authorization": f"Bearer {self._secret_key}", "Content-Type": "application/json"}
        if self._client is not None:
            return self._client.request(method, path, headers=headers, **kwargs)
        with httpx.Client(base_url=self._base, timeout=self._timeout) as client:
            return client.request(method, path, headers=headers, **kwargs)

    def _verify_signature(self, body: bytes, header: str) -> bool:
        """Check ``t=<ts>,s=<hmac>`` where hmac = HMAC-SHA256(secret, "<ts>.<raw body>")."""
        if not self._webhook_secret or not header:
            return False
        timestamp = ""
        signatures: list[str] = []
        for part in header.split(","):
            key, _, value = part.strip().partition("=")
            if key == "t":
                timestamp = value
            elif key == "s":
                signatures.append(value)
        if not timestamp.isdigit() or not signatures:
            return False
        if abs(time.time() - int(timestamp)) > _WEBHOOK_TOLERANCE_SECONDS:
            return False
        expected = hmac.new(
            self._webhook_secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        return any(hmac.compare_digest(expected, s) for s in signatures)

    def _to_result(self, txn: dict) -> pt.Result:
        """Map a FedaPay transaction into a normalized ``Result`` (fail closed on gaps)."""
        status_raw = str(txn.get("status", "")).lower()
        if status_raw in _PAID_STATUSES:
            status = pt.Status.PAID
        elif status_raw in _PENDING_STATUSES:
            status = pt.Status.PENDING
        else:
            status = pt.Status.FAILED
        iso = self._currency_iso(txn)
        return pt.Result(
            provider=self.name(),
            reference=str(txn.get("merchant_reference") or ""),
            event_id=str(txn.get("id", "")),
            status=status,
            amount_minor=int(txn.get("amount") or 0),
            currency=iso.upper(),
            paid_at=_parse_time(txn.get("approved_at")),
            raw=txn,
        )


    def _currency_iso(self, txn: dict) -> str:
        """ISO code of the transaction currency; empty (so reconcile fails) when unknown.

        The API returns ``currency_id`` (not an object), so ids are resolved through
        ``GET /currencies`` once and cached.
        """
        currency = txn.get("currency")
        if isinstance(currency, dict) and currency.get("iso"):
            return str(currency["iso"]).upper()
        if isinstance(currency, str) and currency:
            return currency.upper()
        currency_id = txn.get("currency_id")
        if currency_id in (None, ""):
            return ""
        if str(currency_id) not in self._currency_iso_by_id:
            resp = self._request("GET", "/currencies")
            resp.raise_for_status()
            data = resp.json()
            items = data.get("v1/currencies") or data.get("currencies") or []
            self._currency_iso_by_id = {
                str(c["id"]): str(c["iso"]).upper() for c in items if c.get("id") and c.get("iso")
            }
        return self._currency_iso_by_id.get(str(currency_id), "")


def _unwrap(data: dict) -> dict:
    """FedaPay wraps single resources as ``{"v1/transaction": {...}}``; accept flat payloads too."""
    for key in ("v1/transaction", "transaction"):
        if isinstance(data.get(key), dict):
            return data[key]
    return data


def _parse_time(raw: object) -> datetime | None:
    """Parse an ISO timestamp to aware UTC, or None."""
    if not raw or not isinstance(raw, str):
        return None
    text = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
