"""Open existing SQLite resources without silently creating a new database."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def _read_authorizer(action, arg1, arg2, database, source):
    """Restrict SQL effects, including temp writes and attaching another file."""
    if action in {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_RECURSIVE}:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() != "load_extension":
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_PRAGMA and (arg1 or "").lower() in {
        "table_info", "table_xinfo", "index_list", "index_info", "database_list", "busy_timeout",
    }:
        return sqlite3.SQLITE_OK
    if action in {sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT}:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def open_existing_sqlite(
    path: Path,
    *,
    writable: bool = False,
    required_tables: tuple[str, ...] = (),
) -> sqlite3.Connection:
    """Return a caller-owned connection to an existing, initialized database.

    Callers must obtain the path from their authoritative resource configuration,
    not a filename search. Table names are compatibility checks, not identity or
    authorization. Read-only connections also reject schema/temp writes and
    ATTACH. Trusted callers can remove that SQL guard; this is not a sandbox.
    """
    path = path.resolve()
    mode = "rw" if writable else "ro"
    # Enforce non-creation at open time, not via a racy exists() pre-check.
    connection = sqlite3.connect(path.as_uri() + f"?mode={mode}", uri=True, timeout=30)
    try:
        if not writable:
            connection.set_authorizer(_read_authorizer)
        tables = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type = 'table' "
                "AND name NOT GLOB 'sqlite_*'"
            )
        }
        if not tables:
            raise sqlite3.DatabaseError("database has no user tables; initialization is separate")
        missing = set(required_tables) - tables
        if missing:
            raise sqlite3.DatabaseError(f"database is missing required tables: {sorted(missing)}")
    except BaseException:
        connection.close()
        raise
    return connection
