import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
import time

import pytest

from workspace_metabolism import core
from workspace_metabolism.claim_backend import JsonClaimBackend
from workspace_metabolism.claim_guard import ClaimGuard, ClaimRejected


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    cache = root / "cache"
    cache.mkdir()
    (cache / "result.txt").write_text("original", encoding="utf-8")
    policy = tmp_path / "metabolism.json"
    policy.write_text(json.dumps({"version": 1, "defaults": {}, "entries": [
        {"path": "cache", "grade": "G4", "cleanup": "auto", "retention_days": 1}
    ]}), encoding="utf-8")
    backend = JsonClaimBackend(root)
    guard = ClaimGuard(root, backend, authorize=lambda p: True, clean_base=lambda p: True)
    return root, policy, tmp_path / "state", backend, guard


def cleanup(workspace, *, yes=True):
    root, policy, state, _, _ = workspace
    old = time.time() - 3 * 86400
    for path in root.rglob("*"):
        os.utime(path, (old, old))
    core.clean(root, policy, state, {"G4"}, yes=yes)


@pytest.mark.parametrize("scope", ["cache/result.txt", "cache/not-created.txt", "CACHE/result.txt"])
def test_claim_preserves_ancestor_directory(workspace, scope, capsys):
    root, _, _, backend, guard = workspace
    claim = guard.begin(task="keep work", files=[scope])
    before = backend.path.read_bytes()
    cleanup(workspace)
    assert (root / "cache/result.txt").read_text() == "original"
    assert backend.path.read_bytes() == before
    output = capsys.readouterr().out
    assert "claim" in output
    assert claim["session_id"] not in output


@pytest.mark.parametrize("status", ["active", "paused", "done"])
def test_pending_intent_preserved_even_with_terminal_status(workspace, status):
    root, _, _, backend, guard = workspace
    guard.begin(task="pending", files=["cache/result.txt"])
    with backend.transaction():
        registry = backend.load()
        registry["claims"][0]["status"] = status
        registry["claims"][0]["wm_guard"]["pending"] = {"operation_id": "incomplete"}
        backend.save(registry)
    cleanup(workspace)
    assert (root / "cache/result.txt").exists()
    with pytest.raises(ClaimRejected, match="occupied"):
        guard.begin(task="no takeover", files=["cache/result.txt"])


def test_expired_claim_not_released(workspace):
    root, _, _, backend, _ = workspace
    guard = ClaimGuard(root, backend, authorize=lambda p: True, clean_base=lambda p: True, clock=lambda: 1)
    guard.begin(task="expired", files=["cache/result.txt"], ttl=1)
    cleanup(workspace)
    assert (root / "cache/result.txt").exists()


def test_completed_claim_and_unrelated_claim_do_not_block(workspace):
    root, _, state, _, guard = workspace
    claim = guard.begin(task="finished", files=["cache/result.txt"])
    guard.finish(claim["claim_id"], claim["session_id"], delivered=lambda c: True)
    guard.begin(task="other task", files=["cache-other.txt"])
    cleanup(workspace)
    assert not (root / "cache").exists()
    assert list((state / "runs").glob("*.json"))


@pytest.mark.parametrize("raw", [
    "{broken", "[]", '{"version": 1, "claims": []}',
    '{"version": 1, "wm_claim_backend": 1, "claims": "bad"}',
    '{"version": 1, "wm_claim_backend": 1, "claims": [{"id":"x","status":"active","files":[],"dirs":[]}]}'
])
def test_invalid_or_foreign_registry_blocks_without_reset(workspace, raw):
    root, _, state, backend, _ = workspace
    backend.directory.mkdir()
    backend.path.write_text(raw, encoding="utf-8")
    with pytest.raises(SystemExit, match="claim"):
        cleanup(workspace)
    assert (root / "cache/result.txt").exists()
    assert backend.path.read_text(encoding="utf-8") == raw
    assert not (state / "recycle").exists()


def test_preview_no_claim_storage_side_effect_and_execution_rechecks(workspace, capsys):
    root, _, _, backend, guard = workspace
    cleanup(workspace, yes=False)
    assert not backend.directory.exists()
    assert "1 item(s)" in capsys.readouterr().out
    guard.begin(task="claimed after preview", files=["cache/result.txt"])
    cleanup(workspace)
    assert (root / "cache/result.txt").exists()


def test_claim_storage_is_never_a_cleanup_candidate(workspace):
    root, policy, state, backend, guard = workspace
    guard.begin(task="not in cache", files=["new.txt"])
    policy.write_text(json.dumps({"version": 1, "defaults": {}, "entries": [
        {"path": ".coordination", "grade": "G4", "cleanup": "auto", "retention_days": 1}
    ]}), encoding="utf-8")
    before = backend.path.read_bytes()
    cleanup(workspace)
    assert backend.path.read_bytes() == before
    assert not (state / "recycle").exists()


def test_nested_claim_storage_preserves_parent(workspace):
    root, _, _, _, _ = workspace
    nested = root / "cache/child/.coordination"
    nested.mkdir(parents=True)
    (nested / "registry.json").write_text("foreign authority")
    cleanup(workspace)
    assert (nested / "registry.json").read_text() == "foreign authority"


def test_restore_refuses_claim_on_missing_original(workspace, capsys):
    root, _, state, _, guard = workspace
    cleanup(workspace)
    run_id = next((state / "runs").glob("*.json")).stem
    guard.begin(task="new owner", files=["cache/new.txt"])
    core.rollback(root, state, run_id)
    assert not (root / "cache").exists()
    assert (state / "recycle" / run_id / "cache/result.txt").exists()
    assert "claim" in capsys.readouterr().out


def test_claim_waits_until_cleanup_move_finishes(workspace, monkeypatch):
    root, _, _, backend, guard = workspace
    moving = threading.Event()
    release = threading.Event()
    requested = threading.Event()
    moved = core.shutil.move

    def paused_move(*args, **kwargs):
        moving.set()
        assert release.wait(5)
        return moved(*args, **kwargs)

    def claim_after_move():
        requested.set()
        return guard.begin(task="after cleanup", files=["cache/result.txt"])

    monkeypatch.setattr(core.shutil, "move", paused_move)
    with ThreadPoolExecutor(max_workers=2) as pool:
        cleaning = pool.submit(cleanup, workspace)
        assert moving.wait(5)
        claiming = pool.submit(claim_after_move)
        try:
            assert requested.wait(2)
            time.sleep(0.15)
            assert not claiming.done()
        finally:
            release.set()
        cleaning.result(timeout=5)
        claiming.result(timeout=5)
    assert not (root / "cache").exists()
    assert backend.load()["claims"][0]["wm_guard"]["base"]["cache/result.txt"]["exists"] is False


def test_cleanup_waits_for_in_flight_write(workspace, monkeypatch):
    root, _, _, _, guard = workspace
    claim = guard.begin(task="writing", files=["cache/result.txt"])
    replacing = threading.Event()
    release = threading.Event()
    original_replace = guard._replace

    def paused_replace(*args):
        replacing.set()
        assert release.wait(5)
        return original_replace(*args)

    monkeypatch.setattr(guard, "_replace", paused_replace)
    with ThreadPoolExecutor(max_workers=2) as pool:
        writing = pool.submit(guard.write, claim["claim_id"], claim["session_id"],
                              path="cache/result.txt", text="new content", operation_id="write-1")
        assert replacing.wait(5)
        cleaning = pool.submit(cleanup, workspace)
        try:
            time.sleep(0.15)
            assert not cleaning.done()
        finally:
            release.set()
        writing.result(timeout=5)
        cleaning.result(timeout=5)
    assert (root / "cache/result.txt").read_text() == "new content"


def test_single_file_candidate_remains_cleanable(workspace):
    root, policy, _, _, _ = workspace
    data = json.loads(policy.read_text())
    data["entries"][0]["path"] = "cache/result.txt"
    policy.write_text(json.dumps(data))
    cleanup(workspace)
    assert (root / "cache").exists()
    assert not (root / "cache/result.txt").exists()


@pytest.mark.parametrize("mutation", ["wrong-workspace", "missing-pending", "bad-scope", "duplicate-id"])
def test_malformed_retention_metadata_fails_closed(workspace, mutation):
    root, _, _, backend, guard = workspace
    guard.begin(task="metadata", files=["cache/result.txt"])
    with backend.transaction():
        data = backend.load()
        claim = data["claims"][0]
        if mutation == "wrong-workspace":
            claim["wm_guard"]["workspace"] = "elsewhere"
        elif mutation == "missing-pending":
            del claim["wm_guard"]["pending"]
        elif mutation == "bad-scope":
            claim["files"] = ["../cache/result.txt"]
        else:
            data["claims"].append(claim)
        backend.save(data)
    with pytest.raises(SystemExit, match="claim"):
        cleanup(workspace)
    assert (root / "cache/result.txt").exists()
