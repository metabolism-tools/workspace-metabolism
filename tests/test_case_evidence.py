import importlib.util
import json
from pathlib import Path

import pytest
from workspace_metabolism.core import journal_append

spec = importlib.util.spec_from_file_location(
    "case_evidence", Path(__file__).parents[1] / "tools/summarize_case_evidence.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_real_writer_outcomes_and_privacy(tmp_path):
    journal_append(tmp_path, "slim", "private-user", status="dry_run", db="secret-db")
    journal_append(tmp_path, "slim", "private-user", status="ok", reclaimed_bytes=900)
    journal_append(tmp_path, "govern", "private-user", decision="deny", paths=["secret-path"])
    journal_append(tmp_path, "slim", "private-user", status="error", error="secret-error")
    path = tmp_path / "journal.jsonl"
    before = path.read_bytes()
    report = module.summarize(path)
    assert report["evidence_status"] == "chain_consistent"
    assert report["operation_observations"] == {
        "preview": 1, "execution_reported_ok": 1, "permission_denied": 1, "failure_reported": 1}
    assert report["business_recovery_verified"] is False
    assert report["supervision_minutes"] is None
    assert report["net_storage_savings_bytes"] is None
    assert "secret" not in json.dumps(report)
    assert "private-user" not in json.dumps(report)
    assert path.read_bytes() == before


@pytest.mark.parametrize("payload,status", [(None, "missing"), (b"", "empty"),
    (b"{", "invalid"), (b"[]\n", "invalid"), (b"\xff", "invalid")])
def test_absence_and_damage_are_not_success(tmp_path, payload, status):
    path = tmp_path / "journal.jsonl"
    if payload is not None:
        path.write_bytes(payload)
    report = module.summarize(path)
    assert report["evidence_status"] == status
    assert report["coverage_verified"] is False


def test_tampering_and_partial_tail_discard_counts(tmp_path):
    journal_append(tmp_path, "audit", "test")
    path = tmp_path / "journal.jsonl"
    original = path.read_bytes()
    for payload in (original + b"{", original.replace(b'"seq": 1', b'"seq": 2')):
        path.write_bytes(payload)
        report = module.summarize(path)
        assert report["evidence_status"] == "invalid"
        assert report["actions"] == {}


def test_budget(tmp_path, monkeypatch):
    path = tmp_path / "journal.jsonl"
    path.write_bytes(b" " * 33)
    monkeypatch.setattr(module, "MAX_BYTES", 32)
    assert module.summarize(path)["evidence_status"] == "over_budget"


def test_other_tools_are_not_wm_evidence(tmp_path):
    path = tmp_path / "journal.jsonl"
    path.write_text('{"kind":"compaction","verified":true}\n', encoding="utf-8")
    assert module.summarize(path)["evidence_status"] == "unsupported_format"
