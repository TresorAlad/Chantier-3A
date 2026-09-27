"""Formulaire de contact public (visiteurs Tdev Festival)."""

from __future__ import annotations

import re
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from http_layer.deps import AppState, get_app_state
from http_layer.errors import json_error
from notify.contact_mail import send_contact_message

router = APIRouter(tags=["contact"])

_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=10, max_length=5000)


@router.post("/public/contact")
def submit_contact(body: ContactIn, state: AppState = Depends(get_app_state)) -> dict:
    """Accept a visitor message and forward it to the T-Dev inbox when SMTP is configured."""
    email = body.email.strip()
    if not _EMAIL.match(email):
        return json_error(400, "invalid_request", "Adresse e-mail invalide.")

    cfg = state.config
    if not cfg.smtp_host or not cfg.smtp_from:
        return json_error(
            503,
            "unavailable",
            "L'envoi par formulaire n'est pas disponible pour le moment. Réessayez plus tard.",
        )

    try:
        send_contact_message(
            cfg,
            name=body.name.strip(),
            email=email,
            subject=body.subject.strip(),
            message=body.message.strip(),
        )
    except RuntimeError as err:
        if str(err) == "smtp_not_configured":
            return json_error(503, "unavailable", "Service de messagerie non configuré.")
        if str(err) == "contact_inbox_missing":
            return json_error(503, "unavailable", "Boîte de contact non configurée.")
        return json_error(500, "internal_error", "Impossible d'envoyer le message.")
    except Exception:
        return json_error(500, "internal_error", "Impossible d'envoyer le message.")

    return {"ok": True}
