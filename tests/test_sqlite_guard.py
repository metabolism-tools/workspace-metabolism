"""Wrong-path opens must not turn into accidental resource creation."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from workspace_metabolism.sqlite_guard import open_existing_sqlite


def make_index(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE snapshot_day (day TEXT)")
        connection.commit()
    finally:
        connection.close()


@pytest.mark.parametrize("writable", [False, True])
def test_missing_index_directory_does_not_create_database(tmp_path, writable):
    canonical = tmp_path / "data" / "index" / "app.sqlite"
    make_index(canonical)
    before = canonical.read_bytes()
    wrong = tmp_path / "data" / "app.sqlite"
    with pytest.raises(sqlite3.OperationalError):
        open_existing_sqlite(wrong, writable=writable)
    assert not wrong.exists()
    assert canonical.read_bytes() == before


def test_concurrent_wrong_path_opens_leave_no_database(tmp_path):
    wrong = tmp_path / "app.sqlite"

    def attempt(_):
        with pytest.raises(sqlite3.OperationalError):
            open_existing_sqlite(wrong, writable=True)

    with ThreadPoolExecutor(max_workers=8) as workers:
        list(workers.map(attempt, range(32)))
    assert not wrong.exists()


@pytest.mark.parametrize("contents", [b"", b"not a database"])
def test_existing_empty_or_invalid_file_is_not_initialized(tmp_path, contents):
    path = tmp_path / "app.sqlite"
    path.write_bytes(contents)
    with pytest.raises(sqlite3.DatabaseError):
        open_existing_sqlite(path, writable=True)
    assert path.read_bytes() == contents
    path.unlink()  # Also proves failed validation closed the Windows handle.


def test_required_tables_are_checked_without_repair(tmp_path):
    path = tmp_path / "app.sqlite"
    make_index(path)
    before = path.read_bytes()
    with pytest.raises(sqlite3.DatabaseError, match="missing required tables"):
        open_existing_sqlite(path, writable=True, required_tables=("other",))
    assert path.read_bytes() == before
    path.unlink()


def test_default_connection_cannot_write(tmp_path):
    path = tmp_path / "app.sqlite"
    make_index(path)
    connection = open_existing_sqlite(path, required_tables=("snapshot_day",))
    try:
        assert connection.execute("SELECT count(*) FROM snapshot_day").fetchone() == (0,)
        with pytest.raises(sqlite3.DatabaseError, match="readonly|not authorized"):
            connection.execute("INSERT INTO snapshot_day VALUES ('today')")
    finally:
        connection.close()


def test_explicit_writer_and_escaped_path(tmp_path):
    path = tmp_path / "space # percent % \u7d22\u5f15" / "app.sqlite"
    make_index(path)
    connection = open_existing_sqlite(path, writable=True)
    try:
        connection.execute("INSERT INTO snapshot_day VALUES ('today')")
        connection.commit()
    finally:
        connection.close()
    reader = open_existing_sqlite(path)
    try:
        assert reader.execute("SELECT day FROM snapshot_day").fetchone() == ("today",)
    finally:
        reader.close()


@pytest.mark.parametrize("sql", [
    "CREATE TABLE IF NOT EXISTS extra (value TEXT)",
    "CREATE TEMP TABLE extra (value TEXT)",
    "ALTER TABLE snapshot_day ADD COLUMN extra TEXT",
    "DROP TABLE snapshot_day",
    "DELETE FROM snapshot_day",
    "PRAGMA user_version=7",
    "PRAGMA writable_schema=ON",
    "PRAGMA query_only=OFF",
])
def test_readonly_rejects_initialization_and_other_writes(tmp_path, sql):
    path = tmp_path / "app.sqlite"
    make_index(path)
    before = path.read_bytes()
    connection = open_existing_sqlite(path)
    try:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute(sql)
    finally:
        connection.close()
    assert path.read_bytes() == before


def test_readonly_cannot_attach_and_create_another_database(tmp_path):
    path = tmp_path / "app.sqlite"
    make_index(path)
    other = tmp_path / "wrong.sqlite"
    connection = open_existing_sqlite(path)
    try:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute("ATTACH DATABASE ? AS other", (str(other),))
    finally:
        connection.close()
    assert not other.exists()


def test_initializing_reader_reproduced_but_guarded_reader_refuses(tmp_path):
    legacy = tmp_path / "legacy.sqlite"
    guarded = tmp_path / "guarded.sqlite"
    legacy.touch()
    guarded.touch()

    def initialize_then_read(connection):
        connection.execute("CREATE TABLE IF NOT EXISTS snapshot_day (day TEXT)")
        return connection.execute("SELECT * FROM snapshot_day").fetchall()

    connection = sqlite3.connect(legacy)
    try:
        assert initialize_then_read(connection) == []  # False appearance of a healthy empty index.
    finally:
        connection.close()
    assert legacy.stat().st_size > 0
    with pytest.raises(sqlite3.DatabaseError, match="no user tables"):
        open_existing_sqlite(guarded)
    assert guarded.read_bytes() == b""
