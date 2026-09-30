"""TDEV Festival 2026 schedule defaults and ticket date formatting."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

FESTIVAL_TIMEZONE = "Africa/Lome"

# Aligné vitrine (21-22 novembre 2026, Lomé).
FESTIVAL_2026_START = datetime(2026, 11, 21, 9, 0, tzinfo=ZoneInfo(FESTIVAL_TIMEZONE))
FESTIVAL_2026_END = datetime(2026, 11, 22, 22, 0, tzinfo=ZoneInfo(FESTIVAL_TIMEZONE))

_FR_WEEKDAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
_FR_MONTHS = (
    "janv.",
    "févr.",
    "mars",
    "avr.",
    "mai",
    "juin",
    "juil.",
    "août",
    "sept.",
    "oct.",
    "nov.",
    "déc.",
)


def _format_hour_fr(dt: datetime) -> str:
    if dt.minute == 0:
        return f"{dt.hour} h"
    return f"{dt.hour} h {dt.minute:02d}"


def _parse_iso(iso: str) -> datetime:
    raw = iso.replace("Z", "+00:00")
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt


def format_event_when_label(
    starts_at_iso: str | None,
    *,
    ends_at_iso: str | None = None,
    tz_name: str = FESTIVAL_TIMEZONE,
) -> str | None:
    """Human-readable schedule for pass PDF/PNG (timezone-aware)."""
    if not starts_at_iso:
        return None
    try:
        tz = ZoneInfo(tz_name or FESTIVAL_TIMEZONE)
    except Exception:
        tz = ZoneInfo(FESTIVAL_TIMEZONE)
    try:
        start = _parse_iso(starts_at_iso).astimezone(tz)
    except ValueError:
        return None

    if ends_at_iso:
        try:
            end = _parse_iso(ends_at_iso).astimezone(tz)
            if end.date() != start.date():
                month = _FR_MONTHS[start.month - 1]
                if start.month == end.month and start.year == end.year:
                    hour = _format_hour_fr(start)
                    return f"{start.day}-{end.day} {month} {start.year} | dès {hour}"
        except ValueError:
            end = None

    wd = _FR_WEEKDAYS[start.weekday()]
    month = _FR_MONTHS[start.month - 1]
    hour = _format_hour_fr(start)
    return f"{wd}, {start.day} {month} {start.year} | {hour}"
