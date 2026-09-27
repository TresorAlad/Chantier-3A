"""Database store facade: PostgreSQL access and shared errors."""

from store.store import NotFoundError, Store, open_postgres

__all__ = ["Store", "NotFoundError", "open_postgres"]
