"""HTTP client for the external Chantier 3A payment microservice."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

import httpx

from payments import types as pt


class RemotePaymentProvider:
    """HTTP client for the external payment microservice (see docs/PAYMENT-SERVICE.md)."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        webhook_secret: str,
        provider_name: str,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        """Initialize ``RemotePaymentProvider``."""
        self._base = base_url.rstrip("/")
        self._api_key = api_key
        self._webhook_secret = webhook_secret
        self._name = provider_name.strip().lower() or "community-pay"
        self._timeout = timeout
        self._client = client

    def name(self) -> str:
        """Registered provider id sent to clients and stored on orders."""
        return self._name

    def capabilities(self) -> pt.Capabilities:
        """Redirect checkout with asynchronous webhook settlement."""
        return pt.Capabilities(flow=pt.Flow.REDIRECT, webhooks=True)

    def _headers(self) -> dict[str, str]:
        """JSON request headers including optional bearer API key."""
        h = {"Content-Type": "application/json"}
        if self._api_key:
            h["Authorization"] = f"Bearer {self._api_key}"
        return h

    def begin(self, order: pt.Order) -> pt.Charge:
        """Create a charge at the payment service and return redirect URL or instructions."""
        payload = {
            "order_id": order.reference,
            "amount_minor": order.amount_minor,
            "currency": order.currency,
            "buyer_email": order.buyer_email,
            "buyer_name": order.buyer_name,
            "success_url": order.callback_url,
            "cancel_url": order.callback_url,
            "metadata": {"event_id": order.event_id, **order.metadata},
        }
        resp = self._post("/v1/charges", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return pt.Charge(
            provider=self.name(),
            reference=data.get("reference", order.reference),
            redirect_url=data.get("redirect_url", ""),
            instructions=data.get("instructions", ""),
        )

    def verify(self, reference: str) -> pt.Result:
        """Poll charge status by provider reference."""
        resp = self._get(f"/v1/charges/{reference}")
        resp.raise_for_status()
        return self._parse_result(resp.json())

    def _post(self, path: str, **kwargs):
        """Post on ``RemotePaymentProvider``."""
        if self._client is not None:
            return self._client.post(path, headers=self._headers(), **kwargs)
        with httpx.Client(base_url=self._base, timeout=self._timeout) as client:
            return client.post(path, headers=self._headers(), **kwargs)

    def _get(self, path: str):
        """Get on ``RemotePaymentProvider``."""
        if self._client is not None:
            return self._client.get(path, headers=self._headers())
        with httpx.Client(base_url=self._base, timeout=self._timeout) as client:
            return client.get(path, headers=self._headers())

    def webhook(self, body: bytes, headers: dict[str, str]) -> pt.Result:
        """Parse and authenticate a payment service webhook payload."""
        sig = headers.get("x-chantier3a-payment-signature", headers.get("X-Chantier3A-Payment-Signature", ""))
        if not self._verify_signature(body, sig):
            raise ValueError("invalid webhook signature")
        data = json.loads(body.decode())
        return self._parse_result(data)

    def _verify_signature(self, body: bytes, header: str) -> bool:
        """Constant-time HMAC-SHA256 check of the raw webhook body."""
        if not self._webhook_secret:
            return False
        expected = "sha256=" + hmac.new(
            self._webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, header.strip())

    def _parse_result(self, data: dict) -> pt.Result:
        """Map payment service JSON into a normalized ``Result``."""
        status_raw = str(data.get("status", "pending")).lower()
        try:
            status = pt.Status(status_raw)
        except ValueError as err:
            raise ValueError(f"unknown status {status_raw}") from err
        paid_at = None
        if raw_paid := data.get("paid_at"):
            if raw_paid.endswith("Z"):
                raw_paid = raw_paid[:-1] + "+00:00"
            paid_at = datetime.fromisoformat(raw_paid).astimezone(timezone.utc)
        return pt.Result(
            provider=self.name(),
            reference=str(data.get("reference", "")),
            event_id=str(data.get("event_id", "")),
            status=status,
            amount_minor=int(data.get("amount_minor", 0)),
            currency=str(data.get("currency", "")).upper(),
            paid_at=paid_at,
            raw=data,
        )
