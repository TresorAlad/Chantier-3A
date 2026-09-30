"""Festival pass ticket (PNG for guest download, PDF for e-mail attachment) with Pillow + qrcode."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont
from qrcode.constants import ERROR_CORRECT_H

_ASSETS = Path(__file__).resolve().parent / "assets"
_SANS_PATH = _ASSETS / "fonts" / "Sora.ttf"
_MONO_PATH = _ASSETS / "fonts" / "JetBrainsMono.ttf"
_LOGO_PATH = _ASSETS / "logo-square.png"

# Layout is designed in "units" (a 448-wide canvas) and drawn at _DRAW times that size, then
# reduced to _OUT times (supersampling keeps rounded corners and text smooth).
_DRAW = 4
_OUT = 2

_CANVAS_W = 448
_CARD_X = 32
_CARD_W = 384
_CARD_TOP = 4
_CARD_RADIUS = 24
_HEADER_H = 86
_PAD = 21
_LOGO_SIZE = 68
_QR_FRAME = 272
_QR_SIZE = 216
_QR_LOGO = 45
_NOTCH_R = 12
_FOOTER_H = 80

_BG = "#0a0a0a"
_INK = "#171717"
_MUTED = "#525252"
_GREEN_TEXT = "#047857"
_HASHTAG = "#5c5c5c"
_DEFAULT_TITLE = "Tdev Festival 2026"
_DEFAULT_VENUE = "Lieu à confirmer"
_HASHTAG_TEXT = "#TDev2026"


@dataclass
class TicketImageInput:
    """Fields shown on the festival pass."""

    event_title: str
    pass_label: str
    holder_name: str
    when_label: str | None
    venue_line: str
    serial: str
    capability: str


def _u(value: float) -> int:
    """Units to drawing pixels."""
    return round(value * _DRAW)


@lru_cache(maxsize=32)
def _font(path: Path, size: float, weight: int) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(path), _u(size))
    font.set_variation_by_axes([weight])
    return font


def _sans(size: float, weight: int = 500) -> ImageFont.FreeTypeFont:
    return _font(_SANS_PATH, size, weight)


def _mono(size: float, weight: int = 600) -> ImageFont.FreeTypeFont:
    return _font(_MONO_PATH, size, weight)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    """Greedy word wrap; a single word wider than the line is kept whole (never clipped)."""
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


@lru_cache(maxsize=1)
def _logo_square() -> Image.Image | None:
    """Brand mark on a green square, or None if the asset is missing (ticket still renders)."""
    if not _LOGO_PATH.is_file():
        return None
    return Image.open(_LOGO_PATH).convert("RGB")


def _logo(size_units: float, radius_units: float = 0) -> Image.Image | None:
    logo = _logo_square()
    if logo is None:
        return None
    size = _u(size_units)
    out = logo.resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")
    if radius_units:
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=_u(radius_units), fill=255)
        out.putalpha(mask)
    return out


def _paste(base: Image.Image, overlay: Image.Image | None, xy: tuple[float, float]) -> None:
    if overlay is not None:
        base.paste(overlay, (_u(xy[0]), _u(xy[1])), overlay)


def _gradient(width: int, height: int, left: tuple[int, int, int], right: tuple[int, int, int]) -> Image.Image:
    strip = Image.new("RGB", (width, 1))
    for x in range(width):
        t = x / max(1, width - 1)
        strip.putpixel((x, 0), tuple(round(a + (b - a) * t) for a, b in zip(left, right)))  # type: ignore[arg-type]
    return strip.resize((width, height))


def _build_qr(capability: str) -> Image.Image:
    """QR with the brand logo in the centre; error correction H absorbs the covered modules."""
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=1, border=0)
    qr.add_data(capability)
    qr.make(fit=True)
    modules = qr.modules_count
    # Integer module size (in drawing pixels, even so the _DRAW to _OUT reduction stays aligned).
    box = max(2, round(_u(_QR_SIZE) / modules / 2) * 2)
    qr.box_size = box
    img = qr.make_image(fill_color="#0a0a0a", back_color="#ffffff").convert("RGB")
    logo = _logo(_QR_LOGO)
    if logo is not None:
        plate = _u(_QR_LOGO + 8)
        w = img.size[0]
        px = (w - plate) // 2
        plate_img = Image.new("RGBA", (plate, plate), (255, 255, 255, 255))
        mask = Image.new("L", (plate, plate), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, plate - 1, plate - 1], radius=_u(6), fill=255)
        img.paste(plate_img, (px, px), mask)
        img.paste(logo, ((w - logo.size[0]) // 2, (w - logo.size[1]) // 2), logo)
    return img


def _centered(draw: ImageDraw.ImageDraw, cx: float, y: float, text: str, font, fill: str) -> None:
    draw.text((_u(cx) - draw.textlength(text, font=font) / 2, _u(y)), text, fill=fill, font=font)


def render_pass_ticket_png(inp: TicketImageInput) -> bytes:
    """Render the pass: dark page, white rounded card with QR, perforated stub, footer branding."""
    title_font = _sans(20, 700)
    pass_font = _sans(16, 600)
    when_font = _sans(15, 600)
    name_font = _sans(18, 700)
    holder_font = _sans(15, 600)
    venue_font = _sans(15, 600)
    ident_font = _mono(13, 700)
    hashtag_font = _sans(16, 700)

    scratch = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    text_x = _PAD + _LOGO_SIZE + 14
    text_w = _u(_CARD_W - text_x - _PAD)
    title_lines = _wrap_text(scratch, inp.event_title.strip() or _DEFAULT_TITLE, title_font, text_w)
    venue_lines = _wrap_text(scratch, inp.venue_line.strip() or _DEFAULT_VENUE, venue_font, _u(_CARD_W - _PAD * 2))

    info_h = max(_LOGO_SIZE + 2 * _PAD, 26 * len(title_lines) + 22 + (22 if inp.when_label else 0) + 2 * _PAD)
    qr_zone_h = 12 + _QR_FRAME + 24 + 26 + 24 + 14
    stub_h = 16 + 22 * len(venue_lines) + 8 + 24 + 20
    card_h = _HEADER_H + info_h + qr_zone_h + stub_h
    canvas_h = _CARD_TOP + card_h + _FOOTER_H

    card = Image.new("RGB", (_u(_CARD_W), _u(card_h)), "#ffffff")
    cd = ImageDraw.Draw(card)

    # Header band with logo.
    card.paste(_gradient(_u(_CARD_W), _u(_HEADER_H), (5, 150, 105), (4, 100, 78)), (0, 0))
    header_logo = _logo(36)
    if header_logo is not None:
        _paste(card, header_logo, ((_CARD_W - 36) / 2, (_HEADER_H - 36) / 2))

    # Title block.
    y = _HEADER_H + _PAD
    _paste(card, _logo(_LOGO_SIZE, 10), (_PAD, y))
    ty = y - 2
    for line in title_lines:
        cd.text((_u(text_x), _u(ty)), line, fill=_INK, font=title_font)
        ty += 26
    cd.text((_u(text_x), _u(ty + 2)), inp.pass_label, fill=_GREEN_TEXT, font=pass_font)
    ty += 24
    if inp.when_label:
        cd.text((_u(text_x), _u(ty)), inp.when_label, fill=_MUTED, font=when_font)

    # QR zone (light panel).
    zone_top = _HEADER_H + info_h
    cd.rectangle([0, _u(zone_top), _u(_CARD_W), _u(zone_top + qr_zone_h)], fill="#fafafa")
    fy = zone_top + 12
    fx = (_CARD_W - _QR_FRAME) / 2
    cd.rounded_rectangle(
        [_u(fx), _u(fy), _u(fx + _QR_FRAME), _u(fy + _QR_FRAME)], radius=_u(18), fill="#ffffff", outline="#ececec", width=_DRAW
    )
    qr = _build_qr(inp.capability)
    card.paste(qr, (_u(_CARD_W / 2) - qr.size[0] // 2, _u(fy + _QR_FRAME / 2) - qr.size[1] // 2))

    ny = fy + _QR_FRAME + 24
    _centered(cd, _CARD_W / 2, ny, inp.pass_label, name_font, _INK)
    _centered(cd, _CARD_W / 2, ny + 28, inp.holder_name, holder_font, "#404040")

    # Perforation + stub.
    perf_y = zone_top + qr_zone_h
    cd.rectangle([0, _u(perf_y), _u(_CARD_W), _u(perf_y + stub_h)], fill="#f4f4f4")
    x = _NOTCH_R + 8
    while x < _CARD_W - _NOTCH_R - 8:
        cd.line([(_u(x), _u(perf_y)), (_u(x + 5), _u(perf_y))], fill="#cfcfcf", width=_DRAW)
        x += 9
    sy = perf_y + 24
    for line in venue_lines:
        _centered(cd, _CARD_W / 2, sy, line, venue_font, _MUTED)
        sy += 22
    _centered(cd, _CARD_W / 2, sy + 10, f"Identifiant · {inp.serial}", ident_font, "#737373")

    # Card mask: rounded corners and the two perforation notches.
    mask = Image.new("L", card.size, 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, card.size[0] - 1, card.size[1] - 1], radius=_u(_CARD_RADIUS), fill=255)
    r = _u(_NOTCH_R)
    for cx in (0, card.size[0]):
        md.ellipse([cx - r, _u(perf_y) - r, cx + r, _u(perf_y) + r], fill=0)

    canvas = Image.new("RGB", (_u(_CANVAS_W), _u(canvas_h)), _BG)
    canvas.paste(card, (_u(_CARD_X), _u(_CARD_TOP)), mask)

    # Footer branding.
    cv = ImageDraw.Draw(canvas)
    footer_y = _CARD_TOP + card_h + 24
    _paste(canvas, _logo(28), (8, footer_y))
    tag_w = cv.textlength(_HASHTAG_TEXT, font=hashtag_font)
    cv.text((_u(_CANVAS_W - 8) - tag_w, _u(footer_y + 8)), _HASHTAG_TEXT, fill=_HASHTAG, font=hashtag_font)

    final = canvas.resize((_CANVAS_W * _OUT, round(canvas_h * _OUT)), Image.Resampling.LANCZOS)
    buf = BytesIO()
    final.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_pass_ticket_pdf(inp: TicketImageInput) -> bytes:
    """Single-page PDF whose page is the pass artwork itself."""
    png = render_pass_ticket_png(inp)
    page = Image.open(BytesIO(png)).convert("RGB")
    out = BytesIO()
    page.save(out, format="PDF", resolution=150.0)
    return out.getvalue()
