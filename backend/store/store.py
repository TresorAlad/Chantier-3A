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
    """Raised when a requested record is not found."""

    pass


class SoldOutError(Exception):
    """Raised when a ticket or resource is sold out."""

    pass


@dataclass
class Store:
    """PostgreSQL connection and query helper wrapper."""

    _pg: psycopg.Connection
    _vault: object | None = None

    @property
    def primary(self) -> psycopg.Connection:
        """Return the primary PostgreSQL connection."""
        return self._pg

    def close(self) -> None:
        """Close the PostgreSQL connection."""
        if self._pg is not None and not self._pg.closed:
            self._pg.close()

    def rollback(self) -> None:
        """Rollback safely if the connection is still usable."""
        if self._pg is None or self._pg.closed:
            return

        try:
            self._pg.rollback()
        except psycopg.OperationalError:
            # Connection was lost. Nothing can be rolled back.
            return
        except Exception:
            return

    def commit(self) -> None:
        """Commit safely."""
        if self._pg is None or self._pg.closed:
            raise psycopg.OperationalError("PostgreSQL connection is closed")

        self._pg.commit()

    def execute(
        self,
        query: str,
        args: tuple[Any, ...] = (),
    ) -> None:
        """Execute a SQL statement."""
        self.execute_rowcount(query, args)

    def execute_rowcount(
        self,
        query: str,
        args: tuple[Any, ...] = (),
    ) -> int:
        """Execute a SQL statement and return its affected row count."""
        q = rebind_query(query)

        try:
            cur = self._pg.execute(q, args)
            self._pg.commit()
            return cur.rowcount

        except Exception:
            self.rollback()
            raise

    def fetchone(
        self,
        query: str,
        args: tuple[Any, ...] = (),
    ) -> Any:
        """Execute a SELECT query and return one row."""
        q = rebind_query(query)

        try:
            cur = self._pg.execute(q, args)
            result = cur.fetchone()

            # End the implicit transaction created by PostgreSQL
            # for this SELECT.
            self._pg.commit()

            return result

        except Exception:
            self.rollback()
            raise

    def fetchall(
        self,
        query: str,
        args: tuple[Any, ...] = (),
    ) -> list[Any]:
        """Execute a SELECT query and return all rows."""
        q = rebind_query(query)

        try:
            cur = self._pg.execute(q, args)
            result = cur.fetchall()

            # End the implicit transaction created by PostgreSQL.
            self._pg.commit()

            return result

        except Exception:
            self.rollback()
            raise

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Run operations inside a PostgreSQL transaction."""
        try:
            with self._pg.transaction():
                yield
        except Exception:
            self.rollback()
            raise


def open_postgres(database_url: str) -> Store:
    """Open PostgreSQL and apply pending schema migrations."""
    migrate_postgres(database_url)

    pg = psycopg.connect(
        database_url,
        row_factory=dict_row,
    )

    return Store(_pg=pg)


def new_ulid() -> str:
    """Generate a new ULID."""
    from ulid import ULID

    return str(ULID())