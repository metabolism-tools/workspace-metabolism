"""Synthetic maintenance-observation examples, using only the Python standard library.

No scheduler, network, DSH model, WM operation, or production input is used.
The small evaluator associates supplied observations; it is not a runtime gate.
"""

from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def stamp(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timezone_required")
    return parsed


def evaluate_obligation(expected, receipt, as_of):
    """Reference example for one explicit slot; never infers or runs a schedule.

    Caller validates actual artifacts and authenticates sources. Missing receipt
    means missing evidence, not proof that a worker did not execute.
    """
    now = stamp(as_of)
    enrolled, opened, deadline = [stamp(expected[k]) for k in
                                 ("enrolled_at", "window_start", "deadline")]
    if opened > deadline or enrolled > now:
        raise ValueError("invalid_window")
    for key in ("obligation_id", "executor_version"):
        if not isinstance(expected[key], str) or not expected[key].strip():
            raise ValueError("invalid_identity")
    result = dict(obligation="unknown", evidence="missing", deadline_missed=None,
                  trigger="unknown", consumer="not_checked", recovery="not_assessed",
                  notification="not_observed", evidence_trust="reported_not_authenticated",
                  authorizes_execution=False, natural_trigger_verified=False,
                  supervision_benefit="not_established", token_benefit="not_established")
    if enrolled > opened:
        result["obligation"] = "uninstrumented_history"
        return result
    if now < opened:
        result["obligation"] = "not_due"
        return result
    result["deadline_missed"] = None if receipt else now > deadline
    if receipt is None:
        result["obligation"] = "missing_evidence" if now > deadline else "within_window"
        return result
    if any(receipt.get(k) != expected[k] for k in ("obligation_id", "executor_version")):
        result["evidence"] = "mismatched"
        return result
    started = stamp(receipt["started_at"])
    if not opened <= started <= now:
        result["evidence"] = "outside_window"
        return result
    result["trigger"] = receipt.get("trigger", "unknown")
    status = receipt["status"]
    if status == "running":
        result.update(obligation="overdue" if now > deadline else "within_window",
                      evidence="reported_running", deadline_missed=now > deadline)
        return result
    if status not in ("completed", "failed"):
        raise ValueError("invalid_execution_status")
    finished = stamp(receipt["finished_at"])
    if not started <= finished <= now:
        result["evidence"] = "outside_window"
        return result
    result["deadline_missed"] = finished > deadline
    if status == "failed":
        result.update(obligation="failed", evidence="reported_failure", deadline_missed=now > deadline)
        return result
    if stamp(receipt["valid_until"]) < now:
        result["evidence"] = "expired"
        return result
    result.update(obligation="completed_late" if finished > deadline else "completed",
                  evidence="reported_current")
    return result


def attempt_notification(incident, ledger, sender):
    """In-memory fixture only; real adapters own durable retries and delivery."""
    if any(row == {"incident": incident, "status": "sent"} for row in ledger):
        return "suppressed_after_sent"
    try:
        sender()
    except OSError:
        state = "failed"
    else:
        state = "sent"
    ledger.append({"incident": incident, "status": state})
    return state


def expected_slot():
    return dict(obligation_id="audit:fixture-slot-1", executor_version="fixture-v1",
                enrolled_at="2026-01-01T00:00:00+00:00",
                window_start="2026-01-02T10:00:00+00:00",
                deadline="2026-01-02T10:10:00+00:00")


def completed_receipt():
    return dict(obligation_id="audit:fixture-slot-1", executor_version="fixture-v1",
                started_at="2026-01-02T10:00:00+00:00",
                finished_at="2026-01-02T10:01:00+00:00",
                valid_until="2026-01-02T11:00:00+00:00",
                status="completed", execution="no_change", trigger="manual")


def consume(root):
    values = json.loads((root / "values.json").read_text(encoding="utf-8"))
    multiplier = json.loads((root / "rule.json").read_text(encoding="utf-8"))
    total = sum(values) * multiplier
    return {"total": total, "accepted": total == 18}


def run_examples():
    expected = expected_slot()
    now = "2026-01-02T10:20:00+00:00"
    results = {}
    # All files belong to this new fixture and TemporaryDirectory removes them.
    with tempfile.TemporaryDirectory(prefix="wm-observation-fixture-") as temporary:
        root = Path(temporary)
        worker = root / "worker.py"
        # Import failure happens before the worker could write its receipt.
        worker.write_text("import fixture_missing_maintenance_dependency\n", encoding="utf-8")
        process = subprocess.run([sys.executable, "-I", str(worker)], cwd=root,
                                 capture_output=True, text=True, timeout=10)
        if process.returncode == 0 or "ModuleNotFoundError" not in process.stderr:
            raise RuntimeError("startup fault was not reproduced")
        result = evaluate_obligation(expected, None, now)
        result.update(worker_exit=process.returncode, outcome="missing_completion_evidence")
        results["startup_failure"] = result

        report = root / "report.txt"
        report.write_text("OK\n", encoding="utf-8")
        report_hash = hashlib.sha256(report.read_bytes()).hexdigest()
        receipt = completed_receipt()
        receipt["valid_until"] = "2026-01-02T10:05:00+00:00"
        result = evaluate_obligation(expected, receipt, now)
        result.update(artifact_hash_matches=hashlib.sha256(report.read_bytes()).hexdigest() == report_hash,
                      outcome="stale_report_unresolved")
        results["stale_report"] = result

        attempts = []
        ledger = []

        def fake_sender():
            attempts.append("attempt")
            if len(attempts) == 1:
                raise OSError("synthetic send failure")

        states = [attempt_notification(expected["obligation_id"], ledger, fake_sender)
                  for _ in range(3)]
        results["notification_retry"] = dict(outcome="failed_then_sent_then_suppressed",
            statuses=states, sender_calls=len(attempts), incident_resolved=False,
            notification="sent", delivery_acknowledged=False, transport="in_memory_stub")

        (root / "values.json").write_text("[7, 11]", encoding="utf-8")
        (root / "rule.json").write_text("1", encoding="utf-8")
        before = consume(root)
        backup = (root / "values.json").read_bytes()
        (root / "values.json").write_text("[]", encoding="utf-8")
        (root / "rule.json").write_text("2", encoding="utf-8")
        (root / "values.json").write_bytes(backup)  # Incomplete recovery boundary.
        after = consume(root)
        result = evaluate_obligation(expected, completed_receipt(), now)
        result.update(outcome="restored_files_consumer_rejected", consumer="rejected",
                      recovery="files_restored", before=before, after=after,
                      restored_bytes_match=(root / "values.json").read_bytes() == backup)
        results["incomplete_recovery"] = result

        (root / "rule.json").write_text("1", encoding="utf-8")
        result = evaluate_obligation(expected, completed_receipt(), now)
        result.update(outcome="no_change_consumer_accepted", execution="no_change",
                      consumer="accepted" if consume(root)["accepted"] else "rejected",
                      reclaimed_bytes=0)
        results["normal_no_change"] = result
        results["not_due"] = evaluate_obligation(expected, None, "2026-01-02T09:00:00+00:00")
        historical = deepcopy(expected)
        historical["enrolled_at"] = "2026-01-02T10:15:00+00:00"
        results["before_enrollment"] = evaluate_obligation(historical, None, now)

    return dict(synthetic_fixture=True, time_source="fixed_replay", llm_executed=False,
                scheduler_executed=False, network_used=False, wm_operations=False,
                supervision_minutes=None, token_savings=None, scenarios=results)


if __name__ == "__main__":
    print(json.dumps(run_examples(), indent=2, allow_nan=False))
