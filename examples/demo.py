"""One-command demo for workspace-metabolism.

Builds a throwaway workspace, then runs `status`, `audit` and a dry-run
`clean` against it. Nothing is deleted; the state directory is a temp dir.

Usage:
    python examples/demo.py
"""

from __future__ import annotations

import os
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
    rc |= run(base + ["clean", "--grades", "G4"], env)
    print(f"\ndemo workspace: {demo}\nstate directory: {state}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
