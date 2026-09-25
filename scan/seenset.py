"""Seen-ticket abstraction for duplicate scan detection at the door."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


class SeenSet(Protocol):
    """Seenset."""
    def mark_seen(self, ticket_id: str, at: datetime) -> tuple[bool, Exception | None]: ...

    def seen(self, ticket_id: str) -> bool: ...


@dataclass
class MemorySeenSet:
    """Memoryseenset."""
    _seen: dict[str, datetime] = field(default_factory=dict)

    def mark_seen(self, ticket_id: str, at: datetime) -> tuple[bool, Exception | None]:
        """Mark seen on ``MemorySeenSet``."""
        if ticket_id in self._seen:
            return False, None
        self._seen[ticket_id] = at
        return True, None

    def seen(self, ticket_id: str) -> bool:
        """Seen on ``MemorySeenSet``."""
        return ticket_id in self._seen
