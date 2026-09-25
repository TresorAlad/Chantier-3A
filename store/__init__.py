"""Database store facade: SQLite/Postgres access and shared errors."""


from store.store import NotFoundError, Store, open_postgres, open_sqlite

__all__ = ["Store", "NotFoundError", "open_sqlite", "open_postgres"]
