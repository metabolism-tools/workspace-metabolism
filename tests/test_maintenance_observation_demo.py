import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


EXAMPLE = Path(__file__).resolve().parents[1] / "plugins/dsh-metabolic-maintenance/examples/maintenance_observation.py"
spec = importlib.util.spec_from_file_location("maintenance_observation_demo", EXAMPLE)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
NOW = "2026-01-02T10:20:00+00:00"


def test_real_fixture_faults_do_not_become_accepted_maintenance():
    report = demo.run_examples()
    cases = report["scenarios"]
    assert cases["startup_failure"]["worker_exit"] != 0
    assert cases["startup_failure"]["obligation"] == "missing_evidence"
    assert cases["stale_report"]["artifact_hash_matches"] is True
    assert cases["stale_report"]["evidence"] == "expired"
    assert cases["stale_report"]["obligation"] == "unknown"
    recovered = cases["incomplete_recovery"]
    assert recovered["obligation"] == "completed"
    assert recovered["restored_bytes_match"] is True
    assert recovered["before"] == {"total": 18, "accepted": True}
    assert recovered["after"] == {"total": 36, "accepted": False}
    assert recovered["consumer"] == "rejected"
    assert cases["normal_no_change"]["consumer"] == "accepted"
    assert cases["normal_no_change"]["reclaimed_bytes"] == 0
    assert cases["not_due"]["obligation"] == "not_due"
    assert cases["before_enrollment"]["obligation"] == "uninstrumented_history"
    assert cases["before_enrollment"]["deadline_missed"] is None
    assert report["supervision_minutes"] is report["token_savings"] is None


def test_notification_failure_retries_but_send_does_not_resolve_incident():
    result = demo.run_examples()["scenarios"]["notification_retry"]
    assert result["statuses"] == ["failed", "sent", "suppressed_after_sent"]
    assert result["sender_calls"] == 2
    assert result["incident_resolved"] is result["delivery_acknowledged"] is False
    # A different due slot cannot be suppressed by the old incident's send.
    ledger = [{"incident": "old-slot", "status": "sent"}]
    calls = []
    assert demo.attempt_notification("new-slot", ledger, lambda: calls.append(1)) == "sent"
    assert calls == [1]


@pytest.mark.parametrize("as_of,state,missed", [
    ("2026-01-02T09:59:59+00:00", "not_due", None),
    ("2026-01-02T10:10:00+00:00", "within_window", False),
    ("2026-01-02T10:10:01+00:00", "missing_evidence", True),
    ("2026-01-02T18:10:00+08:00", "within_window", False),
])
def test_deadline_and_timezone_boundary(as_of, state, missed):
    result = demo.evaluate_obligation(demo.expected_slot(), None, as_of)
    assert (result["obligation"], result["deadline_missed"]) == (state, missed)


@pytest.mark.parametrize("mutation,evidence", [
    ({"obligation_id": "other-slot"}, "mismatched"),
    ({"executor_version": "old-deployment"}, "mismatched"),
    ({"started_at": "2026-01-02T09:59:59+00:00"}, "outside_window"),
    ({"finished_at": "2026-01-02T10:21:00+00:00"}, "outside_window"),
    ({"valid_until": "2026-01-02T10:19:59+00:00"}, "expired"),
])
def test_wrong_slot_version_or_time_cannot_establish_completion(mutation, evidence):
    receipt = demo.completed_receipt() | mutation
    result = demo.evaluate_obligation(demo.expected_slot(), receipt, NOW)
    assert (result["obligation"], result["evidence"]) == ("unknown", evidence)


def test_late_completion_retains_missed_deadline_and_manual_trigger_boundary():
    expected = demo.expected_slot()
    receipt = demo.completed_receipt() | {"finished_at": "2026-01-02T10:12:00+00:00"}
    originals = copy.deepcopy((expected, receipt))
    result = demo.evaluate_obligation(expected, receipt, NOW)
    assert result["obligation"] == "completed_late"
    assert result["deadline_missed"] is True
    assert result["trigger"] == "manual"
    assert result["natural_trigger_verified"] is result["authorizes_execution"] is False
    assert result["consumer"] == "not_checked"
    assert (expected, receipt) == originals


@pytest.mark.parametrize("status,state", [("failed", "failed"), ("running", "overdue")])
def test_failed_and_unfinished_attempts_remain_visible(status, state):
    result = demo.evaluate_obligation(demo.expected_slot(), demo.completed_receipt() | {"status": status}, NOW)
    assert result["obligation"] == state
    assert result["deadline_missed"] is True


def test_unzoned_time_is_rejected():
    with pytest.raises(ValueError, match="timezone_required"):
        demo.evaluate_obligation(demo.expected_slot(), None, "2026-01-02T10:20:00")


def test_example_runs_from_unrelated_working_directory_without_installed_wm(tmp_path):
    process = subprocess.run([sys.executable, "-I", str(EXAMPLE)], cwd=tmp_path,
                             capture_output=True, text=True, timeout=30, check=True)
    report = json.loads(process.stdout)
    assert report["wm_operations"] is report["network_used"] is report["scheduler_executed"] is False
    assert not list(tmp_path.iterdir())
