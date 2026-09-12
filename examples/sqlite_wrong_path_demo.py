"""Reproduce an accidental SQLite open using temporary, synthetic data only."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

from workspace_metabolism.sqlite_guard import open_existing_sqlite
from workspace_metabolism.resources import check_sqlite_resource


def run_demo() -> dict:
    with TemporaryDirectory(prefix="wm-sqlite-path-") as directory:
        root = Path(directory)
        canonical = root / "data" / "index" / "app.sqlite"
        canonical.parent.mkdir(parents=True)
        connection = sqlite3.connect(canonical)
        connection.execute("CREATE TABLE snapshot_day (day TEXT)")
        connection.commit()
        connection.close()
        original = canonical.read_bytes()

        # Separate branches keep the legacy artifact as evidence until teardown.
        legacy = root / "legacy" / "data" / "app.sqlite"
        guarded = root / "guarded" / "data" / "app.sqlite"
        legacy.parent.mkdir(parents=True)
        guarded.parent.mkdir(parents=True)
        sqlite3.connect(legacy).close()
        refused = False
        try:
            connection = open_existing_sqlite(guarded, writable=True)
        except sqlite3.OperationalError:
            refused = True
        else:
            connection.close()

        reader = open_existing_sqlite(canonical, required_tables=("snapshot_day",))
        try:
            rows = reader.execute("SELECT count(*) FROM snapshot_day").fetchone()[0]
        finally:
            reader.close()
        result = {
            "synthetic_only": True,
            "legacy_wrong_path_created_file": legacy.exists(),
            "guarded_wrong_path_refused": refused,
            "guarded_wrong_path_created_file": guarded.exists(),
            "canonical_read_succeeded": rows == 0,
            "canonical_unchanged": canonical.read_bytes() == original,
        }
        if not (result["legacy_wrong_path_created_file"] and refused
                and not guarded.exists() and result["canonical_read_succeeded"]
                and result["canonical_unchanged"]):
            raise RuntimeError(f"wrong-path regression: {result}")
        registry = {"version": 1, "entries": [{
            "path": "data/index/app.sqlite", "resource_id": "query-index",
            "grade": "G2", "cleanup": "never",
            "sqlite": {"required_tables": ["snapshot_day"]},
        }]}
        result["registered_resource_check"] = check_sqlite_resource(root, registry, "query-index")
        # An old "reader" may initialize first and then report misleading success.
        connection = sqlite3.connect(legacy)
        try:
            connection.execute("CREATE TABLE IF NOT EXISTS snapshot_day (day TEXT)")
            result["legacy_initializing_reader_result"] = connection.execute("SELECT * FROM snapshot_day").fetchall()
        finally:
            connection.close()
        guarded.touch()
        try:
            connection = open_existing_sqlite(guarded)
        except sqlite3.DatabaseError:
            result["empty_reader_refused_without_repair"] = guarded.read_bytes() == b""
        else:
            connection.close()
            raise RuntimeError("empty reader unexpectedly accepted")
        if not result["empty_reader_refused_without_repair"]:
            raise RuntimeError("empty reader modified the database")
        return result


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
