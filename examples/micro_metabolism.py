"""Micro-metabolism: the end-of-loop question, automated.

An agent (or a human) calls this after observation and before the next plan:
"The files just produced - keep, archive, recycle, or leave for tomorrow's
digestion?" This script runs `wm audit --json`, prints the summary, and shows
a dry-run clean plan. Nothing is deleted.

Usage:
    python examples/micro_metabolism.py [--root DIR] [--state-dir DIR] [--grades G4]

Wire it into a session-end hook so every loop ends with a checkup:
    - Claude Code: SessionEnd hook -> this script
    - Codex: session-end hook -> this script
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def wm(args: list[str], root: str | None, state: str | None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "workspace_metabolism"]
    if root:
        cmd += ["--root", root]
    if state:
        cmd += ["--state-dir", state]
    env = dict(os.environ)
    env.setdefault("PYTHONPATH", str(REPO_ROOT / "src"))
    return subprocess.run(cmd + args, env=env, capture_output=True, text=True, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=None, help="workspace to govern (default: current directory)")
    parser.add_argument("--state-dir", default=None, help="state directory (journal / recycle area)")
    parser.add_argument("--grades", default="G4", help="grades to include in the dry-run plan (default: G4)")
    args = parser.parse_args()

    audit = wm(["audit", "--json"], args.root, args.state_dir)
    if audit.returncode != 0:
        print(audit.stdout, end="")
        print(audit.stderr, end="", file=sys.stderr)
        return audit.returncode
    summary = json.loads(audit.stdout)["summary"]

    print("micro-metabolism (end of loop)")
    print(f"  active files: {summary['files']}   size: {summary['size_mb']} MB"
          f"   candidates: {summary['candidates']}")
    print(f"  recycle: {summary['recycle_files']} files / {summary['recycle_mb']} MB"
          f"   journal: {summary['journal_entries']} entries"
          f"   chain: {'OK' if summary['journal_chain_ok'] else 'BROKEN'}")
    print(f"  health: {summary['health_score']}/100 ({summary['health_grade']})")
    print()
    print("decision (pick one):")
    print("  keep      - leave the files where they are")
    print("  archive   - move them to a G3 path for human review")
    print("  recycle   - let the policy recycle them (see plan below)")
    print("  tomorrow  - leave them for the next digestion run")
    print()
    plan = wm(["clean", "--grades", args.grades], args.root, args.state_dir)
    print("dry-run plan (nothing was moved):")
    print(plan.stdout, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
