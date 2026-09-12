"""Synthetic closed-task retention rehearsal; does not run or connect Symphony.

Creates only fresh temporary workspaces and retains their evidence. Task state is
an input label, not deletion permission. Never accepts an existing directory.
"""

from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from workspace_metabolism.claim_backend import JsonClaimBackend, git_clean_path
from workspace_metabolism.claim_guard import ClaimGuard


class LostReceiptBackend(JsonClaimBackend):
    def save(self, registry):
        if any(c.get("wm_guard", {}).get("receipts") for c in registry["claims"]):
            raise OSError("synthetic receipt storage failure")
        super().save(registry)


def run_case(base, scenario):
    root = base / scenario
    root.mkdir()
    output_dir = root / "outputs"
    output_dir.mkdir()
    subprocess.run(["git", "init", "--quiet", str(root)], check=True, capture_output=True)
    policy = root / "metabolism.json"
    policy.write_text(json.dumps({"version": 1, "defaults": {}, "entries": [
        {"path": "outputs", "grade": "G4", "cleanup": "auto", "retention_days": 1}
    ]}), encoding="utf-8")
    backend_type = LostReceiptBackend if scenario == "lost-receipt" else JsonClaimBackend
    backend = backend_type(root)
    guard = ClaimGuard(root, backend, authorize=lambda p: p == "outputs/review.md",
                       clean_base=lambda p: git_clean_path(root, p),
                       clock=(lambda: 1) if scenario == "expired" else time.time)
    claim = guard.begin(task="Document a maintenance result", files=["outputs/review.md"])
    try:
        guard.write(claim["claim_id"], claim["session_id"], path="outputs/review.md",
                    text="# Maintenance Review\n\nEvidence must survive an uncertain write.\n",
                    operation_id="review-1")
    except OSError:
        if scenario != "lost-receipt":
            raise
    if scenario == "delivered":
        subprocess.run(["git", "-C", str(root), "add", "--", "outputs/review.md"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.name=WM Rehearsal",
                        "-c", "user.email=rehearsal@example.invalid", "-c", "core.hooksPath=/dev/null",
                        "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Deliver synthetic review"],
                       check=True, capture_output=True)
        guard.finish(claim["claim_id"], claim["session_id"],
                     delivered=lambda c: all(git_clean_path(root, p) for p in c["files"]))
        # Core cleanup independently protects Git-tracked files. Use a separate
        # disposable untracked output to verify normal cleanup can still proceed.
        (root / "scratch").mkdir()
        (root / "scratch/old.txt").write_text("disposable", encoding="utf-8")
        data = json.loads(policy.read_text(encoding="utf-8"))
        data["entries"].append({"path": "scratch", "grade": "G4", "cleanup": "auto", "retention_days": 1})
        policy.write_text(json.dumps(data), encoding="utf-8")
    target = output_dir / "review.md"
    old = time.time() - 3 * 86400
    for directory in [output_dir] + ([root / "scratch"] if scenario == "delivered" else []):
        for path in [*directory.iterdir(), directory]:
            os.utime(path, (old, old))
    before_hash = hashlib.sha256(target.read_bytes()).hexdigest()
    before_registry = backend.path.read_bytes()
    state = base / (scenario + "-state")
    results = []
    for _ in range(2):
        completed = subprocess.run([sys.executable, "-m", "workspace_metabolism", "--root", str(root),
                                    "--state-dir", str(state), "clean", "--grades", "G4", "--yes"],
                                   capture_output=True, text=True, encoding="utf-8", timeout=30)
        if completed.returncode:
            raise RuntimeError("rehearsal cleanup did not complete")
        results.append(completed.stdout)
    retained = target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == before_hash
    unchanged = backend.path.read_bytes() == before_registry
    pending = backend.load()["claims"][0]["wm_guard"]["pending"] is not None
    normal_cleanup = scenario != "delivered" or not (root / "scratch").exists()
    claim_blocked = scenario != "delivered" and all("claim ownership" in text for text in results)
    return {"scenario": scenario, "external_task_state": "closed (synthetic)",
            "cleanup_processes": 2, "document_retained_unchanged": retained,
            "registry_unchanged": unchanged, "pending_intent_retained": pending,
            "normal_cleanup_ok": normal_cleanup, "claim_blocked": claim_blocked,
            "ok": retained and unchanged and normal_cleanup and (claim_blocked or scenario == "delivered")}


def main():
    base = Path(tempfile.mkdtemp(prefix="wm-claim-cleanup-"))
    with redirect_stdout(io.StringIO()):
        cases = [run_case(base, scenario) for scenario in ("active", "expired", "lost-receipt", "delivered")]
    result = {"kind": "synthetic task-lifecycle rehearsal; not Symphony integration",
              "cases": cases, "ok": all(c["ok"] for c in cases),
              "automatic_reconnect": False, "trading_system_changed": False}
    report = base / "result.json"
    report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(report), **result}, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
