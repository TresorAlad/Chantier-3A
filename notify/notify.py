"""Best-effort SMTP notifications after order payment (optional)."""

from __future__ import annotations

import logging
import smtplib
import threading
from email.message import EmailMessage

from config import Config
from store import events_repo, orders as orders_repo
from store.store import Store

log = logging.getLogger("chantier3a.notify")


class NotifyService:
    """Background SMTP queue: one confirmation e-mail per paid order when SMTP is configured."""

    def __init__(self, store: Store, config: Config) -> None:
        """Initialize ``NotifyService``."""
        self._store = store
        self._config = config
        self._sent_orders: set[str] = set()
        self._lock = threading.Lock()

    def on_order_paid(self, order_id: str) -> None:
        """On order paid on ``NotifyService``."""
        with self._lock:
            if order_id in self._sent_orders:
                return
            self._sent_orders.add(order_id)
        threading.Thread(target=self._send_confirmation, args=(order_id,), daemon=True).start()

    def _send_confirmation(self, order_id: str) -> None:
        """Send confirmation on ``NotifyService``."""
        try:
            ord_row = orders_repo.get_order_by_id(self._store, order_id)
            ev = events_repo.get_event_by_id(self._store, ord_row.event_id)
        except Exception as err:
            log.error("notify: load order/event: %s", err)
            return
        if not self._config.smtp_host or not self._config.smtp_from:
            log.info("notify: SMTP not configured; skipping e-mail for order %s", order_id)
            return
        base = self._config.base_url.rstrip("/")
        # Plain-text template; localize via config/i18n when product copy is finalized.
        body = (
            f"Hello {ord_row.buyer_name},\n\n"
            f'Your order for "{ev.title}" is confirmed (ref. {ord_row.id}).\n'
            f"Amount: {ord_row.total_minor} {ord_row.currency}\n\n"
            f"View your order: {base}/order/{ord_row.id}\n\n"
            "Thank you,\nThe ticketing team\n"
        )
        try:
            self._send_smtp(ord_row.buyer_email, f"Confirmation - {ev.title}", body)
        except Exception as err:
            log.error("notify: send failed order=%s err=%s", order_id, err)

    def _send_smtp(self, to: str, subject: str, body: str) -> None:
        """Send smtp on ``NotifyService``."""
        msg = EmailMessage()
        msg["From"] = self._config.smtp_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        addr = f"{self._config.smtp_host}:{self._config.smtp_port}"
        with smtplib.SMTP(self._config.smtp_host, self._config.smtp_port, timeout=30) as smtp:
            if self._config.smtp_user:
                smtp.starttls()
                smtp.login(self._config.smtp_user, self._config.smtp_password)
            smtp.send_message(msg)
        log.info("notify: sent confirmation to %s via %s", to, addr)
