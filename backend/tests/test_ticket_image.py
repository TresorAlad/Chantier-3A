"""Pass ticket rendering: layout does not clip long text and the QR still decodes."""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from notify.ticket_image import TicketImageInput, render_pass_ticket_pdf, render_pass_ticket_png

# Same shape and length as a real signed capability (about 450 characters).
CAPABILITY = "v1." + "eyJ2IjoxLCJ0aWQiOiIwMUtBQkNERUZHSElKS0xNTk9QUVJTVFVWVyJ9" * 6 + ".c2lnbmF0dXJl" * 4


def _input(**overrides) -> TicketImageInput:
    base = dict(
        event_title="Tdev Festival 2026",
        pass_label="Pass étudiant",
        holder_name="Kodjo Bernard Trésor ALADE",
        when_label="jeudi, 26 nov. | 7:55 AM",
        venue_line="Lomé Convention Center, Lomé, Togo",
        serial="TDEV-2026-0001",
        capability=CAPABILITY,
    )
    base.update(overrides)
    return TicketImageInput(**base)


def test_png_matches_template_width_and_grows_with_long_title():
    short = Image.open(BytesIO(render_pass_ticket_png(_input())))
    long_title = "Tdev Festival 2026 Grande Édition Internationale de Lomé et de toute la région"
    longer = Image.open(BytesIO(render_pass_ticket_png(_input(event_title=long_title))))
    assert short.size == (896, 1488)
    assert longer.width == 896 and longer.height > short.height  # wrapped, not clipped


def test_missing_venue_and_date_still_render():
    png = render_pass_ticket_png(_input(venue_line="", when_label=None))
    assert Image.open(BytesIO(png)).width == 896


def test_pdf_is_single_page_pdf():
    pdf = render_pass_ticket_pdf(_input())
    assert pdf.startswith(b"%PDF")


@pytest.mark.parametrize("overrides", [{}, {"event_title": "Titre " * 12, "venue_line": "Adresse " * 15}])
def test_qr_decodes_to_the_capability(overrides):
    zxingcpp = pytest.importorskip("zxingcpp")
    image = Image.open(BytesIO(render_pass_ticket_png(_input(**overrides)))).convert("RGB")
    assert [r.text for r in zxingcpp.read_barcodes(image)] == [CAPABILITY]
