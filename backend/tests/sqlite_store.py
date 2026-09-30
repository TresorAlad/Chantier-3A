"""SQLite-backed ``Store`` for tests: throwaway database per test, no PostgreSQL needed.

Production stays PostgreSQL-only. This adapter reuses the real migrations, translating the few
PostgreSQL-only constructs, and mimics the slice of the psycopg connection API that ``Store``
and the ``store/*`` repositories use (``execute``, ``commit``, ``transaction``, dict rows).
"""

from __future__ import annotations

import re
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from store.paths import MIGRATIONS_DIR
from store.store import Store

_ADD_CONSTRAINT_FK = re.compile(
    r"ALTER\s+TABLE\s+\w+\s+ADD\s+CONSTRAINT\s+\w+\s+FOREIGN\s+KEY[^;]*;", re.IGNORECASE
)
_TO_CHAR_NOW = re.compile(
    r"to_char\(now\(\)\s+AT\s+TIME\s+ZONE\s+'UTC'\s*,\s*'[^']*'\)", re.IGNORECASE
)
_PG_ALTER_COLUMN = re.compile(
    r"ALTER\s+TABLE\s+\w+\s+ALTER\s+COLUMN[^;]+;",
    re.IGNORECASE | re.DOTALL,
)


def _split_pg_add_columns(sql: str) -> str:
    """PostgreSQL allows several ADD COLUMN in one ALTER; SQLite needs one per statement."""

    def repl(match: re.Match[str]) -> str:
        table = match.group(1)
        cols_part = match.group(2).strip()
        if re.search(r",\s*ADD\s+COLUMN\s+", cols_part, re.IGNORECASE) is None:
            return match.group(0)
        parts = re.split(r",\s*ADD\s+COLUMN\s+", cols_part, flags=re.IGNORECASE)
        stmts = [f"ALTER TABLE {table} ADD COLUMN {parts[0]};"]
        for part in parts[1:]:
            stmts.append(f"ALTER TABLE {table} ADD COLUMN {part};")
        return "\n".join(stmts)

    return re.sub(
        r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(.+?);",
        repl,
        sql,
        flags=re.IGNORECASE | re.DOTALL,
    )


def translate_migration(sql: str) -> str:
    """Rewrite PostgreSQL-only DDL/DML in a migration so SQLite accepts it."""
    sql = re.sub(r"\bBYTEA\b", "BLOB", sql, flags=re.IGNORECASE)
    sql = re.sub(
        r"\bSERIAL\s+PRIMARY\s+KEY\b", "INTEGER PRIMARY KEY AUTOINCREMENT", sql, flags=re.IGNORECASE
    )
    # SQLite cannot add a foreign key to an existing table; referential checks are not what
    # the unit tests exercise (the real constraint is created by the PostgreSQL migration).
    sql = _ADD_CONSTRAINT_FK.sub("", sql)
    sql = _TO_CHAR_NOW.sub("strftime('%Y-%m-%dT%H:%M:%fZ','now')", sql)
    sql = _PG_ALTER_COLUMN.sub("", sql)
    sql = re.sub(r"\bBOOLEAN\b", "INTEGER", sql, flags=re.IGNORECASE)
    sql = _split_pg_add_columns(sql)
    return sql


def translate_placeholders(query: str) -> str:
    """psycopg style (``%s``, ``%%``) to sqlite3 style (``?``, ``%``), leaving literals alone."""
    out: list[str] = []
    i, n = 0, len(query)
    while i < n:
        ch = query[i]
        if ch == "'":
            j = i + 1
            while j < n:
                if query[j] == "'":
                    if j + 1 < n and query[j + 1] == "'":
                        j += 2
                        continue
                    break
                j += 1
            out.append(query[i : j + 1])
            i = j + 1
        elif ch == "%" and query.startswith("%s", i):
            out.append("?")
            i += 2
        elif ch == "%" and query.startswith("%%", i):
            out.append("%")
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _dict_row(cursor: sqlite3.Cursor, row: tuple) -> dict[str, Any]:
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class _Result:
    """Rows fetched eagerly under the connection lock.

    Two threads running the same SQL on one sqlite3 connection (request thread and the e-mail
    notification thread) share a cached statement; fetching lazily outside the lock lets one
    thread read the other's rows.
    """

    def __init__(self, rows: list[dict[str, Any]], rowcount: int) -> None:
        self._rows = rows
        self._pos = 0
        self.rowcount = rowcount

    def fetchone(self) -> dict[str, Any] | None:
        if self._pos >= len(self._rows):
            return None
        row = self._rows[self._pos]
        self._pos += 1
        return row

    def fetchall(self) -> list[dict[str, Any]]:
        rows, self._pos = self._rows[self._pos :], len(self._rows)
        return rows


class SqliteConn:
    """Minimal stand-in for ``psycopg.Connection`` over a single shared sqlite3 connection."""

    def __init__(self, path: str | Path) -> None:
        self._conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self._conn.row_factory = _dict_row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._lock = threading.RLock()
        self._depth = 0
        self.closed = False

    def execute(self, query: str, args: tuple[Any, ...] = ()) -> _Result:
        with self._lock:
            cur = self._conn.execute(translate_placeholders(query), args)
            return _Result(cur.fetchall() if cur.description else [], cur.rowcount)

    def commit(self) -> None:
        """No-op: statements outside ``transaction()`` autocommit (``isolation_level=None``)."""

    def close(self) -> None:
        with self._lock:
            self._conn.close()
            self.closed = True

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """BEGIN/COMMIT at the outermost level, SAVEPOINT when nested (like psycopg)."""
        with self._lock:
            self._depth += 1
            name = f"sp_{self._depth}"
            self._conn.execute("BEGIN" if self._depth == 1 else f"SAVEPOINT {name}")
            try:
                yield
            except BaseException:
                self._conn.execute("ROLLBACK" if self._depth == 1 else f"ROLLBACK TO {name}")
                raise
            else:
                self._conn.execute("COMMIT" if self._depth == 1 else f"RELEASE {name}")
            finally:
                self._depth -= 1

    def executescript(self, script: str) -> None:
        with self._lock:
            self._conn.executescript(script)


def open_sqlite_store(path: str | Path) -> Store:
    """Create a fresh SQLite database at ``path`` with all migrations applied."""
    conn = SqliteConn(path)
    for migration in sorted(Path(MIGRATIONS_DIR).glob("*.sql")):
        conn.executescript(translate_migration(migration.read_text(encoding="utf-8")))
    return Store(_pg=conn)  # type: ignore[arg-type]
