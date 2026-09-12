"""Exact resource bindings in the existing policy, with non-creating DB checks."""

from __future__ import annotations

import re
import stat
from pathlib import Path, PurePosixPath

from .sqlite_guard import open_existing_sqlite


def validate_resource_entries(entries: list[dict]) -> None:
    ids: set[str] = set()
    for entry in entries:
        if "resource_id" not in entry and "sqlite" not in entry:
            continue
        resource_id = entry.get("resource_id")
        if not isinstance(resource_id, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", resource_id):
            raise ValueError("resource_id must be a lowercase name of 1-64 characters")
        if resource_id in ids:
            raise ValueError(f"duplicate resource_id: {resource_id}")
        ids.add(resource_id)
        name = entry.get("path")
        if not isinstance(name, str) or not name or name != PurePosixPath(name).as_posix() or (
            PurePosixPath(name).is_absolute()
            or any(c in name for c in "\\:*?[]\x00")
            or any(part in (".", "..") or part.endswith((" ", ".")) for part in name.split("/"))
        ):
            raise ValueError(f"resource requires an exact relative file path: {resource_id}")
        spec = entry.get("sqlite")
        if not isinstance(spec, dict) or set(spec) != {"required_tables"}:
            raise ValueError(f"resource requires sqlite.required_tables: {resource_id}")
        tables = spec["required_tables"]
        if not isinstance(tables, list) or not tables or any(
            not isinstance(table, str) or not table.strip() or "\x00" in table for table in tables
        ):
            raise ValueError(f"required_tables must be a nonempty list of names: {resource_id}")
        if len(set(tables)) != len(tables):
            raise ValueError(f"duplicate required table: {resource_id}")


def check_sqlite_resource(root: Path, registry: dict, resource_id: str) -> dict:
    """Check the registered file only; never search, initialize, repair or delete.

    This checks current path/schema compatibility, not database identity,
    freshness, consumer health, or protection from concurrent path replacement.
    """
    if not isinstance(resource_id, str) or not resource_id:
        raise ValueError("resource_id must be a nonempty string")
    validate_resource_entries(registry["entries"])
    matches = [entry for entry in registry["entries"] if entry.get("resource_id") == resource_id]
    if not matches:
        raise ValueError(f"unknown resource_id: {resource_id}; register it in the policy first")
    entry = matches[0]
    root = root.resolve()
    target = root
    for part in PurePosixPath(entry["path"]).parts:
        target = target / part
        info = target.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0
        ):
            raise ValueError(f"linked resource paths are unsupported: {entry['path']}")
    if not target.resolve().is_relative_to(root):
        raise ValueError("resource leaves workspace")
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("resource must be a regular file without hard-link aliases")
    required = tuple(entry["sqlite"]["required_tables"])
    connection = open_existing_sqlite(target, required_tables=required)
    try:
        connection.execute("BEGIN")
        # Repeat required-table validation inside the same read snapshot as the report.
        tables = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_schema WHERE type='table' "
            "AND name NOT GLOB 'sqlite_*' ORDER BY name"
        )]
        if not set(required).issubset(tables):
            raise ValueError("required tables changed during the check; retry")
        return {
            "status": "ok", "resource_id": resource_id, "path": entry["path"],
            "read_only": True, "required_tables": list(required), "tables": tables,
            "scope": "registered_path_and_required_tables_only",
        }
    finally:
        connection.close()
