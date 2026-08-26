"""One-command demo for workspace-metabolism.

Builds a throwaway workspace, then shows the difference between the usual
blind-delete fix and the wm way (recycle + rollback + journal):

1. status / audit          - read-only overview and health check
2. the usual fix           - a blind delete on one file: gone, no undo, no record
3. the wm way              - clean moves items to the recycle area (journaled),
                             rollback restores them after an integrity check
4. verify                  - the journal hash chain still holds after all of it

Nothing outside the demo/state temp dirs is touched. Usage:

    python examples/demo.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
REGISTRY = HERE / "registry.example.json"


def make_old(path: Path, days: int = 45) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for i in range(3):
        (path / f"file{i}.log").write_text("x" * 1000, encoding="utf-8")
    old = datetime.now().timestamp() - days * 86400
    for f in path.rglob("*"):
        try:
            os.utime(f, (old, old))
        except OSError:
            pass
    try:
        os.utime(path, (old, old))
    except OSError:
        pass


def build(demo: Path) -> None:
    (demo / "src").mkdir(parents=True)
    (demo / "src" / "main.py").write_text("print('hello from the demo')\n", encoding="utf-8")
    (demo / "docs").mkdir()
    (demo / "docs" / "README.md").write_text("# demo workspace\n", encoding="utf-8")
    for name in ("logs", "tmp", "cache", "archive"):
        make_old(demo / name)


def run(cmd: list[str], env: dict) -> int:
    print("$ " + " ".join(cmd))
    return subprocess.call(cmd, env=env)


def run_capture(cmd: list[str], env: dict) -> tuple[int, str]:
    print("$ " + " ".join(cmd))
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip())
    return proc.returncode, proc.stdout


def main() -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    demo = Path(tempfile.mkdtemp(prefix="wm-demo-")) / "workspace"
    state = Path(tempfile.mkdtemp(prefix="wm-state-"))
    build(demo)
    base = [
        sys.executable,
        "-m",
        "workspace_metabolism",
        "--root",
        str(demo),
        "--registry",
        str(REGISTRY),
        "--state-dir",
        str(state),
    ]
    rc = 0
    rc |= run(base + ["status"], env)
    print()
    rc |= run(base + ["audit"], env)
    print()

    print("=" * 62)
    print("The usual fix: a blind cleanup script")
    print("=" * 62)
    victim = demo / "cache" / "file0.log"
    print(f"$ rm -f {victim.relative_to(demo)}   # direct delete, no policy, no journal")
    victim.unlink()
    # deleting a file bumps the parent directory's mtime, which would make
    # cache/ look "fresh" to an idle-based policy; restore the old stamp so
    # the demo stays deterministic (a real blind-delete script leaves the
    # same side effect, by the way)
    old = datetime.now().timestamp() - 45 * 86400
    os.utime(victim.parent, (old, old))
    print(f"gone: {victim.relative_to(demo)} is deleted in place.")
    print("No recycle area, no hash record, no undo. If the pattern was wrong,")
    print("a valid file is gone forever - nobody can tell you what happened.\n")

    print("=" * 62)
    print("The wm way: policy -> recycle -> rollback")
    print("=" * 62)
    rc_clean, clean_out = run_capture(base + ["clean", "--grades", "G4", "--yes"], env)
    rc |= rc_clean
    # clean prints:  done: N/M item(s) moved to recycle. rollback: wm rollback <run_id>
    run_id = ""
    for line in clean_out.splitlines():
        match = re.search(r"rollback: wm rollback (\S+)", line)
        if match:
            run_id = match.group(1)
    if run_id:
        print()
        rc |= run(base + ["rollback", run_id], env)
        print()
    else:
        print("(no run id captured; skipping rollback step)")
        rc = 1

    print()
    print("=" * 62)
    print("The scoreboard")
    print("=" * 62)
    cache_files = sorted(p.name for p in (demo / "cache").iterdir())
    print(f"cache/ now holds: {', '.join(cache_files)}")
    print("- file0.log is still missing: the blind delete has no undo.")
    print("- everything wm moved to the recycle area came back, integrity-checked.")
    rc |= run(base + ["verify"], env)
    print()
    print(f"demo workspace: {demo}\nstate directory: {state}")
    print()
    print("Like the idea? Break it on a weird directory structure and tell us:")
    print("  https://github.com/metabolism-tools/workspace-metabolism  (issues & stars welcome)")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
