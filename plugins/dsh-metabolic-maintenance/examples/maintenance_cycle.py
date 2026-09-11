"""Isolated, scripted WM lifecycle demonstration; no LLM or production input.

Run with Python 3.11+ and workspace-metabolism installed. All writes and WM
actions target newly created temporary fixtures. Evidence is left for inspection.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

from workspace_metabolism import __version__
from workspace_metabolism.mcp_server import handle_message


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def consumer(path: Path) -> dict:
    """The fixture's actual downstream calculation, with a fixed acceptance rule."""
    try:
        total = sum(json.loads(path.read_text(encoding="utf-8"))["values"])
        return {"total": total, "accepted": total == 18}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {"total": None, "accepted": False, "error": type(exc).__name__}


def run_scenario(base: Path, scenario: str) -> dict:
    if scenario not in {"normal", "fault_injection", "missing_consumer"}:
        raise ValueError("unknown scenario")
    base.mkdir(parents=True, exist_ok=False)  # Never operate on an existing workspace.
    root = base / "workspace"
    (root / "inputs").mkdir(parents=True)
    (root / "scratch").mkdir()
    source = root / "inputs" / "values.json"
    expired = root / "scratch" / "old-report.json"
    for path in (source, expired):
        path.write_text(json.dumps({"values": [7, 11]}), encoding="utf-8")
    old = time.time() - 45 * 86400
    for path in (expired, expired.parent):
        os.utime(path, (old, old))  # Synthetic age, never a production policy change.
    policy = root / "metabolism.json"
    policy.write_text(json.dumps({
        "version": 1, "defaults": {"recycle_retention_days": 30},
        "never_clean": ["inputs", "metabolism.json"],
        "entries": [{"path": "scratch", "grade": "G4", "cleanup": "auto", "retention_days": 30}],
    }), encoding="utf-8")
    ctx = {"root": root, "state_dir": base / "state", "registry_path": policy}
    calls = []

    def call(name: str, **arguments):
        request = {"jsonrpc": "2.0", "id": len(calls) + 1, "method": "tools/call",
                   "params": {"name": name, "arguments": arguments}}
        response = json.loads(handle_message(json.dumps(request), ctx))
        calls.append({"request": request, "response": response})
        if "error" in response or response["result"].get("isError"):
            raise RuntimeError(f"WM tool failed: {name}")
        return response["result"]["content"][0]["text"]

    # The negative fixture intentionally violates a known dependency boundary.
    # It demonstrates recovery; it is NOT what the skill should authorize.
    consumed = expired if scenario == "fault_injection" else source
    report = {"scenario": scenario, "synthetic_fixture": True, "llm_executed": False,
              "wm_version": __version__, "policy_sha256": digest(policy),
              "consumer_version": digest(Path(__file__)), "expected_total": 18,
              "input_sha256": digest(consumed), "wm_calls": calls,
              "supervision_minutes": None, "token_savings": None}
    audit = json.loads(call("wm_audit"))
    report["candidate_count"] = len(audit["candidates"])
    if report["candidate_count"] != 1:
        raise RuntimeError("Fixture should have exactly one due scratch directory")
    call("wm_clean", grades="G4")  # Preview only, as in the DSH tool interface.
    if not expired.exists():
        raise RuntimeError("Preview unexpectedly changed the fixture")
    if scenario == "missing_consumer":
        report.update(outcome="held_missing_consumer", before=None, after=None, recovery=None)
    else:
        report["before"] = consumer(consumed)
        if not report["before"]["accepted"]:
            raise RuntimeError("Baseline consumer failed")
        # Preserve acceptance evidence outside the cleanup scope before acting.
        (base / "before.json").write_text(json.dumps({
            key: report[key] for key in ("before", "input_sha256", "policy_sha256", "consumer_version", "expected_total")
        }, indent=2), encoding="utf-8")
        call("wm_clean", grades="G4", execute=True)
        if expired.exists():
            raise RuntimeError("Cleanup did not move the expected fixture")
        report["after"] = consumer(consumed)
        report["recovery"] = None
        if report["after"]["accepted"]:
            report["outcome"] = "maintained_consumer_verified"
        else:
            manifests = list((ctx["state_dir"] / "runs").glob("clean-*.json"))
            if len(manifests) != 1:
                raise RuntimeError("Expected one cleanup recovery manifest")
            run_id = json.loads(manifests[0].read_text(encoding="utf-8"))["run_id"]
            call("wm_rollback", run_id=run_id)  # Preview.
            call("wm_rollback", run_id=run_id, execute=True)
            report["recovery"] = consumer(consumed)
            if not report["recovery"]["accepted"] or digest(consumed) != report["input_sha256"]:
                raise RuntimeError("Restored consumer or input identity failed verification")
            report["outcome"] = "fault_recovered_consumer_verified"
    report["wm_integrity"] = json.loads(call("wm_verify"))
    integrity_ok = report["wm_integrity"]["chain_ok"] and not report["wm_integrity"]["missing_manifests"]
    if not integrity_ok:
        report["outcome"] = "unresolved_integrity_failure"
    (base / "evidence.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not integrity_ok:
        raise RuntimeError("WM integrity check failed; inspect evidence.json")
    return report


def main() -> None:
    base = Path(tempfile.mkdtemp(prefix="wm-maintenance-example-"))
    print("Scripted synthetic example; no DSH model or production workspace is used.")
    for scenario in ("normal", "fault_injection", "missing_consumer"):
        result = run_scenario(base / scenario, scenario)
        print(f"{scenario}: {result['outcome']}")
    print(f"Inspect evidence and recovery files: {base}")


if __name__ == "__main__":
    main()
