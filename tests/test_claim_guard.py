import copy
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import threading

import pytest

from workspace_metabolism.claim_guard import ClaimGuard, ClaimRejected


class Backend:
    def __init__(self):
        self.registry = {"version": 1, "claims": []}
        self.lock = threading.RLock()
        self.saves = 0
        self.fail_at = None

    @contextmanager
    def transaction(self):
        with self.lock:
            yield

    def load(self):
        return copy.deepcopy(self.registry)

    def save(self, registry):
        self.saves += 1
        if self.saves == self.fail_at:
            raise OSError("simulated storage failure")
        self.registry = copy.deepcopy(registry)


@pytest.fixture
def case(tmp_path):
    (tmp_path / "app.py").write_text("value = 1\n")
    (tmp_path / "other.py").write_text("value = 10\n")
    backend = Backend()
    clock = [1000]
    guard = ClaimGuard(tmp_path, backend, authorize=lambda p: p != "protected.py",
                       clean_base=lambda p: True, clock=lambda: clock[0])
    claim = guard.begin(task="test", files=["app.py"])
    return tmp_path, backend, clock, guard, claim


def write(case, **kwargs):
    _, _, _, guard, claim = case
    return guard.write(claim["claim_id"], claim["session_id"],
                       **dict({"path": "app.py", "text": "value = 2\n", "operation_id": "op1"}, **kwargs))


def test_write_and_delivery(case):
    root, backend, _, guard, claim = case
    receipt = write(case)
    assert "before" not in receipt
    assert (root / "app.py").read_text() == "value = 2\n"
    assert backend.registry["claims"][0]["wm_guard"]["pending"] is None
    guard.finish(claim["claim_id"], claim["session_id"], delivered=lambda c: True)
    assert backend.registry["claims"][0]["status"] == "done"
    assert backend.registry["claims"][0]["wm_guard"]["receipts"][0]["before"]["data"]
    with pytest.raises(ClaimRejected, match="not active"):
        write(case)


def test_conflict_and_atomic_expand(case):
    _, backend, _, guard, claim = case
    guard.begin(task="other", files=["other.py"])
    before = copy.deepcopy(backend.registry)
    with pytest.raises(ClaimRejected, match="occupied"):
        guard.expand(claim["claim_id"], claim["session_id"], ["new.py", "other.py"])
    assert backend.registry == before
    with pytest.raises(ClaimRejected, match="occupied"):
        guard.begin(task="duplicate", files=["app.py"])


def test_two_sessions_same_scope_only_one_wins(tmp_path):
    backend = Backend()
    guard = ClaimGuard(tmp_path, backend, authorize=lambda p: True, clean_base=lambda p: True)

    def attempt(_):
        try:
            return guard.begin(task="parallel", files=["new.py"])
        except ClaimRejected:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(16)))
    assert sum(r is not None for r in results) == 1
    assert len(backend.registry["claims"]) == 1


def test_no_scope_or_session_no_write(case):
    root, _, _, guard, claim = case
    with pytest.raises(ClaimRejected, match="scope"):
        write(case, path="other.py")
    with pytest.raises(ClaimRejected, match="mismatch"):
        guard.write(claim["claim_id"], "another session", path="app.py", text="bad", operation_id="bad")
    assert (root / "app.py").read_text() == "value = 1\n"
    assert (root / "other.py").read_text() == "value = 10\n"


def test_expiry_preserves_dirty_claim_and_cannot_renew(case):
    root, backend, clock, guard, claim = case
    write(case)
    clock[0] += 1801
    with pytest.raises(ClaimRejected, match="expired"):
        guard.renew(claim["claim_id"], claim["session_id"])
    with pytest.raises(ClaimRejected, match="expired"):
        write(case, operation_id="op2")
    with pytest.raises(ClaimRejected, match="occupied"):
        guard.begin(task="takeover", files=["app.py"])
    assert backend.registry["claims"][0]["status"] == "active"
    assert (root / "app.py").read_text() == "value = 2\n"


def test_renew_and_expand_to_new_file(case):
    root, _, clock, guard, claim = case
    clock[0] += 100
    guard.renew(claim["claim_id"], claim["session_id"])
    guard.expand(claim["claim_id"], claim["session_id"], ["new.py"])
    write(case, path="new.py")
    assert (root / "new.py").read_text() == "value = 2\n"


def test_external_change_refused(case):
    root, _, _, _, _ = case
    (root / "app.py").write_text("someone else's work")
    with pytest.raises(ClaimRejected, match="outside"):
        write(case)
    assert (root / "app.py").read_text() == "someone else's work"


def test_replay_not_repeat_and_no_backup_exposed(case):
    write(case)
    result = write(case)
    assert result["replayed"] is True and "before" not in result
    assert len(case[1].registry["claims"][0]["wm_guard"]["receipts"]) == 1
    with pytest.raises(ClaimRejected, match="reused"):
        write(case, text="different")


@pytest.mark.parametrize("failure", ["intent", "replace", "receipt"])
def test_failure_preserves_evidence_and_blocks_unsafe_retry(case, monkeypatch, failure):
    root, backend, _, guard, _ = case
    if failure == "replace":
        def broken(*args):
            raise OSError("simulated replace failure")
        monkeypatch.setattr(guard, "_replace", broken)
    else:
        backend.fail_at = backend.saves + (1 if failure == "intent" else 2)
    with pytest.raises(OSError):
        write(case)
    if failure == "intent":
        assert backend.registry["claims"][0]["wm_guard"]["pending"] is None
    else:
        assert backend.registry["claims"][0]["wm_guard"]["pending"]["before"]["data"]
        with pytest.raises(ClaimRejected, match="recovery_required"):
            write(case)
    expected = "value = 2\n" if failure == "receipt" else "value = 1\n"
    assert (root / "app.py").read_text() == expected


def test_policy_denial_not_overridden_by_claim(case):
    root, _, _, guard, claim = case
    guard.expand(claim["claim_id"], claim["session_id"], ["protected.py"])
    with pytest.raises(ClaimRejected, match="policy denied"):
        write(case, path="protected.py")
    assert not (root / "protected.py").exists()


def test_dirty_baseline_cannot_be_adopted(case):
    _, _, _, guard, _ = case
    guard.clean_base = lambda p: False
    with pytest.raises(ClaimRejected, match="baseline_unattributed"):
        guard.begin(task="adopt", files=["other.py"])


def test_delivery_failure_keeps_ownership(case):
    _, backend, _, guard, claim = case
    with pytest.raises(ClaimRejected, match="delivery not verified"):
        guard.finish(claim["claim_id"], claim["session_id"], delivered=lambda c: False)
    assert backend.registry["claims"][0]["status"] == "active"


@pytest.mark.parametrize("path", ["../outside", ".git/config", ".coordination/registry.json", "a/../b", "a//b", "a\\b", "/a", "a*", "app.py.", "NUL", "sub/COM1.txt"])
def test_invalid_paths(case, path):
    with pytest.raises(ClaimRejected):
        case[3].begin(task="bad", files=[path])


def test_legacy_directory_claim_blocks_new_child(case):
    case[1].registry["claims"].append({"id": "legacy", "status": "active", "dirs": ["tools"], "files": []})
    with pytest.raises(ClaimRejected, match="occupied"):
        case[3].begin(task="new file", files=["tools/new.py"])


def test_case_alias_conflicts(case):
    with pytest.raises(ClaimRejected, match="occupied"):
        case[3].begin(task="alias", files=["APP.py"])


def test_corrupt_registry_not_reset(case):
    case[1].registry = {"claims": []}
    with pytest.raises(ClaimRejected, match="invalid claim registry"):
        case[3].begin(task="oops", files=["other.py"])
    assert "version" not in case[1].registry


def test_claim_cannot_be_reused_in_another_workspace(case, tmp_path):
    other = tmp_path / "other_root"
    other.mkdir()
    backend = case[1]
    foreign = ClaimGuard(other, backend, authorize=lambda p: True, clean_base=lambda p: True)
    with pytest.raises(ClaimRejected, match="different workspace"):
        foreign.write(case[4]["claim_id"], case[4]["session_id"], path="app.py", text="bad", operation_id="x")


def test_recovery_metadata_serializable(case):
    write(case)
    assert json.loads(json.dumps(case[1].registry)) == case[1].registry


@pytest.mark.parametrize("scope", [None, "app.py", [None], [""]])
def test_invalid_existing_scope_blocks_claim(case, scope):
    case[1].registry["claims"].append({"id": "broken", "status": "active", "files": scope, "dirs": []})
    before = copy.deepcopy(case[1].registry)
    with pytest.raises(ClaimRejected, match="invalid claim scope"):
        case[3].begin(task="must not proceed", files=["other.py"])
    assert case[1].registry == before


@pytest.mark.parametrize("written", [False, True])
def test_recover_only_observes_and_preserves_original_evidence(case, monkeypatch, written):
    root, backend, _, guard, claim = case
    if written:
        backend.fail_at = backend.saves + 2
    else:
        def fail_replace(*args):
            raise OSError("interrupted before replace")
        monkeypatch.setattr(guard, "_replace", fail_replace)
    with pytest.raises(OSError):
        write(case)
    backend.fail_at = None
    contents = (root / "app.py").read_bytes()
    mtime = (root / "app.py").stat().st_mtime_ns
    result = guard.recover(claim["claim_id"], claim["session_id"])
    assert result["outcome"] == ("intended_observed" if written else "original_observed")
    assert result["files_written"] == 0 and "before" not in result
    assert (root / "app.py").read_bytes() == contents
    assert (root / "app.py").stat().st_mtime_ns == mtime
    metadata = backend.registry["claims"][0]["wm_guard"]
    assert metadata["pending"] is None
    evidence = metadata["receipts"] if written else metadata["recoveries"]
    assert evidence[0]["before"]["data"]
    assert guard.recover(claim["claim_id"], claim["session_id"])["status"] == "no_pending"
    if written:
        assert write(case)["replayed"] is True
        assert metadata["receipts"][0]["observation_only"] is True


def test_recover_external_version_preserves_pending(case):
    root, backend, _, guard, claim = case
    backend.fail_at = backend.saves + 2
    with pytest.raises(OSError):
        write(case)
    (root / "app.py").write_text("third version", encoding="utf-8")
    before = copy.deepcopy(backend.registry)
    with pytest.raises(ClaimRejected, match="unrecognized"):
        guard.recover(claim["claim_id"], claim["session_id"])
    assert backend.registry == before
    assert (root / "app.py").read_text() == "third version"


def test_recover_persistence_failure_keeps_pending(case):
    root, backend, _, guard, claim = case
    backend.fail_at = backend.saves + 2
    with pytest.raises(OSError):
        write(case)
    backend.fail_at = backend.saves + 1
    with pytest.raises(OSError):
        guard.recover(claim["claim_id"], claim["session_id"])
    assert backend.registry["claims"][0]["wm_guard"]["pending"]
    assert (root / "app.py").read_text() == "value = 2\n"


def test_resume_expired_claim_rotates_session_and_keeps_receipts(case):
    _, backend, clock, guard, claim = case
    write(case)
    clock[0] += 1801
    resumed = guard.resume(claim["claim_id"], claim["session_id"])
    assert resumed["session_id"] != claim["session_id"]
    assert resumed["generation"] == 2
    assert len(backend.registry["claims"][0]["wm_guard"]["receipts"]) == 1
    with pytest.raises(ClaimRejected, match="mismatch"):
        write(case, operation_id="stale")
    assert guard.write(resumed["claim_id"], resumed["session_id"], path="app.py", text="next",
                       operation_id="next")["after"]["exists"]


def test_resume_rejects_external_change_and_pending(case):
    root, backend, _, guard, claim = case
    backend.fail_at = backend.saves + 2
    with pytest.raises(OSError):
        write(case)
    with pytest.raises(ClaimRejected, match="recovery_required"):
        guard.resume(claim["claim_id"], claim["session_id"])
    backend.fail_at = None
    guard.recover(claim["claim_id"], claim["session_id"])
    (root / "app.py").write_text("external", encoding="utf-8")
    with pytest.raises(ClaimRejected, match="outside"):
        guard.resume(claim["claim_id"], claim["session_id"])


def test_recovery_does_not_renew_expired_lease(case):
    _, backend, clock, guard, claim = case
    backend.fail_at = backend.saves + 2
    with pytest.raises(OSError):
        write(case)
    backend.fail_at = None
    clock[0] += 1801
    guard.recover(claim["claim_id"], claim["session_id"])
    with pytest.raises(ClaimRejected, match="expired"):
        write(case)


def test_recovery_requires_owner_and_checks_other_claimed_files(case):
    root, backend, _, guard, claim = case
    guard.expand(claim["claim_id"], claim["session_id"], ["other.py"])
    backend.fail_at = backend.saves + 2
    with pytest.raises(OSError):
        write(case)
    with pytest.raises(ClaimRejected, match="mismatch"):
        guard.recover(claim["claim_id"], "different")
    (root / "other.py").write_text("external", encoding="utf-8")
    with pytest.raises(ClaimRejected, match="another claimed"):
        guard.recover(claim["claim_id"], claim["session_id"])


def test_invalid_pending_evidence_is_not_cleared(case):
    _, backend, _, guard, claim = case
    backend.registry["claims"][0]["wm_guard"]["pending"] = {"uncertain": True}
    with pytest.raises(ClaimRejected, match="invalid pending"):
        guard.recover(claim["claim_id"], claim["session_id"])
    assert backend.registry["claims"][0]["wm_guard"]["pending"] == {"uncertain": True}


def test_failed_operation_cannot_change_request_after_recovery(case, monkeypatch):
    _, _, _, guard, claim = case
    replace = guard._replace
    def fail(*args):
        raise OSError("injected")
    monkeypatch.setattr(guard, "_replace", fail)
    with pytest.raises(OSError):
        write(case)
    guard.recover(claim["claim_id"], claim["session_id"])
    monkeypatch.setattr(guard, "_replace", replace)
    with pytest.raises(ClaimRejected, match="reused"):
        write(case, text="new request")
    assert write(case)["after"]["exists"]
