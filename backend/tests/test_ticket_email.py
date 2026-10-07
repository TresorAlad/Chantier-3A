"""Tests du modèle e-mail billet."""

from notify.ticket_email import TicketEmailContext, TicketEmailLine, build_ticket_email


def test_build_festival_email_includes_goodies_shop():
    ctx = TicketEmailContext(
        buyer_name="Awa Mensah",
        event_title="Tdev Festival 2026",
        when_label="samedi, 21 nov. | 9:00 am",
        venue_line="Lomé Convention Center",
        billet_url="https://festival.example/api/orders/abc/guest/ticket.pdf?email=awa%40test.com",
        tickets=(
            TicketEmailLine(pass_label="Pass Festival", holder_name="Awa Mensah", serial="TDEV-001"),
        ),
        contact_url="https://festival.example/contact",
        variant="festival",
        goodies_shop_url="https://shop.ourtdev.com",
    )
    subject, plain, html = build_ticket_email(ctx)

    assert "Pass Festival" in subject
    assert "Bonjour Awa" in plain
    assert "Pass Festival" in plain
    assert "Goodies et Welcome Pack" in plain
    assert "shop.ourtdev.com" in plain
    assert "QR code" in plain

    assert "Votre Pass Festival est confirmé" in html
    assert "Découvrir les goodies" in html
    assert "shop.ourtdev.com" in html
    assert "Télécharger mon billet" in html
    assert "Contactez l'équipe T-Dev" in html


def test_build_nexus_email_bundle_and_goodies():
    ctx = TicketEmailContext(
        buyer_name="Kofi Mensah",
        event_title="Tdev Festival 2026",
        when_label="21-22 nov. 2026",
        venue_line="Lomé",
        billet_url="https://festival.example/api/orders/xyz/guest/ticket.pdf?email=kofi%40test.com",
        tickets=(
            TicketEmailLine(pass_label="Pass Nexus Night", holder_name="Kofi Mensah", serial="NX-001"),
            TicketEmailLine(pass_label="Pass Festival", holder_name="Kofi Mensah", serial="FF-001"),
        ),
        variant="nexus",
        goodies_shop_url="https://shop.ourtdev.com",
    )
    subject, plain, html = build_ticket_email(ctx)

    assert "Pass Nexus Night" in subject
    assert "Pass Festival" in plain
    assert "Pass Nexus Night" in plain
    assert "2 billets PDF" in plain
    assert "Goodies et Welcome Pack" in plain

    assert "Votre Pass Nexus Night est confirmé" in html
    assert "Pass Festival" in html
    assert "Télécharger mes billets" in html
    assert "Découvrir les goodies" in html


def test_preview_writes_html_files(tmp_path, monkeypatch):
    from notify import preview_ticket_email as preview_mod

    monkeypatch.setattr(preview_mod, "PREVIEWS_DIR", tmp_path)
    shell, body = preview_mod.write_previews()
    assert shell.exists() and body.exists()
    assert "Aperçu - E-mail confirmation billet" in shell.read_text(encoding="utf-8")
    assert "Votre Pass Festival est confirmé" in body.read_text(encoding="utf-8")
