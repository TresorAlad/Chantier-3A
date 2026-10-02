"""Génère un aperçu HTML statique de l'e-mail billet (sans envoi SMTP).

Usage:
    cd backend-python
    python -m notify.preview_ticket_email
"""

from __future__ import annotations

from pathlib import Path

from notify.ticket_email import TicketEmailContext, TicketEmailLine, build_ticket_email

PREVIEWS_DIR = Path(__file__).resolve().parent / "previews"


def sample_context() -> TicketEmailContext:
    """Données fictives pour l'aperçu."""
    return TicketEmailContext(
        buyer_name="Awa Mensah",
        event_title="Tdev Festival 2026",
        when_label="samedi, 21 nov. | 9:00 am",
        venue_line="Lomé Convention Center, Lomé, Togo",
        billet_url="https://festival.ourtdev.com/api/orders/01EXAMPLE/guest/ticket.pdf?email=awa.mensah%40example.com",
        tickets=(
            TicketEmailLine(
                pass_label="Pass Festival",
                holder_name="Awa Mensah",
                serial="TDEV-2026-0042",
            ),
        ),
        contact_url="https://festival.ourtdev.com/contact",
        variant="festival",
        goodies_shop_url="https://shop.tdevfestival.com",
    )


def sample_nexus_context() -> TicketEmailContext:
    """Commande Nexus avec Pass Festival inclus."""
    return TicketEmailContext(
        buyer_name="Kofi Mensah",
        event_title="Tdev Festival 2026",
        when_label="21-22 nov. 2026",
        venue_line="Lomé Convention Center, Lomé, Togo",
        billet_url="https://festival.ourtdev.com/api/orders/01NEXUS/guest/ticket.pdf?email=kofi.mensah%40example.com",
        tickets=(
            TicketEmailLine(
                pass_label="Pass Nexus Night",
                holder_name="Kofi Mensah",
                serial="NX-2026-0007",
            ),
            TicketEmailLine(
                pass_label="Pass Festival",
                holder_name="Kofi Mensah",
                serial="FF-2026-0007",
            ),
        ),
        contact_url="https://festival.ourtdev.com/contact",
        variant="nexus",
        goodies_shop_url="https://shop.tdevfestival.com",
    )


def _preview_shell(subject: str, plain: str, email_html: str) -> str:
    plain_escaped = (
        plain.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return f"""\
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Aperçu e-mail billet - Tdev Festival</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      background: #0f0f0f;
      color: #e5e5e5;
    }}
    .banner {{
      padding: 20px 24px;
      background: #1a1a1a;
      border-bottom: 1px solid #333;
    }}
    .banner h1 {{
      margin: 0 0 8px;
      font-size: 1.25rem;
      font-weight: 600;
    }}
    .banner p {{
      margin: 4px 0;
      font-size: 0.875rem;
      color: #a3a3a3;
      line-height: 1.5;
    }}
    .banner .subject {{
      color: #6ee7b7;
      font-weight: 500;
    }}
    main {{
      max-width: 960px;
      margin: 0 auto;
      padding: 24px 16px 48px;
    }}
    section {{
      margin-bottom: 32px;
    }}
    section h2 {{
      margin: 0 0 12px;
      font-size: 0.75rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #737373;
    }}
    .iframe-wrap {{
      border: 1px solid #333;
      border-radius: 12px;
      overflow: hidden;
      background: #0a0a0a;
    }}
    iframe {{
      display: block;
      width: 100%;
      min-height: 720px;
      border: 0;
    }}
    pre.plain {{
      margin: 0;
      padding: 20px;
      background: #141414;
      border: 1px solid #333;
      border-radius: 12px;
      font-size: 13px;
      line-height: 1.55;
      white-space: pre-wrap;
      word-break: break-word;
      color: #d4d4d4;
    }}
    .note {{
      font-size: 13px;
      color: #737373;
      margin-top: 8px;
    }}
    a.link {{
      color: #34d399;
    }}
  </style>
</head>
<body>
  <header class="banner">
    <h1>Aperçu - E-mail confirmation billet</h1>
    <p class="subject">Objet : {subject.replace("&", "&amp;").replace("<", "&lt;")}</p>
    <p>
      Fichier généré par
      <code>python -m notify.preview_ticket_email</code>.
      Les PDF restent des pièces jointes réelles à l'envoi SMTP.
    </p>
    <p>
      Corps HTML seul :
      <a class="link" href="ticket-email-body.html">ticket-email-body.html</a>
    </p>
  </header>
  <main>
    <section aria-labelledby="html-preview">
      <h2 id="html-preview">Rendu HTML (client mail)</h2>
      <div class="iframe-wrap">
        <iframe title="Aperçu HTML e-mail billet" src="ticket-email-body.html"></iframe>
      </div>
      <p class="note">Ouvrez ticket-email-body.html pour voir le mail seul, sans chrome d'aperçu.</p>
    </section>
    <section aria-labelledby="plain-preview">
      <h2 id="plain-preview">Version texte brut</h2>
      <pre class="plain">{plain_escaped}</pre>
    </section>
  </main>
</body>
</html>"""


def write_previews(ctx: TicketEmailContext | None = None) -> tuple[Path, Path]:
    """Écrit previews/ticket-email.html et ticket-email-body.html."""
    ctx = ctx or sample_context()
    subject, plain, email_html = build_ticket_email(ctx)

    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    body_path = PREVIEWS_DIR / "ticket-email-body.html"
    shell_path = PREVIEWS_DIR / "ticket-email.html"

    body_path.write_text(email_html, encoding="utf-8")
    shell_path.write_text(_preview_shell(subject, plain, email_html), encoding="utf-8")
    return shell_path, body_path


def write_ticket_samples() -> tuple[Path, Path]:
    """Render the sample pass as PNG and PDF (same renderer as the real attachment)."""
    from notify.ticket_image import TicketImageInput, render_pass_ticket_pdf, render_pass_ticket_png

    inp = TicketImageInput(
        event_title="Tdev Festival 2026",
        pass_label="Pass Standard",
        holder_name="Awa Mensah",
        when_label="samedi, 21 nov. | 9:00 am",
        venue_line="Lomé Convention Center, Lomé, Togo",
        serial="TDEV-2026-0042",
        capability="exemple-de-capability-non-valide",
    )
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    png_path = PREVIEWS_DIR / "billet-exemple.png"
    pdf_path = PREVIEWS_DIR / "billet-exemple.pdf"
    png_path.write_bytes(render_pass_ticket_png(inp))
    pdf_path.write_bytes(render_pass_ticket_pdf(inp))
    return png_path, pdf_path


def write_nexus_preview() -> Path:
    """Aperçu HTML du template Pass Nexus Night."""
    _, _, email_html = build_ticket_email(sample_nexus_context())
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    path = PREVIEWS_DIR / "ticket-email-body-nexus.html"
    path.write_text(email_html, encoding="utf-8")
    return path


def main() -> None:
    shell, body = write_previews()
    nexus_body = write_nexus_preview()
    print(f"wrote {shell}")
    print(f"wrote {body}")
    print(f"wrote {nexus_body}")
    for path in write_ticket_samples():
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
