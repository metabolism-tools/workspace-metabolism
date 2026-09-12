import json
import os
import sqlite3

import pytest

from workspace_metabolism.cli import main
from workspace_metabolism.core import explain, load_registry
from workspace_metabolism.mcp_server import handle_message
from workspace_metabolism.resources import check_sqlite_resource, validate_resource_entries


def registered(tmp_path):
    path = tmp_path / "data" / "index" / "app.sqlite"
    path.parent.mkdir(parents=True)
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE snapshot_day (day TEXT)")
    connection.close()
    registry = {
        "version": 1,
        "entries": [
            {"path": "data/*", "grade": "G2", "cleanup": "never"},
            {"path": "data/index/app.sqlite", "grade": "G2", "cleanup": "never",
             "resource_id": "query-index", "sqlite": {"required_tables": ["snapshot_day"]}},
        ],
    }
    policy = tmp_path / "metabolism.json"
    policy.write_text(json.dumps(registry), encoding="utf-8")
    return path, policy, registry


def test_binding_ignores_same_name_empty_file_and_preserves_policy(tmp_path):
    path, policy, registry = registered(tmp_path)
    stray = tmp_path / "data" / "app.sqlite"
    stray.touch()
    before = path.read_bytes(), policy.read_bytes()
    result = check_sqlite_resource(tmp_path, registry, "query-index")
    assert result["status"] == "ok" and result["tables"] == ["snapshot_day"]
    assert result["path"] == "data/index/app.sqlite"
    assert (path.read_bytes(), policy.read_bytes()) == before
    assert stray.read_bytes() == b""
    info = explain(tmp_path, policy, tmp_path / "state", "data/app.sqlite")
    assert info["grade"] == "G2" and info["cleanup"] == "never"
    assert info["candidate"] is False


def test_unknown_name_never_falls_back_to_filename(tmp_path):
    _, _, registry = registered(tmp_path)
    for name in ("query-indxe", "app.sqlite", "data/index/app.sqlite", "QUERY-INDEX"):
        with pytest.raises(ValueError, match="unknown resource_id"):
            check_sqlite_resource(tmp_path, registry, name)


def test_missing_canonical_file_does_not_use_valid_same_name_copy(tmp_path):
    path, _, registry = registered(tmp_path)
    other = tmp_path / "data" / "app.sqlite"
    other.write_bytes(path.read_bytes())
    path.unlink()
    with pytest.raises(FileNotFoundError):
        check_sqlite_resource(tmp_path, registry, "query-index")
    assert not path.exists() and other.exists()


@pytest.mark.parametrize("kind", ["empty", "corrupt", "missing_table"])
def test_bad_registered_database_refused_without_repair(tmp_path, kind):
    path, _, registry = registered(tmp_path)
    if kind == "empty":
        path.write_bytes(b"")
    elif kind == "corrupt":
        path.write_bytes(b"not sqlite")
    else:
        registry["entries"][1]["sqlite"]["required_tables"].append("missing")
    before = path.read_bytes()
    with pytest.raises(sqlite3.DatabaseError):
        check_sqlite_resource(tmp_path, registry, "query-index")
    assert path.read_bytes() == before
    assert sorted(p.name for p in path.parent.iterdir()) == [path.name]


@pytest.mark.parametrize("change", [
    {"path": "data/*"}, {"path": "../other.sqlite"}, {"path": "/other.sqlite"},
    {"path": "data/./app.sqlite"}, {"path": "data\\app.sqlite"},
    {"path": "data/app.sqlite."}, {"path": "data/app.sqlite:stream"},
    {"resource_id": ""}, {"resource_id": 4}, {"resource_id": "QueryIndex"},
    {"sqlite": {}}, {"sqlite": {"required_tables": []}},
    {"sqlite": {"required_tables": "snapshot_day"}},
    {"sqlite": {"required_tables": ["snapshot_day", "snapshot_day"]}},
    {"sqlite": {"required_tables": [None]}},
])
def test_invalid_binding_fails_policy_loading(tmp_path, change):
    _, policy, registry = registered(tmp_path)
    registry["entries"][1].update(change)
    policy.write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(SystemExit):
        load_registry(policy)


def test_duplicate_id_is_ambiguous_not_first_match(tmp_path):
    _, _, registry = registered(tmp_path)
    registry["entries"].append(dict(registry["entries"][1], path="other.sqlite"))
    with pytest.raises(ValueError, match="duplicate resource_id"):
        check_sqlite_resource(tmp_path, registry, "query-index")


def test_legacy_policy_needs_no_resource_fields():
    validate_resource_entries([{"path": "data/*", "grade": "G2", "cleanup": "never"}])


def test_hard_link_alias_refused(tmp_path):
    path, _, registry = registered(tmp_path)
    os.link(path, tmp_path / "alias.sqlite")
    with pytest.raises(ValueError, match="hard-link"):
        check_sqlite_resource(tmp_path, registry, "query-index")


def test_symlink_alias_refused(tmp_path):
    path, _, registry = registered(tmp_path)
    other = tmp_path / "other.sqlite"
    path.rename(other)
    try:
        path.symlink_to(other)
    except OSError:
        pytest.skip("symlink creation unavailable on this host")
    with pytest.raises(ValueError, match="linked resource"):
        check_sqlite_resource(tmp_path, registry, "query-index")


def test_cli_resource_check_success_and_refusal(tmp_path, capsys):
    path, _, _ = registered(tmp_path)
    args = ["--root", str(tmp_path), "db-check", "--resource", "query-index"]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["read_only"] is True
    path.write_bytes(b"")
    assert main(args) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "blocked"
    assert path.read_bytes() == b""


def test_cli_missing_policy_does_not_initialize(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "db-check", "--resource", "query-index"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "blocked"
    assert list(tmp_path.iterdir()) == []


def call_mcp(tmp_path, policy, arguments):
    return json.loads(handle_message(json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "wm_db_check", "arguments": arguments},
    }), {"root": tmp_path, "state_dir": tmp_path / "state", "registry_path": policy}))["result"]


def test_mcp_resource_check_success_and_refusal(tmp_path):
    path, policy, _ = registered(tmp_path)
    result = call_mcp(tmp_path, policy, {"resource_id": "query-index"})
    assert json.loads(result["content"][0]["text"])["status"] == "ok"
    path.write_bytes(b"")
    assert call_mcp(tmp_path, policy, {"resource_id": "query-index"})["isError"]
    assert path.read_bytes() == b""


@pytest.mark.parametrize("extra", [{"path": "other.sqlite"}, {"sql": "CREATE TABLE x(y)"}])
def test_mcp_does_not_accept_path_or_sql_override(tmp_path, extra):
    _, policy, _ = registered(tmp_path)
    assert call_mcp(tmp_path, policy, {"resource_id": "query-index", **extra})["isError"]
