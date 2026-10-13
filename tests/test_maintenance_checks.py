"""Evidence must describe actual execution; doctor must not create it."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import pytest

from workspace_metabolism import core
from workspace_metabolism.maintenance_checks import assess_maintenance_tasks, scope_digest

NOW = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)


def record(action, **fields):
    value = {"seq": 1, "ts": (NOW - timedelta(minutes=5)).isoformat(), "action": action,
             "prev_hash": "GENESIS", "registry_sha256": "a" * 64, **fields}
    value["hash"] = hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return value


@pytest.fixture
def evidence(tmp_path):
    task = {"id": "history", "scope": ["data/app.db"], "policy_version": "policy-1",
            "executor": {"id": "scheduled-slim", "version": "1", "description": "Existing maintenance executor",
                         "operation_action": "slim"},
            "required_actions": ["execute"], "required_capabilities": ["sqlite_write"],
            "capability_receipt": "capability.json", "execution_receipt": "execution.json", "max_age_seconds": 3600}
    binding = {"task_id": "history", "scope_sha256": scope_digest(task["scope"]), "policy_version": "policy-1",
               "policy_sha256": "a" * 64, "executor_id": "scheduled-slim", "executor_version": "1"}
    capability = {"schema": "wm.executor_capability.v1", "binding": binding,
                  "checked_at": (NOW - timedelta(minutes=4)).isoformat(), "valid_until": (NOW + timedelta(hours=1)).isoformat(),
                  "permissions": [record("govern", decision="allow", governed_action="execute", paths=["data/app.db"])],
                  "probes": [{"capability": "sqlite_write", "status": "passed", "method": "sqlite_immediate_rollback",
                              "observation_sha256": "b" * 64}]}
    operation = record("slim", db=str(tmp_path / "data/app.db"), status="ok", rows_stripped=1)
    operation["ts"] = (NOW - timedelta(minutes=1)).isoformat()
    operation["hash"] = hashlib.sha256(json.dumps({k: v for k, v in operation.items() if k != "hash"},
                                                  ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    execution = {"schema": "wm.maintenance_execution.v1",
                 "binding": {**binding, "cycle_id": "cycle-1", "object_manifest_sha256": "c" * 64},
                 "started_at": (NOW - timedelta(minutes=2)).isoformat(), "finished_at": operation["ts"],
                 "operation_receipt": operation}

    def save(cap=capability, exe=execution):
        (tmp_path / "capability.json").write_text(json.dumps(cap), encoding="utf-8")
        (tmp_path / "execution.json").write_text(json.dumps(exe), encoding="utf-8")

    save()
    return tmp_path, {"maintenance_tasks": [task]}, capability, execution, save


def assess(evidence):
    root, registry, *_ = evidence
    return assess_maintenance_tasks(root, registry, policy_sha256="a" * 64, now=NOW)


def test_registered_recent_execution_is_reported_and_reader_is_readonly(evidence, monkeypatch):
    root, _, _, _, _ = evidence
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    monkeypatch.setattr(core, "journal_append", lambda *a, **kw: pytest.fail("doctor wrote a receipt"))
    result = assess(evidence)
    assert result["all_recent"] is True
    assert result["tasks"][0]["state"] == "recent_execution_reported"
    assert result["authorizes_execution"] is False
    assert result["trust"] == "local_reported_not_authenticated"
    assert {p.name: p.read_bytes() for p in root.iterdir()} == before


@pytest.mark.parametrize("filename,state", [("capability.json", "capability_evidence_missing"),
                                           ("execution.json", "execution_missing")])
def test_configuration_does_not_replace_missing_receipts(evidence, filename, state):
    (evidence[0] / filename).unlink()
    assert assess(evidence)["tasks"][0]["state"] == state


def test_missing_executor_is_explicit(evidence):
    del evidence[1]["maintenance_tasks"][0]["executor"]
    assert assess(evidence)["tasks"][0]["state"] == "executor_missing"


@pytest.mark.parametrize("field,value,state", [
    ("scope_sha256", "d" * 64, "scope_mismatch"),
    ("policy_sha256", "d" * 64, "policy_mismatch"),
    ("executor_version", "other", "executor_mismatch"),
    ("task_id", "other", "task_mismatch"),
])
def test_wrong_binding_cannot_reuse_execution(evidence, field, value, state):
    evidence[3]["binding"][field] = value
    evidence[4]()
    assert assess(evidence)["tasks"][0]["state"] == state


def test_capability_boolean_without_permission_or_probe_receipts_is_missing(evidence):
    evidence[2]["permissions"] = []
    evidence[2]["ok"] = True
    evidence[4]()
    assert assess(evidence)["tasks"][0]["state"] == "permission_evidence_missing"
    evidence[2]["permissions"] = [record("govern", decision="allow", governed_action="execute", paths=["data/app.db"])]
    evidence[2]["probes"] = []
    evidence[4]()
    assert assess(evidence)["tasks"][0]["state"] == "capability_evidence_missing"


@pytest.mark.parametrize("status,state", [("failed", "execution_failed"), ("dry_run", "not_executed")])
def test_real_failed_or_preview_receipt_cannot_be_success(evidence, status, state):
    operation = evidence[3]["operation_receipt"]
    operation["status"] = status
    operation["hash"] = hashlib.sha256(json.dumps({k: v for k, v in operation.items() if k != "hash"},
                                                  ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    evidence[4]()
    result = assess(evidence)
    assert result["all_recent"] is False
    assert result["tasks"][0]["state"] == state


def test_expired_execution_is_not_recent(evidence):
    result = assess_maintenance_tasks(evidence[0], evidence[1], policy_sha256="a" * 64,
                                     now=NOW + timedelta(minutes=60))
    assert result["tasks"][0]["state"] == "execution_stale"
    result = assess_maintenance_tasks(evidence[0], evidence[1], policy_sha256="a" * 64,
                                     now=NOW + timedelta(hours=2))
    assert result["tasks"][0]["state"] == "capability_stale"


def test_damaged_or_oversized_receipt_fails_without_path_leaks(evidence):
    path = evidence[0] / "execution.json"
    path.write_text("private-secret", encoding="utf-8")
    result = assess(evidence)
    assert result["all_recent"] is False
    assert "private-secret" not in json.dumps(result)
    path.write_bytes(b"x" * (256 * 1024 + 1))
    assert assess(evidence)["tasks"][0]["state"] == "evidence_over_budget"


def test_receipt_paths_cannot_escape_workspace(evidence, tmp_path):
    evidence[1]["maintenance_tasks"][0]["execution_receipt"] = "../outside.json"
    assert assess(evidence)["tasks"][0]["state"] == "relative_path_required"


def test_wrapper_scope_cannot_replace_actual_operation_scope(evidence):
    operation = evidence[3]["operation_receipt"]
    del operation["db"]
    operation["hash"] = hashlib.sha256(json.dumps({k: v for k, v in operation.items() if k != "hash"},
                                                  ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    evidence[4]()
    assert assess(evidence)["tasks"][0]["state"] == "scope_evidence_missing"


def test_actual_paths_can_supply_operation_scope(evidence):
    operation = evidence[3]["operation_receipt"]
    del operation["db"]
    operation["paths"] = ["data/app.db"]
    operation["hash"] = hashlib.sha256(json.dumps({k: v for k, v in operation.items() if k != "hash"},
                                                  ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    evidence[4]()
    assert assess(evidence)["tasks"][0]["state"] == "recent_execution_reported"


def test_old_policy_without_registration_is_compatible(tmp_path):
    assert assess_maintenance_tasks(tmp_path, {}, policy_sha256="a" * 64, now=NOW)["state"] == "not_declared"


def test_doctor_accepts_recent_no_change_without_claiming_maintenance(evidence, monkeypatch):
    from workspace_metabolism import maintenance_checks
    root, registry, capability, execution, save = evidence
    registry.update(version=1, entries=[])
    registry["maintenance_tasks"][0]["executor"]["operation_action"] = "retain"
    policy = root / "metabolism.json"
    policy.write_text(json.dumps(registry), encoding="utf-8")
    policy_hash = core.sha256_file(policy)
    for wrapper in (capability, execution):
        wrapper["binding"]["policy_sha256"] = policy_hash
    records = capability["permissions"] + [execution["operation_receipt"]]
    operation = records[-1]
    operation.update(action="retain", status="no_action_due", rows_deleted=0)
    for record in records:
        record["registry_sha256"] = policy_hash
        record["hash"] = hashlib.sha256(json.dumps({k: v for k, v in record.items() if k != "hash"},
                                                  ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    save()
    monkeypatch.setattr(maintenance_checks, "_now", lambda value=None: NOW)
    result = core.doctor(root, policy, root / "state")
    assert result["maintenance"]["all_recent"] is True
    assert result["maintenance"]["tasks"][0]["state"] == "no_change_reported"


def test_failed_capability_or_denied_permission_is_explicit(evidence):
    evidence[2]["probes"][0]["status"] = "failed"
    evidence[4]()
    assert assess(evidence)["tasks"][0]["state"] == "capability_failed"
    evidence[2]["permissions"] = [record("govern", decision="deny", governed_action="execute", paths=["data/app.db"])]
    evidence[4]()
    assert assess(evidence)["tasks"][0]["state"] == "permission_denied"


def test_schema_is_valid_json_and_declares_both_explicit_interfaces():
    path = Path(__file__).parents[1] / "schema/metabolism.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert "maintenance_tasks" in schema["properties"]
    assert schema["properties"]["consumer_checks"]["items"]["properties"]["adapter"]["const"] == "sqlite_json_export_v1"
