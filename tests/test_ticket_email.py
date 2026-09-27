"""Tests du modèle e-mail billet."""

from notify.ticket_email import TicketEmailContext, TicketEmailLine, build_ticket_email


def test_build_ticket_email_includes_message_and_event():
    ctx = TicketEmailContext(
        buyer_name="Awa Mensah",
        event_title="Tdev Festival 2026",
        when_label="samedi, 21 nov. | 9:00 am",
        venue_line="Lomé Convention Center",
        billet_url="https://festival.example/order/abc/billet?email=awa%40test.com",
        tickets=(
            TicketEmailLine(pass_label="Pass Standard", holder_name="Awa Mensah", serial="TDEV-001"),
        ),
        contact_url="https://festival.example/contact",
    )
    subject, plain, html = build_ticket_email(ctx)

    assert "Tdev Festival" in subject
    assert "Bonjour Awa" in plain
    assert "Pass Standard" in plain
    assert "TDEV-001" in plain
    assert "PDF" in plain
    assert "QR code" in plain
    assert "abc/billet" in plain
    assert "Référence :" not in plain

    assert "Votre pass est confirmé" in html
    assert "Pass Standard" in html
    assert "Ouvrir mon billet en ligne" in html
    assert "Contactez l'équipe T-Dev" in html


def test_preview_writes_html_files(tmp_path, monkeypatch):
    from notify import preview_ticket_email as preview_mod

    monkeypatch.setattr(preview_mod, "PREVIEWS_DIR", tmp_path)
    shell, body = preview_mod.write_previews()
    assert shell.exists() and body.exists()
    assert "Aperçu - E-mail confirmation billet" in shell.read_text(encoding="utf-8")
    assert "Votre pass est confirmé" in body.read_text(encoding="utf-8")
