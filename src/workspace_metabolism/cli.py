"""Command-line interface for workspace-metabolism."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .core import (
    audit,
    clean,
    default_state_dir,
    parse_window,
    purge,
    rollback,
    status,
    verify,
)


def _resolve_state_dir(root: Path, raw: str | None) -> Path:
    if raw:
        sd = Path(raw)
        return (sd if sd.is_absolute() else root / sd).resolve()
    return default_state_dir().resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wm",
        description=(
            "Policy-driven file lifecycle management: classify, audit, "
            "clean (recyclable), rollback, purge with a hash-chained audit trail."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--root",
        default=os.getcwd(),
        help="workspace to govern (default: current directory)",
    )
    parser.add_argument(
        "--state-dir",
        default=None,
        help=(
            "directory for the journal, recycle area, run manifests and reports "
            "(default: system cache dir, outside the workspace)"
        ),
    )
    parser.add_argument(
        "--protected-window",
        default=None,
        metavar="HH:MM-HH:MM",
        help="weekday window (local time) during which protected entries are skipped, e.g. 09:25-15:00",
    )
    parser.add_argument(
        "--registry",
        default=None,
        help="path to the policy registry (JSON); required for audit/clean/status",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_audit = sub.add_parser("audit", help="read-only health check; writes a report")
    p_audit.add_argument("--dupes", action="store_true", help="also scan for possible duplicates")
    p_audit.add_argument("--auto", action="store_true", help="mark the run as scheduled")
    p_audit.add_argument("--json", action="store_true", help="print the report as JSON (for agent integration)")

    p_clean = sub.add_parser("clean", help="clean by grade (moves to recycle area first)")
    p_clean.add_argument("--grades", required=True, help="comma-separated grades, e.g. G4 or G3,G4")
    p_clean.add_argument("--yes", action="store_true", help="execute instead of dry-run")
    p_clean.add_argument("--approve", action="store_true", help="mark G3 cleanup as approved")
    p_clean.add_argument("--approver", help="approver name/identity (required for G3)")
    p_clean.add_argument("--auto", action="store_true", help="mark the run as scheduled")

    p_roll = sub.add_parser("rollback", help="restore one cleanup run from the recycle area")
    p_roll.add_argument("run_id")
    p_roll.add_argument("--dry-run", action="store_true")

    p_purge = sub.add_parser("purge", help="delete expired recycle batches (the only real delete)")
    p_purge.add_argument("--older-than", type=int, default=30, help="age threshold in days (default: 30)")
    p_purge.add_argument("--yes", action="store_true", help="execute instead of preview")
    p_purge.add_argument("--auto", action="store_true", help="mark the run as scheduled")

    sub.add_parser("verify", help="verify the journal hash chain and run manifests")

    p_status = sub.add_parser("status", help="workspace and state overview")

    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    state_dir = _resolve_state_dir(root, args.state_dir)
    window = parse_window(args.protected_window)
    operator = "auto" if getattr(args, "auto", False) else "manual"
    registry_path = Path(args.registry) if args.registry else None
    if args.command in ("audit", "clean", "status") and registry_path is None:
        raise SystemExit("--registry is required for audit/clean/status (see examples/registry.example.json)")

    if args.command == "audit":
        report, report_path = audit(
            root,
            registry_path,
            state_dir,
            dupes=args.dupes,
            operator=operator,
        )
        if getattr(args, "json", False):
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"audit done: {len(report['candidates'])} candidate(s), {len(report['unregistered'])} unregistered")
            print(f"report: {report_path}")
    elif args.command == "clean":
        grades = {g.strip().upper() for g in args.grades.split(",") if g.strip().upper() in {"G1", "G2", "G3", "G4"}}
        if not grades:
            raise SystemExit("--grades must include G3 and/or G4")
        if "G3" in grades and not args.approve:
            raise SystemExit("G3 cleanup requires --approve (human approval)")
        clean(
            root,
            registry_path,
            state_dir,
            grades,
            yes=args.yes,
            approve=args.approve,
            approver=args.approver,
            operator=operator,
            window=window,
        )
    elif args.command == "rollback":
        rollback(root, state_dir, args.run_id, dry=args.dry_run, operator=operator)
    elif args.command == "purge":
        purge(state_dir, older_than_days=args.older_than, yes=args.yes, operator=operator)
    elif args.command == "verify":
        result = verify(state_dir)
        print(f"journal: {result['entries']} entries, hash chain {'OK' if result['chain_ok'] else 'BROKEN (seq ' + str(result['broken_at']) + ')'}")
        if result["missing_manifests"]:
            print(f"missing run manifests: {', '.join(result['missing_manifests'])}")
        for e in result["last"]:
            print(f"  #{e['seq']} [{e['ts']}] {e['action']} operator={e['operator']} run_id={e.get('run_id') or e.get('batches') or '-'}")
    elif args.command == "status":
        status(root, registry_path, state_dir)
    return 0
