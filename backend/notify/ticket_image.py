"""PNG pass ticket for e-mail attachment and guest download (Pillow + qrcode)."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont
from qrcode.constants import ERROR_CORRECT_H

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LOGO_PATH = _REPO_ROOT / "frontend" / "public" / "TDev " / "Tdev.png"

_CARD_W = 420
_HEADER_H = 72
_PAD = 20
_QR_SIZE = 260
_QR_FRAME_PAD = 16


@dataclass
class TicketImageInput:
    """Fields shown on the festival pass PNG."""

    event_title: str
    pass_label: str
    holder_name: str
    when_label: str | None
    venue_line: str
    serial: str
    capability: str


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold else ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    )
    for name in names:
        for root in ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation"):
            path = Path(root) / name
            if path.is_file():
                return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
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


def _paste_logo_square(base: Image.Image, xy: tuple[int, int], size: int) -> None:
    if not _LOGO_PATH.is_file():
        return
    logo = Image.open(_LOGO_PATH).convert("RGBA")
    logo = logo.resize((size, size), Image.Resampling.LANCZOS)
    base.paste(logo, xy, logo)


def _build_qr(capability: str) -> Image.Image:
    """Plain QR (no logo overlay) sized for reliable scanning."""
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=8, border=4)
    qr.add_data(capability)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0a0a0a", back_color="#ffffff").convert("RGB")
    w, _ = img.size
    if w != _QR_SIZE:
        img = img.resize((_QR_SIZE, _QR_SIZE), Image.Resampling.NEAREST)
    return img


def render_pass_ticket_png(inp: TicketImageInput) -> bytes:
    """Render a vertical pass card PNG (white card, green header, QR)."""
    title_font = _load_font(20, bold=True)
    body_font = _load_font(15)
    body_bold = _load_font(15, bold=True)
    small_font = _load_font(13)
    mono_font = _load_font(12)

    # Estimate height
    tmp = Image.new("RGB", (_CARD_W, 900))
    tdraw = ImageDraw.Draw(tmp)
    title_lines = _wrap_text(tdraw, inp.event_title.strip() or "Tdev Festival 2026", title_font, _CARD_W - _PAD * 2 - 76)
    info_h = 76 + len(title_lines) * 24 + 44
    stub_h = 88
    qr_block_h = _QR_SIZE + _QR_FRAME_PAD * 2 + 8
    height = _HEADER_H + info_h + qr_block_h + 120 + stub_h + _PAD

    img = Image.new("RGB", (_CARD_W, height), "#ffffff")
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, _CARD_W, _HEADER_H], fill="#047857")

    y = _HEADER_H + _PAD
    _paste_logo_square(img, (_PAD, y), 68)
    tx = _PAD + 68 + 12
    ty = y
    for line in title_lines:
        draw.text((tx, ty), line, fill="#171717", font=title_font)
        ty += 24
    draw.text((tx, ty + 2), inp.pass_label, fill="#047857", font=body_bold)
    ty += 22
    if inp.when_label:
        draw.text((tx, ty), inp.when_label, fill="#525252", font=body_font)
        ty += 20

    y = max(y + 76, ty) + 16
    qr = _build_qr(inp.capability)
    frame_w = _QR_SIZE + _QR_FRAME_PAD * 2
    fx = (_CARD_W - frame_w) // 2
    qx = fx + _QR_FRAME_PAD
    draw.rounded_rectangle(
        [fx, y, fx + frame_w, y + frame_w],
        radius=16,
        fill="#ffffff",
        outline="#e5e5e5",
        width=1,
    )
    img.paste(qr, (qx, y + _QR_FRAME_PAD))

    y += frame_w + 24
    pass_w = draw.textlength(inp.pass_label, font=body_bold)
    draw.text(((_CARD_W - pass_w) / 2, y), inp.pass_label, fill="#171717", font=body_bold)
    y += 22
    name_w = draw.textlength(inp.holder_name, font=body_font)
    draw.text(((_CARD_W - name_w) / 2, y), inp.holder_name, fill="#404040", font=body_font)
    y += 28

    draw.line([(_PAD, y), (_CARD_W - _PAD, y)], fill="#d4d4d4", width=1)
    y += 16
    for line in _wrap_text(draw, inp.venue_line, small_font, _CARD_W - _PAD * 2):
        lw = draw.textlength(line, font=small_font)
        draw.text(((_CARD_W - lw) / 2, y), line, fill="#525252", font=small_font)
        y += 18
    y += 8
    ident = f"Identifiant · {inp.serial}"
    iw = draw.textlength(ident, font=mono_font)
    draw.text(((_CARD_W - iw) / 2, y), ident, fill="#737373", font=mono_font)

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_pass_ticket_pdf(inp: TicketImageInput) -> bytes:
    """PDF A4-ready page wrapping the same pass artwork as the PNG."""
    png = render_pass_ticket_png(inp)
    page = Image.open(BytesIO(png)).convert("RGB")
    out = BytesIO()
    page.save(out, format="PDF", resolution=150.0)
    return out.getvalue()
