"""Real filesystem failure cases for durable clean/restore records."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from workspace_metabolism import core as m
from workspace_metabolism.cli import main


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root, state = tmp_path / "workspace", tmp_path / "state"
    root.mkdir()
    source = root / "cache"
    source.mkdir()
    (source / "data").write_bytes(b"before")
    policy = root / "policy.json"
    policy.write_text('{"version":1,"entries":[]}', encoding="utf-8")
    monkeypatch.setattr(m, "plan_items", lambda *a, **kw: [{"path": "cache", "grade": "G4",
        "cleanup": "auto", "reason": "", "is_dir": True, "files": 1, "size": 6}])
    return root, state, policy


def manifest_for(state):
    path = next((state / "runs").glob("clean-*.json"))
    return path, json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("after_move", [False, True])
def test_process_interrupt_is_recoverable(workspace, monkeypatch, after_move):
    root, state, policy = workspace
    move = m.shutil.move
    def interrupt(src, dst):
        if after_move:
            move(src, dst)
        raise KeyboardInterrupt("interruption fault")
    monkeypatch.setattr(m.shutil, "move", interrupt)
    with pytest.raises(KeyboardInterrupt):
        m.clean(root, policy, state, {"G4"}, yes=True)
    path, manifest = manifest_for(state)
    assert manifest["pending"][0]["hashes"]
    assert m.verify(state)["recovery_issues"][0]["run_id"] == path.stem
    assert main(["--state-dir", str(state), "verify"]) == 2
    m.purge(state, older_than_days=-1, yes=True)
    if after_move:
        assert (state / "recycle" / path.stem / "cache" / "data").exists()
    monkeypatch.setattr(m.shutil, "move", move)
    assert m.rollback(root, state, path.stem)
    assert (root / "cache" / "data").read_bytes() == b"before"
    assert not m.verify(state)["recovery_issues"]


def test_interrupt_during_restore_can_resume(workspace, monkeypatch):
    root, state, policy = workspace
    m.clean(root, policy, state, {"G4"}, yes=True)
    path, _ = manifest_for(state)
    move = m.shutil.move
    def interrupt(src, dst):
        move(src, dst)
        raise KeyboardInterrupt()
    monkeypatch.setattr(m.shutil, "move", interrupt)
    with pytest.raises(KeyboardInterrupt):
        m.rollback(root, state, path.stem)
    monkeypatch.setattr(m.shutil, "move", move)
    assert m.rollback(root, state, path.stem)
    assert (root / "cache" / "data").read_bytes() == b"before"


@pytest.mark.parametrize("corruption", ["same_size", "extra_file", "legacy"])
def test_restore_rejects_unverified_content(workspace, corruption):
    root, state, policy = workspace
    m.clean(root, policy, state, {"G4"}, yes=True)
    path, manifest = manifest_for(state)
    recycled = state / "recycle" / path.stem / "cache"
    if corruption == "same_size":
        (recycled / "data").write_bytes(b"change")
    elif corruption == "extra_file":
        (recycled / "extra").write_bytes(b"x")
    else:
        manifest["items"][0].update(hashes=None, integrity="size_only")
        path.write_text(json.dumps(manifest), encoding="utf-8")
    assert not m.rollback(root, state, path.stem)
    assert not (root / "cache").exists()
    m.purge(state, older_than_days=-1, yes=True)
    assert recycled.exists()


def test_orphan_recycle_is_reported_and_protected(tmp_path):
    batch = tmp_path / "recycle" / "clean-orphan"
    batch.mkdir(parents=True)
    (batch / "valuable").write_bytes(b"saved")
    assert m.verify(tmp_path)["recovery_issues"][0]["reason"] == "orphan_recycle"
    m.purge(tmp_path, older_than_days=-1, yes=True)
    assert (batch / "valuable").exists()


def test_manifest_failure_happens_before_any_move(workspace, monkeypatch):
    root, state, policy = workspace
    def fail(*args):
        raise OSError("disk full")
    monkeypatch.setattr(m, "_save_clean_manifest", fail)
    with pytest.raises(OSError):
        m.clean(root, policy, state, {"G4"}, yes=True)
    assert (root / "cache" / "data").read_bytes() == b"before"


def test_restore_rejects_other_root_and_run_traversal(workspace, tmp_path):
    root, state, policy = workspace
    m.clean(root, policy, state, {"G4"}, yes=True)
    path, _ = manifest_for(state)
    with pytest.raises(SystemExit, match="another workspace"):
        m.rollback(tmp_path, state, path.stem)
    with pytest.raises(SystemExit, match="invalid clean run ID"):
        m.rollback(root, state, "../../escape")


def test_mcp_reports_failed_restore_and_recovery_without_policy(workspace):
    from workspace_metabolism.mcp_server import handle_message
    root, state, policy = workspace
    m.clean(root, policy, state, {"G4"}, yes=True)
    path, _ = manifest_for(state)
    (state / "recycle" / path.stem / "cache" / "data").write_bytes(b"change")
    ctx = {"root": root, "state_dir": state, "registry_path": None}
    for name, arguments in [("wm_rollback", {"run_id": path.stem, "execute": True}), ("wm_verify", {})]:
        message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": name, "arguments": arguments}}
        response = json.loads(handle_message(json.dumps(message), ctx))
        assert response["result"]["isError"] is True


@pytest.mark.parametrize("legacy", ["no_status", "size_only", "invalid_items"])
def test_purge_protects_old_or_unverifiable_batches_before_restore(workspace, legacy):
    root, state, policy = workspace
    m.clean(root, policy, state, {"G4"}, yes=True)
    path, manifest = manifest_for(state)
    if legacy == "no_status":
        manifest.pop("status")
    elif legacy == "size_only":
        manifest["items"][0].update(hashes=None, integrity="size_only")
    else:
        manifest["items"] = "corrupt"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    m.purge(state, older_than_days=-1, yes=True)
    assert (state / "recycle" / path.stem / "cache" / "data").read_bytes() == b"before"


def test_restore_verifies_result_after_move(workspace, monkeypatch):
    root, state, policy = workspace
    m.clean(root, policy, state, {"G4"}, yes=True)
    path, _ = manifest_for(state)
    move = m.shutil.move
    def corrupt(src, dst):
        move(src, dst)
        (Path(dst) / "data").write_bytes(b"change")
    monkeypatch.setattr(m.shutil, "move", corrupt)
    assert not m.rollback(root, state, path.stem)
    assert manifest_for(state)[1]["status"] == "incomplete"


def test_purge_refuses_alias_to_unresolved_batch(tmp_path):
    state = tmp_path / "state"
    original = state / "recycle" / "clean-unresolved"
    original.mkdir(parents=True)
    (original / "data").write_bytes(b"important")
    alias = original.parent / "clean-completed-alias"
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(alias), str(original)], check=True, capture_output=True)
    else:
        alias.symlink_to(original, target_is_directory=True)
    runs = state / "runs"
    runs.mkdir()
    (runs / (alias.name + ".json")).write_text(json.dumps({"status": "completed", "items": []}))
    m.purge(state, older_than_days=-1, yes=True)
    assert (original / "data").read_bytes() == b"important"
    assert any(issue["reason"] == "recycle_alias" for issue in m.recovery_issues(state))


def make_link(alias, target):
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(alias), str(target)], check=True, capture_output=True)
    else:
        alias.symlink_to(target, target_is_directory=True)


def test_clean_refuses_linked_source_before_moving_target(workspace):
    root, state, policy = workspace
    (root / "cache").rename(root / "other")
    make_link(root / "cache", root / "other")
    with pytest.raises(SystemExit, match="linked clean source"):
        m.clean(root, policy, state, {"G4"}, yes=True)
    assert (root / "other" / "data").read_bytes() == b"before"


def test_restore_refuses_linked_batch(workspace):
    root, state, policy = workspace
    m.clean(root, policy, state, {"G4"}, yes=True)
    path, _ = manifest_for(state)
    batch = state / "recycle" / path.stem
    moved = state / "recycle" / "valuable"
    batch.rename(moved)
    make_link(batch, moved)
    with pytest.raises(SystemExit, match="linked recycle source"):
        m.rollback(root, state, path.stem)
    assert (moved / "cache" / "data").read_bytes() == b"before"


def test_restore_refuses_broken_destination_link(workspace):
    root, state, policy = workspace
    m.clean(root, policy, state, {"G4"}, yes=True)
    path, _ = manifest_for(state)
    make_link(root / "cache", root / "missing-target")
    with pytest.raises(SystemExit, match="linked restore target"):
        m.rollback(root, state, path.stem)
    assert not (root / "missing-target").exists()
    assert (state / "recycle" / path.stem / "cache" / "data").read_bytes() == b"before"


def test_hard_exit_preserves_manifest_but_requires_stale_lock_review(workspace):
    root, state, policy = workspace
    code = '''
import os, sys
from pathlib import Path
from workspace_metabolism import core as m
m.plan_items = lambda *a, **kw: [{"path":"cache", "grade":"G4", "cleanup":"auto", "reason":"",
    "is_dir":True, "files":1, "size":6}]
move = m.shutil.move
def crash(src, dst):
    move(src, dst)
    os._exit(77)
m.shutil.move = crash
m.clean(Path(sys.argv[1]), Path(sys.argv[3]), Path(sys.argv[2]), {"G4"}, yes=True)
'''
    process = subprocess.run([sys.executable, "-c", code, str(root), str(state), str(policy)], capture_output=True, timeout=30)
    assert process.returncode == 77
    path, _ = manifest_for(state)
    assert m.verify(state)["recovery_issues"]
    with pytest.raises(SystemExit, match="busy"):
        m.rollback(root, state, path.stem)
    (state / ".wm.lock").unlink()  # fixture only: producer exit was confirmed above
    assert m.rollback(root, state, path.stem)
    assert (root / "cache" / "data").read_bytes() == b"before"
