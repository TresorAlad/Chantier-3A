"""PostgreSQL connection wrapper with query helpers."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row

from store.migrate import migrate_postgres
from store.rebind import rebind_query


class NotFoundError(Exception):
    """Notfounderror."""
    pass


class SoldOutError(Exception):
    """Soldouterror."""
    pass


@dataclass
class Store:
    """Store."""
    _pg: psycopg.Connection
    _vault: object | None = None

    @property
    def primary(self) -> psycopg.Connection:
        """Primary on ``Store``."""
        return self._pg

    def close(self) -> None:
        """Close on ``Store``."""
        if self._pg is not None and not self._pg.closed:
            self._pg.close()

    def execute(self, query: str, args: tuple[Any, ...] = ()) -> None:
        """Execute on ``Store``."""
        self.execute_rowcount(query, args)

    def execute_rowcount(self, query: str, args: tuple[Any, ...] = ()) -> int:
        """Execute rowcount on ``Store``."""
        q = rebind_query(query)
        cur = self._pg.execute(q, args)
        self._pg.commit()
        return cur.rowcount

    def fetchone(self, query: str, args: tuple[Any, ...] = ()) -> Any:
        """Fetchone on ``Store``."""
        q = rebind_query(query)
        cur = self._pg.execute(q, args)
        return cur.fetchone()

    def fetchall(self, query: str, args: tuple[Any, ...] = ()) -> list[Any]:
        """Fetchall on ``Store``."""
        q = rebind_query(query)
        cur = self._pg.execute(q, args)
        return cur.fetchall()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Transaction on ``Store``."""
        with self._pg.transaction():
            yield


def open_postgres(database_url: str) -> Store:
    """Open PostgreSQL and apply pending schema migrations."""
    migrate_postgres(database_url)
    pg = psycopg.connect(database_url, row_factory=dict_row)
    return Store(_pg=pg)


def new_ulid() -> str:
    """New ulid."""
    from ulid import ULID

    return str(ULID())
