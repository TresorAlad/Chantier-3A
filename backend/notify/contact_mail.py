"""Envoi SMTP d'un message du formulaire de contact public."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from config import Config

log = logging.getLogger("chantier3a.notify.contact")


def send_contact_message(
    config: Config,
    *,
    name: str,
    email: str,
    subject: str,
    message: str,
) -> None:
    """Deliver a contact form submission to the T-Dev inbox."""
    if not config.smtp_host or not config.smtp_from:
        raise RuntimeError("smtp_not_configured")
    to_addr = (config.contact_to or config.smtp_from).strip()
    if not to_addr:
        raise RuntimeError("contact_inbox_missing")

    safe_name = name.strip() or "Visiteur"
    safe_email = email.strip()
    safe_subject = subject.strip() or "Message depuis le site Tdev Festival"
    body = message.strip()

    mail_subject = f"[Contact T-Dev] {safe_subject}"
    plain = (
        f"Message reçu depuis festival.ourtdev.com\n\n"
        f"Nom : {safe_name}\n"
        f"E-mail : {safe_email}\n"
        f"Sujet : {safe_subject}\n\n"
        f"{body}\n"
    )
    html = f"""\
<p>Message reçu depuis le site Tdev Festival.</p>
<ul>
  <li><strong>Nom</strong> : {safe_name}</li>
  <li><strong>E-mail</strong> : {safe_email}</li>
  <li><strong>Sujet</strong> : {safe_subject}</li>
</ul>
<p style="white-space:pre-wrap;">{body}</p>
"""

    msg = EmailMessage()
    msg["From"] = config.smtp_from
    msg["To"] = to_addr
    msg["Subject"] = mail_subject
    msg["Reply-To"] = safe_email
    msg.set_content(plain)
    msg.add_alternative(html, subtype="html")

    with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=30) as smtp:
        if config.smtp_user:
            smtp.starttls()
            smtp.login(config.smtp_user, config.smtp_password)
        smtp.send_message(msg)
    log.info("contact: delivered inquiry from %s to %s", safe_email, to_addr)
