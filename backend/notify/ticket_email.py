"""Modèle d'e-mail de confirmation billet (texte + HTML, PDF en pièce jointe)."""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Literal

TicketEmailVariant = Literal["festival", "nexus"]

DEFAULT_GOODIES_SHOP_URL = "https://shop.tdevfestival.com"


@dataclass(frozen=True)
class TicketEmailLine:
    """Une ligne pass dans le corps du message."""

    pass_label: str
    holder_name: str
    serial: str


@dataclass(frozen=True)
class TicketEmailContext:
    """Données visiteur pour le mail de billet."""

    buyer_name: str
    event_title: str
    when_label: str | None
    venue_line: str
    billet_url: str
    tickets: tuple[TicketEmailLine, ...]
    contact_url: str | None = None
    variant: TicketEmailVariant = "festival"
    goodies_shop_url: str = DEFAULT_GOODIES_SHOP_URL


def _esc(text: str) -> str:
    return html.escape(text.strip(), quote=True)


def _greeting_name(ctx: TicketEmailContext) -> str:
    name = ctx.buyer_name.strip()
    if not name:
        return "Bonjour,"
    first = name.split()[0]
    return f"Bonjour {first}," if first else "Bonjour,"


def _has_festival_and_nexus_bundle(tickets: tuple[TicketEmailLine, ...]) -> bool:
    labels = [t.pass_label.lower() for t in tickets]
    has_nexus = any("nexus" in label or "vip" in label for label in labels)
    has_festival = any("festival" in label for label in labels)
    return has_nexus and has_festival


def _variant_copy(ctx: TicketEmailContext) -> dict[str, str]:
    event = ctx.event_title.strip() or "TDEV Festival 2026"
    bundle = _has_festival_and_nexus_bundle(ctx.tickets)
    if ctx.variant == "nexus":
        bundle_note = ""
        if bundle:
            bundle_note = (
                " Vous recevez aussi votre Pass Festival pour les deux jours "
                "de conférences et ateliers."
            )
        return {
            "subject": f"Votre Pass Nexus Night - {event}",
            "headline": "Votre Pass Nexus Night est confirmé",
            "badge": "Pass Nexus Night",
            "intro": (
                f"Merci pour votre inscription au {event}. "
                f"Votre Pass Nexus Night est confirmé.{bundle_note} "
                "Les billets PDF avec QR code sont joints à cet e-mail."
            ),
            "header_gradient": "linear-gradient(135deg,#78350f 0%,#1a1208 55%,#0a0a0a 100%)",
            "badge_color": "#fcd34d",
            "button_bg": "#d97706",
            "button_hover": "#b45309",
            "goodies_border": "#92400e",
            "goodies_bg": "#1c1410",
        }
    return {
        "subject": f"Votre Pass Festival - {event}",
        "headline": "Votre Pass Festival est confirmé",
        "badge": "Pass Festival",
        "intro": (
            f"Merci pour votre inscription au {event}. "
            "Votre Pass Festival est confirmé. "
            "Le billet PDF avec QR code est joint à cet e-mail."
        ),
        "header_gradient": "linear-gradient(135deg,#064e3b 0%,#0a0a0a 100%)",
        "badge_color": "#6ee7b7",
        "button_bg": "#047857",
        "button_hover": "#065f46",
        "goodies_border": "#14532d",
        "goodies_bg": "#0f1a14",
    }


def _goodies_plain(shop_url: str) -> str:
    url = shop_url.strip() or DEFAULT_GOODIES_SHOP_URL
    return f"""
Goodies et Welcome Pack
Besoin de goodies, du Welcome Pack officiel ou du merch partenaires ?
Visitez la boutique TDEV Festival pour compléter votre expérience :
{url}
"""


def _goodies_html(shop_url: str, *, border: str, bg: str, accent: str) -> str:
    url = _esc(shop_url.strip() or DEFAULT_GOODIES_SHOP_URL)
    return f"""
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 24px;background:{bg};border:1px solid {border};border-radius:12px;">
                <tr>
                  <td style="padding:18px 20px;">
                    <p style="margin:0 0 8px;font-size:12px;font-weight:600;color:{accent};text-transform:uppercase;letter-spacing:0.06em;">Goodies et Welcome Pack</p>
                    <p style="margin:0 0 16px;font-size:14px;line-height:1.55;color:#d4d4d4;">
                      Besoin de goodies, du Welcome Pack ou du merch officiel du festival ?
                      Découvrez la boutique partenaire pour choisir vos articles.
                    </p>
                    <a href="{url}" style="display:inline-block;background:transparent;color:{accent};text-decoration:none;padding:12px 20px;border-radius:999px;font-size:14px;font-weight:600;border:2px solid {accent};">Découvrir les goodies</a>
                  </td>
                </tr>
              </table>"""


def build_ticket_email(ctx: TicketEmailContext) -> tuple[str, str, str]:
    """
    Retourne (subject, plain_text, html_body).
    Les PDF sont ajoutés séparément par NotifyService.
    """
    meta = _variant_copy(ctx)
    subject = meta["subject"]

    when = ctx.when_label.strip() if ctx.when_label else "Dates communiquées sur le site"
    venue = ctx.venue_line.strip() or "Lieu à confirmer"
    greeting = _greeting_name(ctx)
    shop_url = ctx.goodies_shop_url.strip() or DEFAULT_GOODIES_SHOP_URL

    ticket_plain_blocks: list[str] = []
    for t in ctx.tickets:
        ticket_plain_blocks.append(f"  - {t.pass_label} · {t.holder_name} · n° {t.serial}")
    tickets_plain = "\n".join(ticket_plain_blocks) if ticket_plain_blocks else "  - (voir PDF joint)"

    n_pdf = len(ctx.tickets)
    pdf_line = (
        f"{n_pdf} billet{'s' if n_pdf > 1 else ''} PDF {'sont' if n_pdf > 1 else 'est'} joint{'s' if n_pdf > 1 else ''} à ce message."
        if n_pdf
        else "Votre billet PDF est joint à ce message."
    )

    download_cta = "Télécharger mes billets" if n_pdf > 1 else "Télécharger mon billet"

    contact_plain = ""
    if ctx.contact_url:
        contact_plain = f"\nUne question ? {ctx.contact_url.strip()}\n"

    plain = f"""\
{greeting}

{meta['intro']}

Informations pratiques
  Date : {when}
  Lieu : {venue}

Détail de votre pass
{tickets_plain}

{pdf_line}
Présentez le QR code du PDF à l'entrée (impression ou écran de téléphone).

Vous pouvez aussi retélécharger votre billet en PDF :
{ctx.billet_url.strip()}
{_goodies_plain(shop_url)}
Conseils
  - Conservez cet e-mail et le PDF jusqu'à la fin de l'événement.
  - Si la pièce jointe n'apparaît pas, vérifiez le dossier spam ou utilisez le lien ci-dessus.

À très bientôt à Lomé,
L'équipe T-Dev Festival
{contact_plain}"""

    ticket_rows_html = ""
    for t in ctx.tickets:
        ticket_rows_html += f"""
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #262626;font-size:14px;color:#e5e5e5;">{_esc(t.pass_label)}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #262626;font-size:14px;color:#d4d4d4;">{_esc(t.holder_name)}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #262626;font-size:13px;color:#a3a3a3;font-family:ui-monospace,monospace;">{_esc(t.serial)}</td>
        </tr>"""

    if not ticket_rows_html:
        ticket_rows_html = """
        <tr>
          <td colspan="3" style="padding:12px;font-size:14px;color:#d4d4d4;">Voir le PDF joint pour le détail de votre pass.</td>
        </tr>"""

    contact_html = ""
    if ctx.contact_url:
        contact_html = f"""
    <p style="margin:24px 0 0;font-size:13px;color:#737373;line-height:1.5;text-align:center;">
      Une question ?
      <a href="{_esc(ctx.contact_url.strip())}" style="color:#34d399;text-decoration:none;">Contactez l'équipe T-Dev</a>
    </p>"""

    goodies_html = _goodies_html(
        shop_url,
        border=meta["goodies_border"],
        bg=meta["goodies_bg"],
        accent=meta["badge_color"],
    )

    html_body = f"""\
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_esc(subject)}</title>
</head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;color:#f5f5f5;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#0a0a0a;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#141414;border:1px solid #262626;border-radius:16px;overflow:hidden;">
          <tr>
            <td style="padding:28px 28px 20px;background:{meta['header_gradient']};">
              <p style="margin:0 0 6px;font-size:11px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:{meta['badge_color']};">{_esc(meta['badge'])}</p>
              <h1 style="margin:0;font-size:22px;font-weight:700;line-height:1.3;color:#ffffff;">{_esc(meta['headline'])}</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:24px 28px 8px;">
              <p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#e5e5e5;">{_esc(greeting.rstrip(','))},</p>
              <p style="margin:0 0 20px;font-size:15px;line-height:1.6;color:#d4d4d4;">{_esc(meta['intro'])}</p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 20px;background:#1a1a1a;border:1px solid #333;border-radius:12px;">
                <tr>
                  <td style="padding:14px 16px;font-size:13px;color:#a3a3a3;width:72px;vertical-align:top;">Date</td>
                  <td style="padding:14px 16px 14px 0;font-size:14px;color:#f5f5f5;">{_esc(when)}</td>
                </tr>
                <tr>
                  <td style="padding:0 16px 14px;font-size:13px;color:#a3a3a3;vertical-align:top;">Lieu</td>
                  <td style="padding:0 16px 14px 0;font-size:14px;color:#f5f5f5;">{_esc(venue)}</td>
                </tr>
              </table>
              <p style="margin:0 0 10px;font-size:13px;font-weight:600;color:#a3a3a3;text-transform:uppercase;letter-spacing:0.06em;">Votre pass</p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 20px;border:1px solid #333;border-radius:12px;border-collapse:collapse;overflow:hidden;">
                <tr style="background:#1f1f1f;">
                  <th align="left" style="padding:10px 12px;font-size:11px;font-weight:600;color:#737373;text-transform:uppercase;">Type</th>
                  <th align="left" style="padding:10px 12px;font-size:11px;font-weight:600;color:#737373;text-transform:uppercase;">Titulaire</th>
                  <th align="left" style="padding:10px 12px;font-size:11px;font-weight:600;color:#737373;text-transform:uppercase;">N° pass</th>
                </tr>
                {ticket_rows_html}
              </table>
              <p style="margin:0 0 20px;font-size:14px;line-height:1.6;color:#d4d4d4;">
                À l'entrée, présentez le <strong style="color:#fff;">QR code</strong> du PDF (sur papier ou sur votre téléphone).
                Conservez cet e-mail et la pièce jointe jusqu'à la fin de l'événement.
              </p>
              <p style="margin:0 0 20px;text-align:center;">
                <a href="{_esc(ctx.billet_url.strip())}" style="display:inline-block;background:{meta['button_bg']};color:#ffffff;text-decoration:none;padding:14px 24px;border-radius:999px;font-size:15px;font-weight:600;">{_esc(download_cta)}</a>
              </p>
              {goodies_html}
              <p style="margin:0;font-size:12px;line-height:1.5;color:#737373;text-align:center;">
                Pièce jointe : billet PDF avec QR code.
                Si vous ne la voyez pas, vérifiez vos spams ou utilisez le bouton ci-dessus.
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:20px 28px 28px;border-top:1px solid #262626;">
              <p style="margin:0;font-size:13px;line-height:1.5;color:#737373;text-align:center;">
                À très bientôt à Lomé · L'équipe T-Dev Festival
              </p>
              {contact_html}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    return subject, plain.strip(), html_body
