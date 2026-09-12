import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from workspace_metabolism.claim_backend import JsonClaimBackend, git_clean_path
from workspace_metabolism.claim_guard import ClaimGuard, ClaimRejected


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def setup(root):
    git(root, "init")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    (root / "app.py").write_text("value = 1\n", encoding="utf-8")
    (root / ".gitignore").write_text(".coordination/\nignored.py\n")
    (root / "metabolism.json").write_text(json.dumps({
        "version": 1, "entries": [], "ai_governance": {"default": "deny", "actions": {
            "write": {"allow": True, "requires_preview": True}
        }},
    }))
    git(root, "add", "app.py", ".gitignore", "metabolism.json")
    git(root, "commit", "-m", "baseline")


def cli(root, *args, session=None):
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    if session:
        env["WM_CLAIM_SESSION"] = session
    else:
        env.pop("WM_CLAIM_SESSION", None)
    return subprocess.run([sys.executable, "-m", "workspace_metabolism", "--root", str(root),
                           "--state-dir", str(root.parent / "state"), "claim", *args],
                          capture_output=True, text=True, encoding="utf-8", env=env, timeout=20)


def test_cli_end_to_end_and_reopen_registry(tmp_path):
    setup(tmp_path)
    result = cli(tmp_path, "begin", "--task", "fix", "--file", "app.py")
    assert result.returncode == 0, result.stdout + result.stderr
    claim = json.loads(result.stdout)
    replacement = tmp_path / "replacement.txt"
    replacement.write_text("value = 2\n")
    args = ("write", claim["claim_id"], "--file", "app.py", "--content-file", str(replacement), "--operation-id", "op1")
    assert cli(tmp_path, *args).returncode == 2
    assert cli(tmp_path, *args, session=claim["session_id"]).returncode == 2  # policy preview missing
    result = cli(tmp_path, *args, "--preview", session=claim["session_id"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "app.py").read_text() == "value = 2\n"
    assert cli(tmp_path, "finish", claim["claim_id"], session=claim["session_id"]).returncode == 2
    git(tmp_path, "add", "app.py")
    git(tmp_path, "commit", "-m", "fix")
    assert cli(tmp_path, "finish", claim["claim_id"], session=claim["session_id"]).returncode == 0
    backend = JsonClaimBackend(tmp_path)
    assert backend.load()["claims"][0]["status"] == "done"


def test_foreign_registry_is_not_modified(tmp_path):
    setup(tmp_path)
    directory = tmp_path / ".coordination"
    directory.mkdir()
    path = directory / "registry.json"
    original = b'{"version":1,"claims":[]}'
    path.write_bytes(original)
    assert cli(tmp_path, "begin", "--task", "bad", "--file", "app.py").returncode == 2
    assert path.read_bytes() == original
    assert sorted(p.name for p in directory.iterdir()) == ["registry.json"]


def test_cli_ignored_existing_file_is_not_clean_baseline(tmp_path):
    setup(tmp_path)
    (tmp_path / "ignored.py").write_text("another task's artifact")
    result = cli(tmp_path, "begin", "--task", "bad", "--file", "ignored.py")
    assert result.returncode == 2
    assert "baseline_unattributed" in result.stdout


def test_process_concurrency_on_real_backend(tmp_path):
    setup(tmp_path)
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    command = [sys.executable, "-m", "workspace_metabolism", "--root", str(tmp_path),
               "claim", "begin", "--task", "race", "--file", "app.py"]
    processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env) for _ in range(4)]
    codes = []
    for process in processes:
        process.communicate(timeout=20)
        codes.append(process.returncode)
    assert sorted(codes) == [0, 2, 2, 2]
    assert len(JsonClaimBackend(tmp_path).load()["claims"]) == 1


def test_corrupt_json_is_not_reset(tmp_path):
    setup(tmp_path)
    directory = tmp_path / ".coordination"
    directory.mkdir()
    path = directory / "registry.json"
    original = b'{"wm_claim_backend":1,"claims":['
    path.write_bytes(original)
    result = cli(tmp_path, "begin", "--task", "blocked", "--file", "app.py")
    assert result.returncode == 2
    assert path.read_bytes() == original
    assert sorted(p.name for p in directory.iterdir()) == ["registry.json"]


@pytest.mark.parametrize("stage", ["replacement", "receipt"])
def test_real_storage_pending_survives_backend_reopen(tmp_path, monkeypatch, stage):
    setup(tmp_path)
    backend = JsonClaimBackend(tmp_path)
    guard = ClaimGuard(tmp_path, backend, authorize=lambda p: True,
                       clean_base=lambda p: git_clean_path(tmp_path, p))
    claim = guard.begin(task="recovery test", files=["app.py"])
    save = backend.save
    calls = 0

    def failing_save(registry):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("receipt failure")
        save(registry)

    def failing_replace(*args):
        raise OSError("replacement failure")

    if stage == "receipt":
        monkeypatch.setattr(backend, "save", failing_save)
    else:
        monkeypatch.setattr(guard, "_replace", failing_replace)
    args = dict(path="app.py", text="value = 2\n", operation_id="op")
    with pytest.raises(OSError):
        guard.write(claim["claim_id"], claim["session_id"], **args)
    reopened_backend = JsonClaimBackend(tmp_path)
    reopened = ClaimGuard(tmp_path, reopened_backend, authorize=lambda p: True,
                          clean_base=lambda p: git_clean_path(tmp_path, p))
    pending = reopened_backend.load()["claims"][0]["wm_guard"]["pending"]
    assert pending["before"]["data"]
    with pytest.raises(ClaimRejected, match="recovery_required"):
        reopened.write(claim["claim_id"], claim["session_id"], **args)
    assert (tmp_path / "app.py").read_text() == (
        "value = 2\n" if stage == "receipt" else "value = 1\n")
    recovered = cli(tmp_path, "recover", claim["claim_id"], session=claim["session_id"])
    assert recovered.returncode == 0, recovered.stdout
    assert json.loads(recovered.stdout)["files_written"] == 0


def test_cli_resume_rotates_session(tmp_path):
    setup(tmp_path)
    claim = json.loads(cli(tmp_path, "begin", "--task", "resume", "--file", "app.py").stdout)
    resumed = cli(tmp_path, "resume", claim["claim_id"], session=claim["session_id"])
    assert resumed.returncode == 0, resumed.stdout
    next_session = json.loads(resumed.stdout)["session_id"]
    assert next_session != claim["session_id"]
    assert cli(tmp_path, "renew", claim["claim_id"], session=claim["session_id"]).returncode == 2
    assert cli(tmp_path, "renew", claim["claim_id"], session=next_session).returncode == 0
