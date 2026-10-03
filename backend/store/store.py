"""PostgreSQL connection wrapper with query helpers."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

import psycopg
from psycopg.pq import TransactionStatus
from psycopg.rows import dict_row

from store.migrate import migrate_postgres
from store.rebind import rebind_query


class NotFoundError(Exception):
    """Notfounderror."""
    pass


class SoldOutError(Exception):
    """Soldouterror."""
    pass


def _connect_postgres(database_url: str) -> psycopg.Connection:
    from store.db_identity import normalize_database_url

    url = normalize_database_url(database_url)
    kwargs: dict = {"row_factory": dict_row, "connect_timeout": 20}
    if "neon.tech" in url.lower():
        kwargs["keepalives"] = 1
        kwargs["keepalives_idle"] = 30
        kwargs["keepalives_interval"] = 10
        kwargs["keepalives_count"] = 5
    return psycopg.connect(url, **kwargs)


@dataclass
class Store:
    """Store."""
    _pg: psycopg.Connection
    _database_url: str = ""
    _vault: object | None = None
    _tx_depth: int = field(default=0, init=False, repr=False, compare=False)

    def _ensure_connection(self) -> None:
        if not self._database_url:
            return
        if self._pg.closed:
            self._pg = _connect_postgres(self._database_url)
            return
        try:
            self._pg.check()
        except psycopg.OperationalError:
            try:
                self._pg.close()
            except Exception:
                pass
            self._pg = _connect_postgres(self._database_url)

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
        self._ensure_connection()
        q = rebind_query(query)
        try:
            cur = self._pg.execute(q, args)
        except Exception:
            self._pg.rollback()  # a failed statement must not leave the shared connection aborted
            raise
        self._pg.commit()
        return cur.rowcount

    def fetchone(self, query: str, args: tuple[Any, ...] = ()) -> Any:
        """Fetchone on ``Store``."""
        self._ensure_connection()
        q = rebind_query(query)
        cur = self._pg.execute(q, args)
        return cur.fetchone()

    def fetchall(self, query: str, args: tuple[Any, ...] = ()) -> list[Any]:
        """Fetchall on ``Store``."""
        self._ensure_connection()
        q = rebind_query(query)
        cur = self._pg.execute(q, args)
        return cur.fetchall()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Transaction on ``Store``: the outermost block is a real transaction, committed on exit.

        ``fetchone``/``fetchall`` leave an implicit transaction open, which would turn a bare
        ``connection.transaction()`` into a mere savepoint that nothing ever commits. Close it first.
        """
        if self._tx_depth == 0 and self._pg.info.transaction_status == TransactionStatus.INTRANS:
            self._pg.commit()
        self._tx_depth += 1
        try:
            with self._pg.transaction():
                yield
        finally:
            self._tx_depth -= 1


def open_postgres(database_url: str) -> Store:
    """Open PostgreSQL and apply pending schema migrations."""
    from store.db_identity import normalize_database_url

    url = normalize_database_url(database_url)
    migrate_postgres(url)
    pg = _connect_postgres(url)
    return Store(_pg=pg, _database_url=url)


def new_ulid() -> str:
    """New ulid."""
    from ulid import ULID

    return str(ULID())
