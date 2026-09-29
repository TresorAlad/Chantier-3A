"""Serialize and parse UTC timestamps stored in the database."""

from __future__ import annotations

from datetime import datetime, timezone


def time_to_text(t: datetime) -> str:
    """Time to text."""
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def text_to_time(text: str) -> datetime:
    """Text to time."""
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text).astimezone(timezone.utc)


def text_to_null_time(text: str | None) -> datetime | None:
    """Text to null time."""
    if not text:
        return None
    return text_to_time(text)
