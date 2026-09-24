"""Wire payment providers, orders, notifications, and key vault at startup."""

from __future__ import annotations

import os
from dataclasses import dataclass

from config import Config
from notify.notify import NotifyService
from orders.service import OrdersService
from payments.manual import ManualProvider
from payments.registry import Registry
from payments.remote import RemotePaymentProvider
from payments.stub import StubProvider
from store import keyvault_crypto as kv
from store import keyvault_db
from store.store import Store


@dataclass
class AppServices:
    """Shared singletons attached to the FastAPI app state."""
    payments: Registry
    orders: OrdersService
    notify: NotifyService
    webhook_seen: _MemorySeenStore


class _MemorySeenStore:
    """In-process webhook idempotency cache (single-node deployments)."""

    def __init__(self) -> None:
        """Initialize an empty seen-event set."""
        self._seen: set[str] = set()

    def mark_seen(self, provider: str, event_id: str) -> bool:
        """Record a provider event id; return False if it was already seen."""
        key = f"{provider}:{event_id}"
        if key in self._seen:
            return False
        self._seen.add(key)
        return True


def unlock_store_vault(store: Store, config: Config) -> None:
    """Unlock the org key vault using demo, passphrase, or leave locked."""
    if config.demo:
        keyvault_db.unlock_key_vault(store, kv.Source.demo(), demo=True)
        return
    if config.key_passphrase:
        keyvault_db.unlock_key_vault(store, kv.Source.passphrase(config.key_passphrase))
        return


def build_payment_registry(store: Store, config: Config) -> Registry:
    """Register manual, demo stub, and remote payment providers from config."""
    reg = Registry.from_env(os.environ.get("CACKLE_PAYMENT_PROVIDERS", ""))
    manual = ManualProvider(store=store)
    reg.register(manual)
    if config.demo:
        reg.register(StubProvider(opt_in=True))
    if config.payment_service_url:
        reg.register(
            RemotePaymentProvider(
                base_url=config.payment_service_url,
                api_key=config.payment_service_api_key,
                webhook_secret=config.payment_webhook_secret,
                provider_name=config.payment_provider_name,
                timeout=float(config.payment_service_timeout),
            )
        )
    return reg


def build_services(store: Store, config: Config) -> AppServices:
    """Construct payment registry, orders, notify, and webhook deduplication services."""
    unlock_store_vault(store, config)
    payments = build_payment_registry(store, config)
    notify = NotifyService(store, config)
    orders = OrdersService(store, payments, notify=notify)
    return AppServices(payments=payments, orders=orders, notify=notify, webhook_seen=_MemorySeenStore())
