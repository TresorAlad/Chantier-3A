"""Build offline scan bundles with event keys and seen-set hints."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from tickets.capability import KeyRing


@dataclass
class EventMeta:
    """Eventmeta."""
    event_id: str
    title: str
    venue_name: str
    starts_at: datetime
    ends_at: datetime


@dataclass
class Bundle:
    """Bundle."""
    event: EventMeta
    issuer_keys: KeyRing
    ticket_index: list[str] = field(default_factory=list)
    ticket_index_present: bool = True
    admitted_index: list[str] = field(default_factory=list)
    issued_at: datetime | None = None

    def validate(self) -> None:
        """Validate on ``Bundle``."""
        if not self.event.event_id:
            raise ValueError("scan: bundle: event_id is empty")
        if not self.issuer_keys.keys:
            raise ValueError("scan: bundle: issuer_keys is empty")
