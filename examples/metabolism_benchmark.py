"""Reproducible 30-loop experiment behind the metabolic narrative.

Simulates 30 agent loops in two identical workspaces: one governed by
workspace-metabolism, one not. Each loop leaves eight byproduct files behind
(drafts, patches, lock files, caches, test stubs, debug output...). In the
governed workspace every loop ends with a policy-driven `clean`; in the
ungoverned workspace the byproducts simply pile up.

Prints the exact numbers quoted in docs/narrative.md and docs/launch-blog-zh.md.
Nothing real is deleted; both workspaces and state directories are temp dirs.

Usage:
    python examples/metabolism_benchmark.py
"""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
SRC = REPO_ROOT / "src"

LOOPS = 30
FILES_PER_LOOP = 8
RETENTION_DAYS = 7
AGE_DAYS = 8  # byproducts are "abandoned" after 8 simulated days
SEED = 20260815

# (kind, extension, size in bytes) - typical loop byproducts
KINDS = [
    ("draft", "py", 1800),
    ("patch", "txt", 900),
    ("lock", "txt", 300),
    ("cache", "bin", 5000),
    ("test_draft", "py", 2400),
    ("debug", "json", 1500),
    ("notes", "md", 700),
    ("tmp_output", "csv", 1200),
]

REGISTRY = {
    "version": 1,
    "defaults": {
        "recycle_retention_days": 30,
        "max_item_mb": 2560,
        "disk_alert_free_gb": 20,
        "disk_alert_free_pct": 15,
        "dupe_scan_dirs": ["tmp", "cache"],
    },
    "never_clean": [".git", "README.md", "src"],
    "entries": [
        {
            "path": "loops",
            "grade": "G4",
            "cleanup": "auto",
            "retention_days": RETENTION_DAYS,
            "scope": "files_only",
        }
    ],
}


def build_workspace(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "src").mkdir(exist_ok=True)
    (root / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (root / "README.md").write_text("# benchmark workspace\n", encoding="utf-8")
    (root / "loops").mkdir(exist_ok=True)


def make_batch(root: Path, loop: int, rng: random.Random) -> list[Path]:
    """Create one loop's byproducts, backdated past the retention period."""
    old = time.time() - AGE_DAYS * 86400
    created: list[Path] = []
    for kind, ext, size in KINDS:
        path = root / "loops" / f"run{loop:02d}_{kind}.{ext}"
        path.write_bytes(bytes(rng.randrange(256) for _ in range(size)))
        os.utime(path, (old, old))
        created.append(path)
    return created


def wm(
    args: list[str],
    root: Path,
    state: Path,
    registry: Path,
    env: dict,
) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        "-m",
        "workspace_metabolism",
        "--root",
        str(root),
        "--registry",
        str(registry),
        "--state-dir",
        str(state),
    ] + args
    return subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8")


def audit_summary(
    root: Path,
    state: Path,
    registry: Path,
    env: dict,
) -> tuple[dict, float]:
    """Run `wm audit --json` three times and keep the best wall time."""
    report: dict = {}
    best_ms: float | None = None
    for _ in range(3):
        t0 = time.perf_counter()
        cp = wm(["audit", "--json"], root, state, registry, env)
        elapsed = (time.perf_counter() - t0) * 1000
        if cp.returncode != 0:
            print(cp.stdout)
            print(cp.stderr)
            raise SystemExit(f"audit failed on {root}")
        report = json.loads(cp.stdout)
        best_ms = elapsed if best_ms is None or elapsed < best_ms else best_ms
    return report, best_ms


def main() -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")

    tmp = Path(tempfile.mkdtemp(prefix="wm-bench-"))
    governed = tmp / "governed"
    ungoverned = tmp / "ungoverned"
    g_state = tmp / "state-governed"
    u_state = tmp / "state-ungoverned"
    registry = tmp / "registry.json"
    registry.write_text(json.dumps(REGISTRY, ensure_ascii=False), encoding="utf-8")

    for root, state in ((governed, g_state), (ungoverned, u_state)):
        build_workspace(root)
        state.mkdir(parents=True, exist_ok=True)

    # --- governed workspace: every loop ends with clean ---------------------
    rng = random.Random(SEED)
    originals: dict[str, bytes] = {}
    run_ids: list[str] = []
    for i in range(LOOPS):
        # clean run ids are unique per microsecond; a small pause keeps the
        # simulation honest even on filesystems where clocks tick slowly
        if i > 0:
            time.sleep(1.05)
        for path in make_batch(governed, i, rng):
            originals[path.name] = path.read_bytes()
        cp = wm(["clean", "--grades", "G4", "--yes"], governed, g_state, registry, env)
        if cp.returncode != 0:
            print(cp.stdout)
            print(cp.stderr)
            return 1
        for line in cp.stdout.splitlines():
            if "rollback: wm rollback" in line:
                run_ids.append(line.strip().split()[-1])

    # --- ungoverned workspace: identical loops, no cleanup ------------------
    rng = random.Random(SEED)
    for i in range(LOOPS):
        make_batch(ungoverned, i, rng)

    # --- final measurements --------------------------------------------------
    g_report, g_audit_ms = audit_summary(governed, g_state, registry, env)
    u_report, u_audit_ms = audit_summary(ungoverned, u_state, registry, env)

    cp = wm(["verify"], governed, g_state, registry, env)
    if cp.returncode != 0:
        print(cp.stdout)
        print(cp.stderr)
        return 1

    # --- rollback: recover loop 00's draft in the governed workspace --------
    target = "run00_draft.py"
    rollback_run = run_ids[0]
    t0 = time.perf_counter()
    cp = wm(["rollback", rollback_run], governed, g_state, registry, env)
    rollback_ms = (time.perf_counter() - t0) * 1000
    if cp.returncode != 0:
        print(cp.stdout)
        print(cp.stderr)
        return 1
    restored = governed / "loops" / target
    hash_ok = restored.exists() and restored.read_bytes() == originals[target]

    result = {
        "loops": LOOPS,
        "files_per_loop": FILES_PER_LOOP,
        "retention_days": RETENTION_DAYS,
        "governed": {
            "workspace_files": g_report["summary"]["files"],
            "workspace_size_mb": g_report["summary"]["size_mb"],
            "candidates": g_report["summary"]["candidates"],
            "recycle_files": g_report["summary"]["recycle_files"],
            "recycle_mb": g_report["summary"]["recycle_mb"],
            "journal_entries": g_report["summary"]["journal_entries"],
            "journal_chain_ok": g_report["summary"]["journal_chain_ok"],
            "audit_ms": round(g_audit_ms, 1),
        },
        "ungoverned": {
            "workspace_files": u_report["summary"]["files"],
            "workspace_size_mb": u_report["summary"]["size_mb"],
            "candidates": u_report["summary"]["candidates"],
            "audit_ms": round(u_audit_ms, 1),
        },
        "rollback": {
            "run_id": rollback_run,
            "restored_file": target,
            "hash_ok": hash_ok,
            "ms": round(rollback_ms, 1),
        },
        "tmp_dir": str(tmp),
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()
    print("governed  :", "clean each loop; recycle holds",
          result["governed"]["recycle_files"], "files;",
          "verify:", "chain OK" if result["governed"]["journal_chain_ok"] else "BROKEN",
          "| rollback hash_ok =", result["rollback"]["hash_ok"])
    print("ungoverned:", result["ungoverned"]["workspace_files"], "files,",
          result["ungoverned"]["workspace_size_mb"], "MB,",
          result["ungoverned"]["candidates"], "expired candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
