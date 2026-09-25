"""SQLite and PostgreSQL connection wrapper with query helpers."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Literal

import psycopg
from psycopg.rows import dict_row

from store.migrate import migrate_postgres, migrate_sqlite
from store.rebind import rebind_query

Driver = Literal["sqlite", "postgres"]


class NotFoundError(Exception):
    """Notfounderror."""
    pass


class SoldOutError(Exception):
    """Soldouterror."""
    pass


@dataclass
class Store:
    """Store."""
    driver: Driver
    _pg: psycopg.Connection | None = None
    _sqlite: sqlite3.Connection | None = None
    _vault: object | None = None

    @property
    def primary(self) -> psycopg.Connection | sqlite3.Connection:
        """Primary on ``Store``."""
        if self.driver == "postgres":
            assert self._pg is not None
            return self._pg
        assert self._sqlite is not None
        return self._sqlite

    def close(self) -> None:
        """Close on ``Store``."""
        if self._pg is not None:
            self._pg.close()
            self._pg = None
        if self._sqlite is not None and self.driver == "sqlite":
            self._sqlite.close()
            self._sqlite = None

    def execute(self, query: str, args: tuple[Any, ...] = ()) -> None:
        """Execute on ``Store``."""
        self.execute_rowcount(query, args)

    def execute_rowcount(self, query: str, args: tuple[Any, ...] = ()) -> int:
        """Execute rowcount on ``Store``."""
        q = rebind_query(query, self.driver)
        if self.driver == "postgres":
            assert self._pg is not None
            cur = self._pg.execute(q, args)
            self._pg.commit()
            return cur.rowcount
        assert self._sqlite is not None
        cur = self._sqlite.execute(q, args)
        self._sqlite.commit()
        return cur.rowcount

    def fetchone(self, query: str, args: tuple[Any, ...] = ()) -> Any:
        """Fetchone on ``Store``."""
        q = rebind_query(query, self.driver)
        if self.driver == "postgres":
            assert self._pg is not None
            cur = self._pg.execute(q, args)
            return cur.fetchone()
        assert self._sqlite is not None
        cur = self._sqlite.execute(q, args)
        return cur.fetchone()

    def fetchall(self, query: str, args: tuple[Any, ...] = ()) -> list[Any]:
        """Fetchall on ``Store``."""
        q = rebind_query(query, self.driver)
        if self.driver == "postgres":
            assert self._pg is not None
            cur = self._pg.execute(q, args)
            return cur.fetchall()
        assert self._sqlite is not None
        cur = self._sqlite.execute(q, args)
        return cur.fetchall()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Transaction on ``Store``."""
        if self.driver == "postgres":
            assert self._pg is not None
            with self._pg.transaction():
                yield
        else:
            assert self._sqlite is not None
            try:
                yield
                self._sqlite.commit()
            except Exception:
                self._sqlite.rollback()
                raise


def open_sqlite(path: str) -> Store:
    """Open a SQLite database file and ensure schema migrations are applied."""
    migrate_sqlite(path)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return Store(driver="sqlite", _sqlite=conn)


def open_postgres(database_url: str) -> Store:
    """Open PostgreSQL (online-only deployment)."""
    migrate_postgres(database_url)
    pg = psycopg.connect(database_url, row_factory=dict_row)
    return Store(driver="postgres", _pg=pg)


def new_ulid() -> str:
    """New ulid."""
    from ulid import ULID

    return str(ULID())
