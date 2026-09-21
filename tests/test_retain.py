"""Row retention must preserve referenced evidence and restore complete SQLite rows."""
import gzip
import hashlib
import json
import sqlite3
from pathlib import Path
from contextlib import closing

import pytest

from workspace_metabolism import core
from workspace_metabolism.cli import main


@pytest.fixture
def store(tmp_path):
    db = tmp_path / "data" / "objects.db"
    db.parent.mkdir()
    with closing(sqlite3.connect(db)) as con, con:
        con.execute("CREATE TABLE objects (hash TEXT PRIMARY KEY, body BLOB NOT NULL, captured_at INTEGER NOT NULL, note TEXT, rank REAL)")
    policy = tmp_path / "metabolism.json"
    config = {"table": "objects", "blob_column": "body", "id_column": "hash",
              "group_by": ["code", "month"], "order_column": "captured_at", "keep": 1,
              "blob_encoding": "auto", "reference_paths": ["objects/*/*"], "verify_sha256": True}
    def save_config(**changes):
        config.update(changes)
        policy.write_text(json.dumps({"version": 1, "entries": [
            {"path": "data/objects.db", "grade": "G2", "cleanup": "never", "db_retain": config}]}))
    save_config()
    def put(obj, order=1, plain=False):
        raw = json.dumps(obj, sort_keys=True).encode()
        raw = raw if plain else gzip.compress(raw, mtime=0)
        key = hashlib.sha256(raw).hexdigest()
        with closing(sqlite3.connect(db)) as con, con:
            con.execute("INSERT INTO objects VALUES(?,?,?,?,?)", (key, raw, order, "完整 row", 1.25))
        return key
    def run(**kw):
        return core.retain(db, root=tmp_path, registry_path=policy, state_dir=tmp_path / "state", **kw)
    return db, put, run, save_config


def versions(put):
    return [put({"code": "A", "month": "2026-01", "bars": [i]}, order=i) for i in (1, 2, 10)]


def rows(db):
    with closing(sqlite3.connect(db)) as con, con:
        return con.execute("SELECT * FROM objects ORDER BY hash").fetchall()


def test_preview_is_byte_preserving_and_numerically_orders_versions(store, tmp_path):
    db, put, run, _ = store
    keys = versions(put)
    before = db.read_bytes()
    result = run()
    assert result["rows_to_delete"] == 2 and result["rows_deleted"] == 0
    assert db.read_bytes() == before and not (tmp_path / "state").exists()
    result = run(yes=True)
    assert [r[0] for r in rows(db)] == [keys[-1]]  # 10 must sort after 2, not as strings.
    assert result["rows_deleted"] == 2 and result["reclaimed_bytes"] == 0


def test_referenced_old_versions_and_ungrouped_payloads_survive(store):
    db, put, run, _ = store
    first, middle, latest = versions(put)
    payload = put({"objects": {"A": [first]}, "other": "archived"}, order=0)
    result = run(yes=True)
    assert result["rows_protected_by_reference"] == 1
    assert {r[0] for r in rows(db)} == {first, latest, payload}
    assert middle not in {r[0] for r in rows(db)}


def test_complete_rows_restore_idempotently_and_preserve_other_tables(store, tmp_path):
    db, put, run, _ = store
    versions(put)
    with closing(sqlite3.connect(db)) as con, con:
        con.execute("CREATE TABLE untouched (value TEXT)")
        con.execute("INSERT INTO untouched VALUES ('keep')")
    before = rows(db)
    result = run(yes=True)
    assert run(restore=result["run_id"])["rows_to_restore"] == 2
    assert len(rows(db)) == 1
    assert run(restore=result["run_id"], yes=True)["rows_restored"] == 2
    assert rows(db) == before
    assert run(restore=result["run_id"], yes=True)["rows_restored"] == 0
    with closing(sqlite3.connect(db)) as con, con:
        assert con.execute("SELECT value FROM untouched").fetchone() == ("keep",)
    entries = [json.loads(line) for line in core.journal_path(tmp_path / "state").read_text().splitlines()]
    assert [e["action"] for e in entries] == ["retain", "retain_restore", "retain_restore"]


@pytest.mark.parametrize("obj", [{"objects": {"A": ["missing"]}}, {"objects": "broken"}, {"objects": {"A": None}}])
def test_bad_references_block_all_deletion(store, obj):
    db, put, run, _ = store
    versions(put)
    put(obj)
    before = rows(db)
    with pytest.raises(ValueError, match="reference"):
        run(yes=True)
    assert rows(db) == before


def test_corrupt_or_undecodable_objects_block_deletion(store):
    db, put, run, config = store
    versions(put)
    with closing(sqlite3.connect(db)) as con, con:
        con.execute("UPDATE objects SET body=? WHERE captured_at=1", (b"broken",))
    before = rows(db)
    with pytest.raises(ValueError, match="hash mismatch"):
        run(yes=True)
    config(verify_sha256=False)
    with pytest.raises(ValueError):
        run(yes=True)
    assert rows(db) == before


def test_failed_recovery_write_never_deletes_source_and_retry_is_held(store, monkeypatch):
    db, put, run, _ = store
    versions(put)
    before = rows(db)
    save = core._retain_save
    def fail(path, raw):
        save(path, raw)
        if path.name == "manifest.json":
            raise OSError("simulated interruption")
    monkeypatch.setattr(core, "_retain_save", fail)
    with pytest.raises(OSError):
        run(yes=True)
    assert rows(db) == before
    monkeypatch.setattr(core, "_retain_save", save)
    with pytest.raises(ValueError, match="unresolved batch"):
        run(yes=True)
    manifest = next((db.parent.parent / "state/retention").glob("*/manifest.json"))
    assert run(yes=True, restore=manifest.parent.name)["rows_restored"] == 0
    assert run(yes=True)["rows_deleted"] == 2


def test_sqlite_writer_cannot_change_references_between_plan_and_delete(store, monkeypatch):
    db, put, run, _ = store
    versions(put)
    save = core._retain_save
    observed = []
    def check(path, raw):
        if path.name == "rows.json.gz":
            with closing(sqlite3.connect(db, timeout=0)) as other, other:
                with pytest.raises(sqlite3.OperationalError, match="locked"):
                    other.execute("INSERT INTO objects VALUES ('late',?,12,NULL,NULL)", (b"{}",))
            observed.append(True)
        save(path, raw)
    monkeypatch.setattr(core, "_retain_save", check)
    assert run(yes=True)["rows_deleted"] == 2 and observed


def test_restore_refuses_tampered_export_and_changed_row(store):
    db, put, run, _ = store
    keys = versions(put)
    old = rows(db)
    result = run(yes=True)
    export = Path(result["export_path"])
    original = export.read_bytes()
    export.write_bytes(gzip.compress(b"[]"))
    with pytest.raises(ValueError, match="hash/budget"):
        run(restore=result["run_id"], yes=True)
    export.write_bytes(original)
    row = next(r for r in old if r[0] == keys[0])
    with closing(sqlite3.connect(db)) as con, con:
        con.execute("INSERT INTO objects VALUES (?,?,?,?,?)", (*row[:3], "changed", row[4]))
    before = rows(db)
    with pytest.raises(ValueError, match="overwrite"):
        run(restore=result["run_id"], yes=True)
    assert rows(db) == before


@pytest.mark.parametrize("changes", [{"keep": 0}, {"reference_paths": None}, {"table": 'objects"; DROP'}, {"max_export_bytes": 1}, {"max_scan_bytes": 1}])
def test_invalid_policy_and_budgets_fail_before_delete(store, changes):
    db, put, run, config = store
    versions(put)
    config(**changes)
    before = rows(db)
    with pytest.raises(ValueError):
        run(yes=True)
    assert rows(db) == before


@pytest.mark.parametrize("ddl", ["CREATE TRIGGER side_effect AFTER DELETE ON objects BEGIN DELETE FROM objects; END",
                              "CREATE TABLE refs (key TEXT REFERENCES objects(hash))"])
def test_implicit_sqlite_side_effects_refused(store, ddl):
    db, put, run, _ = store
    versions(put)
    with closing(sqlite3.connect(db)) as con, con:
        con.execute(ddl)
    before = rows(db)
    with pytest.raises(ValueError):
        run(yes=True)
    assert rows(db) == before


def test_cli_uses_policy_and_preview_does_not_create_missing_database(store, tmp_path, capsys):
    db, put, run, _ = store
    versions(put)
    args = ["--root", str(tmp_path), "--state-dir", str(tmp_path / "state"), "retain", "--db", "data/objects.db"]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["rows_to_delete"] == 2
    db.unlink()
    assert main(args) == 2
    assert not db.exists()


def test_policy_does_not_match_suffix_or_allow_g1(store, tmp_path):
    db, put, run, _ = store
    policy = json.loads((tmp_path / "metabolism.json").read_text())
    with pytest.raises(ValueError):
        core.db_retain_policy(policy, tmp_path / "other/data/objects.db", tmp_path)
    policy["entries"][0]["grade"] = "G1"
    with pytest.raises(ValueError, match="G2"):
        core.db_retain_policy(policy, db, tmp_path)


def test_protected_window_blocks_retain(store, monkeypatch):
    db, put, run, _ = store
    versions(put)
    monkeypatch.setattr(core, "in_protected_window", lambda *a: True)
    with pytest.raises(ValueError, match="protected window"):
        run(yes=True, window=(0, 1439))
    assert len(rows(db)) == 3


def test_failure_after_commit_leaves_recoverable_prepared_batch(store, monkeypatch):
    db, put, run, _ = store
    versions(put)
    before = rows(db)
    save = core._retain_save
    def interrupted(path, raw):
        if path.name == "manifest.json" and json.loads(raw)["status"] == "completed":
            raise OSError("crash after sqlite commit")
        save(path, raw)
    monkeypatch.setattr(core, "_retain_save", interrupted)
    with pytest.raises(OSError):
        run(yes=True)
    assert len(rows(db)) == 1
    monkeypatch.setattr(core, "_retain_save", save)
    manifest = next((db.parent.parent / "state/retention").glob("*/manifest.json"))
    with pytest.raises(ValueError, match="unresolved"):
        run()
    run(restore=manifest.parent.name, yes=True)
    assert rows(db) == before


def test_host_scope_can_only_narrow_and_stale_snapshot_blocks(store):
    db, put, run, _ = store
    keys = versions(put)
    args = dict(root=db.parent.parent, registry_path=db.parent.parent / "metabolism.json",
                state_dir=db.parent.parent / "state")
    with pytest.raises(ValueError, match="stale"):
        core.retain(db, **args, yes=True, expected_ids_sha256="0" * 64)
    result = core.retain(db, **args, yes=True, eligible_ids={keys[0], keys[-1]})
    assert result["rows_deleted"] == 1
    assert {r[0] for r in rows(db)} == set(keys[1:])


def test_foreign_claim_registry_is_not_ignored_or_rewritten(store):
    db, put, run, _ = store
    versions(put)
    coord = db.parent.parent / ".coordination"
    coord.mkdir()
    registry = coord / "registry.json"
    raw = b'{"version":1,"claims":[]}'
    registry.write_bytes(raw)
    with pytest.raises(ValueError, match="host claim registry"):
        run(yes=True)
    assert registry.read_bytes() == raw and len(rows(db)) == 3
