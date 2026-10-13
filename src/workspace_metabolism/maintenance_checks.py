"""Read-only maintenance evidence checks and an explicitly called SQLite consumer.

Local receipt hashes establish consistency, not the identity of their producer.
The doctor API never runs a scheduler, probe, SQL query or external command.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sqlite3
from time import monotonic

MAX_RECEIPT_BYTES = 256 * 1024
MAX_EXPORT_BYTES = 32 * 1024 * 1024
MAX_ROWS = 100_000
MAX_CONSUMER_SECONDS = 30
ADAPTER = "sqlite_json_export_v1"
ADAPTER_VERSION = "1"
HEX = re.compile(r"[0-9a-f]{64}\Z")
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
OPERATIONS = {"clean", "slim", "retain", "rollback", "retain_restore", "purge"}


def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _stamp(value) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp_missing")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("timezone_required")
    return result


def _now(value=None) -> datetime:
    # WM's journal uses seconds. Do not imply finer event ordering than it records.
    result = value or datetime.now(timezone.utc).replace(microsecond=0)
    result = _stamp(result) if isinstance(result, str) else result
    if not isinstance(result, datetime) or result.tzinfo is None:
        raise ValueError("timezone_required")
    return result


def _relative(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("relative_path_required")
    value = value.replace("\\", "/")
    path = PurePosixPath(value)
    if (path.is_absolute() or PureWindowsPath(value).drive or path == PurePosixPath(".")
            or ".." in path.parts):
        raise ValueError("relative_path_required")
    return path.as_posix()


def _inside(root: Path, value: str) -> Path:
    root = root.resolve()
    path = root / _relative(value)
    if not path.resolve().is_relative_to(root):
        raise ValueError("evidence_outside_workspace")
    return path


def scope_digest(paths: list[str]) -> str:
    if not isinstance(paths, list) or not paths or len(paths) > 128:
        raise ValueError("invalid_scope")
    normalized = [_relative(path) for path in paths]
    if len(set(normalized)) != len(normalized):
        raise ValueError("duplicate_scope")
    return _digest({"paths": sorted(normalized)})


def _read(path: Path, limit=MAX_RECEIPT_BYTES):
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("evidence_over_budget")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("evidence_not_object")
    return value, hashlib.sha256(raw).hexdigest()


def _journal(record: dict) -> str:
    if not isinstance(record, dict) or not HEX.fullmatch(str(record.get("hash", ""))):
        raise ValueError("operation_receipt_missing")
    canonical = json.dumps({k: v for k, v in record.items() if k != "hash"},
                           ensure_ascii=False, sort_keys=True, allow_nan=False)
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != record["hash"]:
        raise ValueError("receipt_hash_mismatch")
    if type(record.get("seq")) is not int or record["seq"] < 1:
        raise ValueError("receipt_sequence_invalid")
    if record.get("prev_hash") != "GENESIS" and not HEX.fullmatch(str(record.get("prev_hash", ""))):
        raise ValueError("receipt_chain_link_missing")
    _stamp(record.get("ts"))
    return record["hash"]


def _operation_state(record: dict) -> str:
    action, status = record.get("action"), record.get("status")
    if action not in OPERATIONS:
        raise ValueError("unsupported_operation")
    if status in {"failed", "error", "incomplete"}:
        return "execution_failed"
    if status in {"preview", "dry_run", "not_run"}:
        return "not_executed"
    if action == "slim" and status == "ok":
        return "recent_execution_reported"
    if action == "clean" and status == "completed":
        return "recent_execution_reported"
    if action == "retain" and status in {"retained", "no_action_due"}:
        return "recent_execution_reported" if status == "retained" else "no_change_reported"
    if action in {"rollback", "retain_restore"}:
        amount = record.get("restored", record.get("rows_restored"))
        if type(amount) is int and amount >= 0:
            return "recent_execution_reported" if amount else "no_change_reported"
    if action == "purge" and isinstance(record.get("batches"), list):
        return "recent_execution_reported" if record["batches"] else "no_change_reported"
    raise ValueError("execution_outcome_missing")


def _operation_scope(root: Path, record: dict) -> str:
    database = record.get("db", record.get("database"))
    if database is not None:
        if not isinstance(database, str):
            raise ValueError("scope_mismatch")
        path = Path(database).resolve()
        try:
            relative = path.relative_to(root.resolve()).as_posix()
        except ValueError:
            raise ValueError("scope_mismatch") from None
        return scope_digest([relative])
    if isinstance(record.get("paths"), list) and record["paths"]:
        return scope_digest(record["paths"])
    raise ValueError("scope_evidence_missing")


def _task_binding(task: dict, policy_sha256: str) -> dict:
    executor = task.get("executor")
    if (not isinstance(executor, dict) or any(not isinstance(executor.get(k), str)
            or not executor[k].strip() for k in ("id", "version", "description"))):
        raise ValueError("executor_missing")
    if executor.get("operation_action") not in OPERATIONS:
        raise ValueError("executor_operation_missing")
    if (not isinstance(task.get("id"), str) or not task["id"].strip()
            or not isinstance(task.get("policy_version"), str) or not task["policy_version"].strip()
            or not HEX.fullmatch(policy_sha256)):
        raise ValueError("invalid_declaration")
    return {"task_id": task["id"], "scope_sha256": scope_digest(task.get("scope")),
            "policy_version": task["policy_version"], "policy_sha256": policy_sha256,
            "executor_id": executor["id"], "executor_version": executor["version"]}


def _match_binding(receipt: dict, expected: dict):
    binding = receipt.get("binding")
    if not isinstance(binding, dict):
        raise ValueError("binding_missing")
    for key, value in expected.items():
        if binding.get(key) != value:
            raise ValueError({"scope_sha256": "scope_mismatch", "task_id": "task_mismatch",
                              "policy_sha256": "policy_mismatch", "policy_version": "policy_mismatch"}
                             .get(key, "executor_mismatch"))


def _assess_task(root: Path, task: dict, policy_sha256: str, now: datetime) -> dict:
    result = {"task_id": task.get("id") if isinstance(task, dict) else None,
              "state": "invalid_declaration", "capability_evidence_sha256": None,
              "execution_evidence_sha256": None, "operation_receipt_sha256": None}
    try:
        expected = _task_binding(task, policy_sha256)
        result["scope_sha256"] = expected["scope_sha256"]
        age = task.get("max_age_seconds")
        if type(age) is not int or not 1 <= age <= 366 * 86400:
            raise ValueError("invalid_max_age")
        for key in ("required_actions", "required_capabilities"):
            items = task.get(key)
            if (not isinstance(items, list) or not items or len(items) > 32
                    or any(not isinstance(item, str) or not item.strip() for item in items)
                    or len(set(items)) != len(items)):
                raise ValueError("invalid_" + key)
        if set(task["required_actions"]) - {"read", "write", "execute", "delete", "network"}:
            raise ValueError("invalid_required_actions")
        try:
            capability, digest = _read(_inside(root, task.get("capability_receipt")))
        except FileNotFoundError:
            raise ValueError("capability_evidence_missing") from None
        result["capability_evidence_sha256"] = digest
        if capability.get("schema") != "wm.executor_capability.v1":
            raise ValueError("capability_format_invalid")
        _match_binding(capability, expected)
        checked, valid = _stamp(capability.get("checked_at")), _stamp(capability.get("valid_until"))
        if checked > now or valid < checked:
            raise ValueError("capability_time_invalid")
        if now > valid:
            raise ValueError("capability_stale")
        permissions = capability.get("permissions")
        if not isinstance(permissions, list) or not permissions or len(permissions) > 32:
            raise ValueError("permission_evidence_missing")
        allowed = set()
        for permission in permissions:
            _journal(permission)
            if (permission.get("action") != "govern" or permission.get("registry_sha256") != policy_sha256
                    or scope_digest(permission.get("paths")) != expected["scope_sha256"]):
                raise ValueError("permission_binding_mismatch")
            if _stamp(permission["ts"]) > checked:
                raise ValueError("permission_time_invalid")
            if permission.get("decision") != "allow":
                raise ValueError("permission_denied")
            allowed.add(permission.get("governed_action"))
        if not set(task["required_actions"]).issubset(allowed):
            raise ValueError("permission_evidence_missing")
        probes = capability.get("probes")
        if not isinstance(probes, list) or len(probes) > 32:
            raise ValueError("capability_evidence_missing")
        for name in task["required_capabilities"]:
            matches = [p for p in probes if isinstance(p, dict) and p.get("capability") == name]
            if len(matches) != 1:
                raise ValueError("capability_evidence_missing")
            probe = matches[0]
            if probe.get("status") != "passed":
                raise ValueError("capability_failed")
            if (not isinstance(probe.get("method"), str) or not probe["method"].strip()
                    or not HEX.fullmatch(str(probe.get("observation_sha256", "")))):
                raise ValueError("capability_evidence_missing")
        try:
            execution, digest = _read(_inside(root, task.get("execution_receipt")))
        except FileNotFoundError:
            raise ValueError("execution_missing") from None
        result["execution_evidence_sha256"] = digest
        if execution.get("schema") != "wm.maintenance_execution.v1":
            raise ValueError("execution_format_invalid")
        _match_binding(execution, expected)
        binding = execution["binding"]
        if (not isinstance(binding.get("cycle_id"), str) or not binding["cycle_id"].strip()
                or not HEX.fullmatch(str(binding.get("object_manifest_sha256", "")))):
            raise ValueError("execution_object_binding_missing")
        operation = execution.get("operation_receipt")
        result["operation_receipt_sha256"] = _journal(operation)
        if operation.get("action") != task["executor"]["operation_action"]:
            raise ValueError("operation_mismatch")
        if operation.get("registry_sha256") != policy_sha256:
            raise ValueError("policy_mismatch")
        if _operation_scope(root, operation) != expected["scope_sha256"]:
            raise ValueError("scope_mismatch")
        started, finished = _stamp(execution.get("started_at")), _stamp(execution.get("finished_at"))
        if started > finished or finished > now or _stamp(operation["ts"]) > finished:
            raise ValueError("execution_time_invalid")
        if checked > started:
            raise ValueError("capability_time_invalid")
        result["last_execution_at"] = finished.isoformat()
        state = _operation_state(operation)
        if state == "execution_failed":
            raise ValueError(state)
        if (now - finished).total_seconds() > age:
            raise ValueError("execution_stale")
        result["state"] = state
    except (ValueError, TypeError, KeyError, AttributeError, OSError, RecursionError) as exc:
        reason = str(exc) if isinstance(exc, ValueError) else "evidence_invalid"
        # Only fixed short reason codes leave the reader; paths and business data stay local.
        result["state"] = reason if re.fullmatch(r"[a-z_]{1,64}", reason) else "evidence_invalid"
    return result


def assess_maintenance_tasks(root: Path, registry: dict, *, policy_sha256: str, now=None) -> dict:
    """Check declared executors and supplied receipts without producing evidence."""
    now = _now(now)
    tasks = registry.get("maintenance_tasks", [])
    result = {"schema": "wm.maintenance_readiness.v1", "mode": "read_only",
              "assessed_at": now.isoformat(), "trust": "local_reported_not_authenticated",
              "authorizes_execution": False, "tasks": [], "all_recent": False}
    if not isinstance(tasks, list) or len(tasks) > 128:
        result["state"] = "invalid_declaration"
        return result
    identifiers = [t.get("id") for t in tasks if isinstance(t, dict)]
    if len(identifiers) != len(tasks) or len(set(str(i) for i in identifiers)) != len(tasks):
        result["state"] = "invalid_declaration"
        return result
    result["tasks"] = [_assess_task(root, task, policy_sha256, now) for task in tasks]
    result["state"] = "checked" if tasks else "not_declared"
    result["all_recent"] = bool(tasks) and all(t["state"] in {"recent_execution_reported", "no_change_reported"}
                                             for t in result["tasks"])
    return result


def _consumer(registry: dict, consumer_id: str) -> dict:
    consumers = registry.get("consumer_checks", [])
    if not isinstance(consumers, list) or len(consumers) > 128:
        raise ValueError("invalid_consumer_registration")
    matches = [c for c in consumers if isinstance(c, dict) and c.get("id") == consumer_id]
    if len(matches) != 1:
        raise ValueError("consumer_not_registered")
    consumer = matches[0]
    if (consumer.get("adapter") != ADAPTER or consumer.get("adapter_version") != ADAPTER_VERSION
            or not isinstance(consumer.get("version"), str) or not consumer["version"].strip()):
        raise ValueError("unsupported_consumer_adapter")
    for name in ("relation", "id_column", "json_column"):
        if not IDENTIFIER.fullmatch(str(consumer.get(name, ""))):
            raise ValueError("invalid_consumer_identifier")
    fields = consumer.get("fields")
    if (not isinstance(fields, list) or not fields or len(fields) > 32
            or any(not isinstance(f, str) or not f or "." in f for f in fields)
            or len(set(fields)) != len(fields)):
        raise ValueError("invalid_consumer_fields")
    return consumer


def capture_sqlite_export(root: Path, registry_path: Path, consumer_id: str, *, now=None) -> dict:
    """Explicitly consume a registered SQLite relation into a deterministic export."""
    from .core import load_registry, sha256_file
    from .sqlite_guard import open_existing_sqlite

    registry = load_registry(registry_path)
    policy_sha = sha256_file(registry_path)
    consumer = _consumer(registry, consumer_id)
    path = _inside(root, consumer.get("database"))
    con = open_existing_sqlite(path)
    deadline = monotonic() + MAX_CONSUMER_SECONDS
    con.set_progress_handler(lambda: int(monotonic() >= deadline), 1000)
    con.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_EXPORT_BYTES)
    rows, manifest, bytes_read = [], [], 0
    try:
        con.execute("BEGIN")
        columns = {row[1] for row in con.execute(f'PRAGMA table_info("{consumer["relation"]}")')}
        if not {consumer["id_column"], consumer["json_column"]}.issubset(columns):
            raise ValueError("consumer_schema_mismatch")
        query = (f'SELECT "{consumer["id_column"]}", "{consumer["json_column"]}" '
                 f'FROM "{consumer["relation"]}" ORDER BY "{consumer["id_column"]}"')
        previous = set()
        for identity, raw in con.execute(query):
            if len(rows) >= MAX_ROWS:
                raise ValueError("consumer_row_budget")
            if not isinstance(identity, (str, int)) or isinstance(identity, bool) or identity in previous:
                raise ValueError("consumer_identity_invalid")
            previous.add(identity)
            if not isinstance(raw, (str, bytes)):
                raise ValueError("consumer_json_invalid")
            raw_bytes = raw.encode("utf-8") if isinstance(raw, str) else raw
            bytes_read += len(raw_bytes)
            if bytes_read > MAX_EXPORT_BYTES:
                raise ValueError("consumer_byte_budget")
            obj = json.loads(raw)
            if not isinstance(obj, dict) or not all(field in obj for field in consumer["fields"]):
                raise ValueError("consumer_field_missing")
            rows.append({"id": identity, "values": {field: obj[field] for field in consumer["fields"]}})
            manifest.append({"id": identity, "content_sha256": hashlib.sha256(raw_bytes).hexdigest()})
    except sqlite3.OperationalError:
        if monotonic() >= deadline:
            raise ValueError("consumer_time_budget") from None
        raise
    finally:
        con.close()
    if sha256_file(registry_path) != policy_sha:
        raise ValueError("policy_changed_during_consumer")
    if not rows:
        raise ValueError("consumer_empty")
    output = {"rows": rows}
    return {"schema": "wm.sqlite_export.v1", "consumer_id": consumer_id,
            "consumer_version": consumer["version"], "adapter": ADAPTER,
            "adapter_version": ADAPTER_VERSION, "policy_sha256": policy_sha,
            "policy_version": "sha256:" + policy_sha, "scope_sha256": scope_digest([consumer["database"]]),
            "captured_at": _now(now).isoformat(), "input_manifest_sha256": _digest(manifest),
            "output": output, "output_sha256": _digest(output), "rows_consumed": len(rows)}


def check_sqlite_consumer(root: Path, registry_path: Path, consumer_id: str, *, baseline: dict,
                          operation_receipt: dict, recovery_receipt: dict | None = None, now=None) -> dict:
    """Read actual data and compare with a frozen export; never accept a caller's ok flag."""
    from . import __version__
    from .core import load_registry, sha256_file

    started = _now(now)
    operation_hash = _journal(operation_receipt)
    if _operation_state(operation_receipt) != "recent_execution_reported":
        raise ValueError("operation_not_completed")
    registry = load_registry(registry_path)
    consumer = _consumer(registry, consumer_id)
    policy_sha = sha256_file(registry_path)
    scope = scope_digest([consumer["database"]])
    if operation_receipt.get("registry_sha256") != policy_sha:
        raise ValueError("operation_policy_mismatch")
    database = operation_receipt.get("db", operation_receipt.get("database"))
    if database is None or Path(database).resolve() != _inside(root, consumer["database"]).resolve():
        raise ValueError("operation_scope_mismatch")
    if (not isinstance(baseline, dict) or baseline.get("schema") != "wm.sqlite_export.v1"
            or baseline.get("consumer_id") != consumer_id or baseline.get("consumer_version") != consumer["version"]
            or baseline.get("adapter_version") != ADAPTER_VERSION or baseline.get("policy_sha256") != policy_sha
            or baseline.get("scope_sha256") != scope
            or not isinstance(baseline.get("output"), dict)
            or not isinstance(baseline["output"].get("rows"), list) or not baseline["output"]["rows"]
            or baseline.get("output_sha256") != _digest(baseline["output"])):
        raise ValueError("baseline_binding_invalid")
    finished = _stamp(operation_receipt["ts"])
    if not (_stamp(baseline.get("captured_at")) <= finished <= started):
        raise ValueError("consumer_time_mismatch")
    recovery_hash = None
    if recovery_receipt is not None:
        recovery_hash = _journal(recovery_receipt)
        try:
            recovery_scope = _operation_scope(root, recovery_receipt)
        except ValueError:
            raise ValueError("recovery_binding_invalid") from None
        if (recovery_receipt.get("action") not in {"rollback", "retain_restore"}
                or _operation_state(recovery_receipt) != "recent_execution_reported"
                or recovery_receipt.get("registry_sha256") != policy_sha
                or recovery_scope != scope
                or not isinstance(operation_receipt.get("run_id"), str) or not operation_receipt["run_id"]
                or recovery_receipt.get("run_id") != operation_receipt.get("run_id")
                or not (finished <= _stamp(recovery_receipt["ts"]) <= started)):
            raise ValueError("recovery_binding_invalid")
    actual = capture_sqlite_export(root, registry_path, consumer_id, now=started)
    checked_at = _now() if now is None else started
    accepted = actual["output_sha256"] == baseline["output_sha256"]
    cycle = operation_receipt.get("run_id", operation_receipt.get("decision_id", operation_hash))
    binding = {"cycle_id": cycle, "scope_sha256": scope, "policy_version": "sha256:" + policy_sha,
               "executor_version": __version__, "consumer_version": consumer["version"]}
    report = {"schema": "wm.consumer_check.v1", "name": "recovery" if recovery_hash else "consumer",
            "binding": binding, "policy_sha256": policy_sha,
            "operation_receipt_sha256": operation_hash, "recovery_receipt_sha256": recovery_hash,
            "object_manifest_sha256": actual["input_manifest_sha256"],
            "consumer_command": ADAPTER, "consumer_command_version": ADAPTER_VERSION,
            "timestamp_precision": "seconds",
            "baseline_output_sha256": baseline["output_sha256"], "checked_at": checked_at.isoformat(),
            "valid_until": checked_at.isoformat(),
            "passed": accepted, "result": "output_matches_baseline" if accepted else "output_changed",
            "rows_consumed": actual["rows_consumed"], "trust": "local_comparison_not_authenticated",
            "consumption": {"mode": "real_workflow", "input_manifest_sha256": actual["input_manifest_sha256"],
                            "output_sha256": actual["output_sha256"], "acceptance_version": "frozen_export_equality_v1",
                            "accepted": accepted, "started_at": started.isoformat()}}
    report["receipt_sha256"] = _digest(report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("capture", "check"):
        target = sub.add_parser(command)
        target.add_argument("--root", type=Path, required=True)
        target.add_argument("--policy", type=Path, required=True)
        target.add_argument("--consumer", required=True)
        if command == "check":
            target.add_argument("--baseline", type=Path, required=True)
            target.add_argument("--operation-receipt", type=Path, required=True)
            target.add_argument("--recovery-receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "capture":
            result = capture_sqlite_export(args.root, args.policy, args.consumer)
        else:
            baseline, _ = _read(args.baseline, MAX_EXPORT_BYTES)
            operation, _ = _read(args.operation_receipt)
            recovery = _read(args.recovery_receipt)[0] if args.recovery_receipt else None
            result = check_sqlite_consumer(args.root, args.policy, args.consumer, baseline=baseline,
                                          operation_receipt=operation, recovery_receipt=recovery)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0 if result.get("passed", True) else 1
    except (ValueError, TypeError, KeyError, OSError, RecursionError, sqlite3.Error) as exc:
        reason = str(exc) if isinstance(exc, ValueError) else "consumer_input_invalid"
        reason = reason if re.fullmatch(r"[a-z_]{1,64}", reason) else "consumer_input_invalid"
        print(json.dumps({"state": reason, "passed": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
