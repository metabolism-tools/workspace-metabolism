"""Run a synthetic, persistent multi-process claim rehearsal. Never uses trading data."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def run_demo():
    run_dir = Path(tempfile.mkdtemp(prefix="wm-claim-demo-"))
    root = run_dir / "workspace"
    root.mkdir()
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"),
               PYTHONIOENCODING="utf-8")
    env.pop("WM_CLAIM_SESSION", None)
    # This is a newly created synthetic repository, never a user's existing checkout.
    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args], check=True,
                              capture_output=True, timeout=20)

    git("init")
    git("config", "user.name", "WM Synthetic Demo")
    git("config", "user.email", "demo@example.invalid")
    git("config", "commit.gpgsign", "false")
    git("config", "core.autocrlf", "false")
    hooks = run_dir / "empty-hooks"
    hooks.mkdir()
    git("config", "core.hooksPath", str(hooks))
    (root / "reader.py").write_bytes(b"mode = 'baseline'\n")
    (root / "other.py").write_bytes(b"value = 1\n")
    (root / ".gitignore").write_bytes(b".coordination/\n")
    (root / "metabolism.json").write_text(json.dumps({
        "version": 1, "entries": [], "ai_governance": {
            "default": "deny", "actions": {"write": {"allow": True, "requires_preview": True}}
        },
    }), encoding="utf-8")
    git("add", "reader.py", "other.py", ".gitignore", "metabolism.json")
    git("commit", "-m", "Synthetic baseline")
    command = [sys.executable, "-m", "workspace_metabolism", "--root", str(root),
               "--state-dir", str(run_dir / "state"), "claim"]
    checks = {}

    def cli(*args, session=None, expected=0):
        child_env = dict(env)
        if session:
            child_env["WM_CLAIM_SESSION"] = session
        result = subprocess.run([*command, *args], env=child_env, capture_output=True,
                                text=True, encoding="utf-8", timeout=20)
        if result.returncode != expected:
            raise RuntimeError(f"Unexpected claim exit: {result.returncode}; {result.stderr}")
        return json.loads(result.stdout)

    processes = [subprocess.Popen([*command, "begin", "--task", f"synthetic-{i}",
                                   "--file", "reader.py"], env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE) for i in range(4)]
    results = []
    try:
        for process in processes:
            out, err = process.communicate(timeout=20)
            results.append((process.returncode, json.loads(out)))
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate()
    if sorted(code for code, _ in results) != [0, 2, 2, 2]:
        raise RuntimeError("Concurrent claim exclusion failed")
    checks["four_processes_one_owner"] = True
    owner = next(value for code, value in results if code == 0)
    claim, session = owner["claim_id"], owner["session_id"]
    replacement = run_dir / "replacement.txt"
    replacement.write_bytes(b"mode = 'guarded'\n")
    write_args = ["write", claim, "--file", "reader.py", "--content-file", str(replacement),
                  "--operation-id", "demo-write"]
    original = (root / "reader.py").read_bytes()
    cli(*write_args, session="different-session", expected=2)
    checks["other_session_denied"] = (root / "reader.py").read_bytes() == original
    cli(*write_args, session=session, expected=2)
    checks["policy_still_required"] = (root / "reader.py").read_bytes() == original
    cli("write", claim, "--file", "other.py", "--content-file", str(replacement),
        "--operation-id", "wrong-scope", "--preview", session=session, expected=2)
    checks["unclaimed_path_denied"] = (root / "other.py").read_bytes() == b"value = 1\n"
    receipt = cli(*write_args, "--preview", session=session)
    checks["authorized_write_succeeded"] = (root / "reader.py").read_bytes() == replacement.read_bytes()
    checks["replay_does_not_write_again"] = cli(*write_args, "--preview", session=session).get("replayed") is True
    cli("finish", claim, session=session, expected=2)
    checks["uncommitted_delivery_denied"] = True
    git("add", "reader.py")
    git("commit", "-m", "Synthetic guarded change")
    checks["committed_delivery_closed"] = cli("finish", claim, session=session)["status"] == "closed"

    second = cli("begin", "--task", "external-change-control", "--file", "other.py")
    (root / "other.py").write_bytes(b"another session's work\n")
    cli("write", second["claim_id"], "--file", "other.py", "--content-file", str(replacement),
        "--operation-id", "external-change", "--preview", session=second["session_id"], expected=2)
    checks["external_change_preserved"] = (root / "other.py").read_bytes() == b"another session's work\n"

    registry = json.loads((root / ".coordination" / "registry.json").read_text(encoding="utf-8"))
    stored = next(c for c in registry["claims"] if c["id"] == claim)
    checks["receipt_and_original_retained"] = (
        stored["status"] == "done" and len(stored["wm_guard"]["receipts"]) == 1
        and bool(stored["wm_guard"]["receipts"][0]["before"]["data"])
    )
    if not all(checks.values()):
        raise RuntimeError(f"Failed checks: {[k for k, v in checks.items() if not v]}")
    report = {
        "status": "passed", "scope": "isolated synthetic workspace, not production integration",
        "at": datetime.now(timezone.utc).isoformat(), "python": sys.version.split()[0],
        "run_dir": str(run_dir), "checks": checks,
        "receipt_after_sha256": receipt["after"]["sha256"],
        "observed_after_sha256": hashlib.sha256((root / "reader.py").read_bytes()).hexdigest(),
        "production_files_modified": False,
        "retained_negative_control": "other.py remains changed and claimed; not auto-restored",
    }
    (run_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
