"""Exercise a real SQLite export consumer around retention and restoration.

Everything, including deliberate corruption, runs inside TemporaryDirectory.
The consumer reads the actual latest-view; no supplied success boolean is used.
"""
from datetime import datetime, timedelta, timezone
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

from workspace_metabolism import __version__, core
from workspace_metabolism.maintenance_checks import (
    ADAPTER, ADAPTER_VERSION, assess_maintenance_tasks, capture_sqlite_export,
    check_sqlite_consumer, scope_digest,
)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _latest(state):
    return json.loads(core.journal_path(state).read_text(encoding="utf-8").splitlines()[-1])


def run_demo(*, corrupt=False):
    with TemporaryDirectory(prefix="wm-consumer-") as temporary:
        root = Path(temporary)
        db, policy, state = root / "data/app.db", root / "metabolism.json", root / "state"
        db.parent.mkdir()
        with closing(sqlite3.connect(db)) as con, con:
            con.execute("CREATE TABLE objects (id TEXT PRIMARY KEY, body TEXT, captured_at INTEGER)")
            for i in (1, 2, 3):
                con.execute("INSERT INTO objects VALUES (?,?,?)", (
                    f"version-{i}", json.dumps({"code": "demo", "month": "2026-10", "value": 7}), i))
            con.execute("CREATE VIEW latest AS SELECT 'demo' AS object_id, body FROM objects "
                        "WHERE captured_at = (SELECT MAX(captured_at) FROM objects)")
        task = {"id": "retain-example", "scope": ["data/app.db"], "policy_version": "example-1",
                "executor": {"id": "wm-retain", "version": __version__, "description": "Explicit example retention",
                             "operation_action": "retain"},
                "required_actions": ["execute"], "required_capabilities": ["sqlite_read", "sqlite_write"],
                "capability_receipt": "evidence/capability.json", "execution_receipt": "evidence/execution.json",
                "max_age_seconds": 3600}
        registration = {"id": "latest-export", "version": "example-1", "adapter": ADAPTER,
                        "adapter_version": ADAPTER_VERSION, "database": "data/app.db", "relation": "latest",
                        "id_column": "object_id", "json_column": "body", "fields": ["value"]}
        registry = {"version": 1, "ai_governance": {"default": "deny", "actions": {"execute": {"allow": True}}},
                    "maintenance_tasks": [task], "consumer_checks": [registration], "entries": [
                        {"path": "data/app.db", "grade": "G2", "cleanup": "never", "db_retain": {
                            "table": "objects", "blob_column": "body", "id_column": "id", "group_by": ["code", "month"],
                            "order_column": "captured_at", "keep": 1, "reference_paths": [], "blob_encoding": "json"}}]}
        policy.write_text(json.dumps(registry), encoding="utf-8")
        policy_sha = core.sha256_file(policy)
        binding = {"task_id": task["id"], "scope_sha256": scope_digest(task["scope"]),
                   "policy_version": task["policy_version"], "policy_sha256": policy_sha,
                   "executor_id": task["executor"]["id"], "executor_version": __version__}
        baseline = capture_sqlite_export(root, policy, "latest-export")
        core.govern(root, policy, state, "execute", paths=task["scope"], preview=True, operator="example")
        permission = _latest(state)
        # A real temporary-database writer probe, always rolled back.
        before_probe = core.sha256_file(db)
        with closing(sqlite3.connect(db)) as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute("UPDATE objects SET captured_at = captured_at WHERE id = 'version-1'")
            con.rollback()
        if core.sha256_file(db) != before_probe:
            raise RuntimeError("writer probe changed the example source")
        checked = datetime.now(timezone.utc).replace(microsecond=0)
        capability = {"schema": "wm.executor_capability.v1", "binding": binding,
                      "checked_at": checked.isoformat(), "valid_until": (checked + timedelta(hours=1)).isoformat(),
                      "permissions": [permission], "probes": [
                          {"capability": "sqlite_read", "status": "passed", "method": "registered_sqlite_export",
                           "observation_sha256": baseline["input_manifest_sha256"]},
                          {"capability": "sqlite_write", "status": "passed", "method": "sqlite_immediate_rollback",
                           "observation_sha256": _digest({"before": before_probe, "after": core.sha256_file(db)})}]}
        evidence = root / "evidence"
        evidence.mkdir()
        (evidence / "capability.json").write_text(json.dumps(capability), encoding="utf-8")
        started = datetime.now(timezone.utc).replace(microsecond=0)
        retained = core.retain(db, root=root, registry_path=policy, state_dir=state, yes=True, operator="example")
        operation = _latest(state)
        execution = {"schema": "wm.maintenance_execution.v1",
                     "binding": {**binding, "cycle_id": retained["run_id"],
                                 "object_manifest_sha256": baseline["input_manifest_sha256"]},
                     "started_at": started.isoformat(), "finished_at": operation["ts"],
                     "operation_receipt": operation}
        (evidence / "execution.json").write_text(json.dumps(execution), encoding="utf-8")
        if corrupt:
            with closing(sqlite3.connect(db)) as con, con:
                con.execute("UPDATE objects SET body = ? WHERE id = 'version-3'", (
                    json.dumps({"code": "demo", "month": "2026-10", "value": 99}),))
        after = check_sqlite_consumer(root, policy, "latest-export", baseline=baseline, operation_receipt=operation)
        core.retain(db, root=root, registry_path=policy, state_dir=state,
                    restore=retained["run_id"], yes=True, operator="example")
        restored = check_sqlite_consumer(root, policy, "latest-export", baseline=baseline,
                                        operation_receipt=operation, recovery_receipt=_latest(state))
        readiness = assess_maintenance_tasks(root, registry, policy_sha256=policy_sha)
        return {"mode": "temporary_example", "production_recovery_verified": False,
                "rows_deleted": retained["rows_deleted"], "after": after, "recovery": restored,
                "maintenance": readiness, "deliberate_corruption": corrupt}


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2, ensure_ascii=False))
