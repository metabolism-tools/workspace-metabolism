"""Consumer checks perform actual SQLite work and compare concrete exports."""
import hashlib
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3

import pytest

from workspace_metabolism import core
from workspace_metabolism.maintenance_checks import capture_sqlite_export, check_sqlite_consumer, main
from workspace_metabolism import maintenance_checks


@pytest.fixture
def consumer(tmp_path):
    db = tmp_path / "data/app.db"
    db.parent.mkdir()
    with closing(sqlite3.connect(db)) as con, con:
        con.execute("CREATE TABLE samples (id TEXT PRIMARY KEY, payload TEXT)")
        con.execute("INSERT INTO samples VALUES (?, ?)", ("sample-1", json.dumps({"metric": 7, "scratch": [1, 2]})))
    policy = tmp_path / "metabolism.json"
    registry = {"version": 1, "entries": [{"path": "data/app.db", "grade": "G2", "cleanup": "never",
                                          "db_slim": {"table": "samples", "blob_column": "payload", "strip_keys": ["scratch"]}}],
                "consumer_checks": [{"id": "export", "version": "1", "adapter": "sqlite_json_export_v1", "adapter_version": "1",
                                     "database": "data/app.db", "relation": "samples", "id_column": "id",
                                     "json_column": "payload", "fields": ["metric"]}]}
    policy.write_text(json.dumps(registry), encoding="utf-8")
    baseline = capture_sqlite_export(tmp_path, policy, "export")
    core.slim(db, policy, tmp_path / "state", yes=True)
    operation = json.loads(core.journal_path(tmp_path / "state").read_text(encoding="utf-8").splitlines()[-1])
    return tmp_path, policy, db, registry, baseline, operation


def check(consumer, **kwargs):
    root, policy, _, _, baseline, operation = consumer
    return check_sqlite_consumer(root, policy, "export", baseline=baseline, operation_receipt=operation, **kwargs)


def rehash(record):
    record["hash"] = hashlib.sha256(json.dumps({k: v for k, v in record.items() if k != "hash"},
                                             ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def test_real_export_matches_frozen_output_without_mutating_database(consumer):
    db = consumer[2]
    before = db.read_bytes()
    result = check(consumer)
    assert result["passed"] is True
    assert result["consumption"]["mode"] == "real_workflow"
    assert result["rows_consumed"] == 1
    assert result["operation_receipt_sha256"] == consumer[5]["hash"]
    assert result["policy_sha256"] == core.sha256_file(consumer[1])
    assert result["consumer_command_version"] == "1"
    # The maintenance changed scratch content; the actual reader derives a new input digest.
    assert result["object_manifest_sha256"] != consumer[4]["input_manifest_sha256"]
    assert result["consumption"]["output_sha256"] == consumer[4]["output_sha256"]
    assert db.read_bytes() == before


def test_real_downstream_change_is_rejected_despite_reported_success(consumer):
    with closing(sqlite3.connect(consumer[2])) as con, con:
        con.execute("UPDATE samples SET payload = ?", (json.dumps({"metric": 99}),))
    before = consumer[2].read_bytes()
    result = check(consumer)
    assert result["passed"] is False
    assert result["result"] == "output_changed"
    assert result["consumption"]["accepted"] is False
    assert consumer[2].read_bytes() == before


def test_ok_boolean_cannot_replace_baseline_or_operation_receipt(consumer):
    with pytest.raises(ValueError, match="baseline_binding_invalid"):
        check_sqlite_consumer(consumer[0], consumer[1], "export", baseline={"ok": True}, operation_receipt=consumer[5])
    with pytest.raises(ValueError, match="operation_receipt_missing"):
        check_sqlite_consumer(consumer[0], consumer[1], "export", baseline=consumer[4], operation_receipt={"ok": True})


@pytest.mark.parametrize("field,value,reason", [
    ("registry_sha256", "b" * 64, "operation_policy_mismatch"),
    ("db", "C:/wrong/app.db", "operation_scope_mismatch"),
    ("status", "dry_run", "operation_not_completed"),
])
def test_wrong_operation_or_scope_cannot_bind(consumer, field, value, reason):
    consumer[5][field] = value
    rehash(consumer[5])
    with pytest.raises(ValueError, match=reason):
        check(consumer)


@pytest.mark.parametrize("field", ["consumer_version", "scope_sha256", "policy_sha256", "output_sha256"])
def test_wrong_baseline_version_scope_or_output_digest_rejected(consumer, field):
    consumer[4][field] = "wrong"
    with pytest.raises(ValueError, match="baseline_binding_invalid"):
        check(consumer)


def test_arbitrary_sql_and_unregistered_commands_are_not_executed(consumer):
    root, policy, db, registry, *_ = consumer
    before = db.read_bytes()
    with pytest.raises(ValueError, match="consumer_not_registered"):
        capture_sqlite_export(root, policy, "shell rm anything")
    registry["consumer_checks"][0]["relation"] = 'samples"; DROP TABLE samples;--'
    policy.write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid_consumer_identifier"):
        capture_sqlite_export(root, policy, "export")
    assert db.read_bytes() == before


def test_missing_database_is_never_created(consumer):
    root, policy, _, registry, *_ = consumer
    registry["consumer_checks"][0]["database"] = "data/missing.db"
    policy.write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(sqlite3.Error):
        capture_sqlite_export(root, policy, "export")
    assert not (root / "data/missing.db").exists()


def test_registered_slow_view_is_bounded_before_first_export_row(consumer, monkeypatch):
    root, policy, db, registry, *_ = consumer
    with closing(sqlite3.connect(db)) as con, con:
        con.execute("CREATE VIEW many_rows AS WITH RECURSIVE r(id) AS "
                    "(SELECT 1 UNION ALL SELECT id+1 FROM r WHERE id<100000000) "
                    "SELECT id, '{\"metric\":7}' AS payload FROM r")
    registry["consumer_checks"][0]["relation"] = "many_rows"
    policy.write_text(json.dumps(registry), encoding="utf-8")
    before = db.read_bytes()
    ticks = iter([0, 31])
    monkeypatch.setattr(maintenance_checks, "monotonic", lambda: next(ticks, 31))
    with pytest.raises(ValueError, match="consumer_time_budget"):
        capture_sqlite_export(root, policy, "export")
    assert db.read_bytes() == before


@pytest.mark.parametrize("field,value", [("registry_sha256", "b" * 64), ("database", "C:/wrong/app.db"),
                                      ("run_id", "wrong-cycle")])
def test_recovery_of_another_object_or_policy_cannot_close_original(consumer, field, value):
    operation = consumer[5]
    operation["run_id"] = "example-cycle"
    rehash(operation)
    recovery = {"seq": 2, "prev_hash": operation["hash"], "action": "retain_restore", "ts": operation["ts"],
                "database": str(consumer[2]), "registry_sha256": operation["registry_sha256"],
                "run_id": "example-cycle", "status": "restored", "rows_restored": 1}
    recovery[field] = value
    rehash(recovery)
    with pytest.raises(ValueError, match="recovery_binding_invalid"):
        check(consumer, recovery_receipt=recovery)


def test_failed_cli_returns_fixed_reason_without_private_data(consumer, capsys):
    baseline, operation = consumer[0] / "baseline.json", consumer[0] / "operation.json"
    baseline.write_text("private-secret", encoding="utf-8")
    operation.write_text(json.dumps(consumer[5]), encoding="utf-8")
    assert main(["check", "--root", str(consumer[0]), "--policy", str(consumer[1]), "--consumer", "export",
                 "--baseline", str(baseline), "--operation-receipt", str(operation)]) == 2
    output = capsys.readouterr().out
    assert "private-secret" not in output


def test_temporary_real_retention_and_restoration_preserve_consumer_output():
    path = Path(__file__).parents[1] / "examples/maintenance_consumer_demo.py"
    spec = importlib.util.spec_from_file_location("consumer_demo", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.run_demo()
    assert result["rows_deleted"] == 2
    assert result["after"]["passed"] is True
    assert result["recovery"]["passed"] is True
    assert result["recovery"]["recovery_receipt_sha256"] is not None
    assert result["after"]["operation_receipt_sha256"] == result["recovery"]["operation_receipt_sha256"]
    assert result["maintenance"]["all_recent"] is True
    assert result["production_recovery_verified"] is False


def test_recovery_receipt_does_not_hide_wrong_downstream_output():
    path = Path(__file__).parents[1] / "examples/maintenance_consumer_demo.py"
    spec = importlib.util.spec_from_file_location("consumer_bad_demo", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.run_demo(corrupt=True)
    assert result["after"]["passed"] is False
    assert result["recovery"]["passed"] is False
