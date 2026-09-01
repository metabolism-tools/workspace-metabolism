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
    doctor,
    explain,
    govern,
    health_score,
    init_policy,
    parse_window,
    POLICY_FILENAMES,
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


def _resolve_registry(root: Path, raw: str | None) -> Path | None:
    """Explicit --registry wins; otherwise auto-discover the standard file."""
    if raw:
        return Path(raw).resolve()
    for name in POLICY_FILENAMES:
        candidate = root / name
        if candidate.exists():
            return candidate.resolve()
    return None


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

    p_init = sub.add_parser("init", help="scaffold a metabolism.json policy file (like `git init`)")
    p_init.add_argument("--force", action="store_true", help="overwrite an existing policy file")
    p_init.add_argument(
        "--file",
        default="metabolism.json",
        choices=list(POLICY_FILENAMES),
        help="policy file name (default: metabolism.json)",
    )

    p_explain = sub.add_parser("explain", help="explain what the policy says about a path")
    p_explain.add_argument("path", help="relative path inside the workspace")
    p_explain.add_argument("--json", action="store_true", help="print the explanation as JSON")

    p_health = sub.add_parser("health", help="workspace health score (0-100)")
    p_health.add_argument("--json", action="store_true", help="print the score breakdown as JSON")
    p_health.add_argument("--badge", action="store_true", help="print a shields.io badge JSON")

    p_doctor = sub.add_parser("doctor", help="check workspace readiness without changing files")
    p_doctor.add_argument("--json", action="store_true", help="print the check as JSON")

    p_govern = sub.add_parser("govern", help="check whether an AI action is allowed by policy")
    p_govern.add_argument("action", help="read, write, execute, delete or network")
    p_govern.add_argument("--path", action="append", default=[], help="path involved in the action; repeatable")
    p_govern.add_argument("--preview", action="store_true", help="confirm that a dry-run or preview was completed")
    p_govern.add_argument("--approve-by", help="human approver identity")
    p_govern.add_argument("--json", action="store_true", help="print the decision as JSON")

    sub.add_parser("mcp", help="run the MCP stdio server so agents can run micro-metabolism")

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
    registry_path = _resolve_registry(root, args.registry)

    if args.command == "init":
        target = root / args.file
        created = init_policy(root, target, force=args.force)
        print(f"policy created: {created}")
        print("next steps:")
        print("  wm audit      - first checkup (read-only)")
        print("  wm status     - workspace and state overview")
        print("  wm health     - workspace health score (0-100)")
        print("  wm explain <path> - why a path is graded the way it is")
        print("edit the policy file and commit it like any source file")
        return 0

    if args.command == "doctor":
        result = doctor(root, registry_path, state_dir)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            checks = [
                ("workspace writable", result["root_writable"]),
                ("state directory writable", result["state_dir_writable"]),
                ("policy present", result["registry_present"]),
                ("policy valid", result["registry_valid"]),
                ("state lock free", not result["lock_busy"]),
            ]
            for label, ok in checks:
                print(f"{'OK' if ok else 'FAIL'}: {label}")
            if result["git_repo"]:
                print(f"INFO: git repository, {result['git_tracked_files']} tracked file(s)")
            if result["registry_error"]:
                print(f"ERROR: {result['registry_error']}")
            if result["missing_registry"]:
                print("NEXT: run `wm init` or pass --registry")
            if result["candidates"] is not None:
                print(
                    f"INFO: {result['candidates']} candidate(s), "
                    f"{result['unregistered']} unregistered top-level item(s), "
                    f"{result['sensitive']} sensitive file(s)"
                )
            if result["workspace_on_memory"]:
                print("WARNING: workspace is on a memory-backed filesystem")
            if result["state_on_memory"]:
                print("WARNING: state directory is on a memory-backed filesystem")
        return 0 if result["root_writable"] and result["state_dir_writable"] and result["registry_valid"] and not result["lock_busy"] else 1

    if args.command in ("audit", "clean", "status", "explain", "health", "govern") and registry_path is None:
        raise SystemExit(
            "no policy file found (metabolism.json / .wm.json); "
            "run `wm init` first or pass --registry"
        )

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
            if report.get("sensitive"):
                print(f"  warning: {len(report['sensitive'])} sensitive file(s) found (see report)")
            if report.get("git", {}).get("repo"):
                print(f"  git repo: {report['git']['tracked_files']} tracked file(s) treated as controlled")
            mem = report.get("memory") or {}
            if mem.get("candidates_on_memory"):
                print(
                    f"  memory-backed: {mem['candidates_on_memory']} candidate(s), "
                    f"{mem['candidates_on_memory_mb']} MB on RAM-backed mounts "
                    "(costs RAM, not just disk; see report)"
                )
            elif mem.get("workspace"):
                ws = mem["workspace"]
                print(
                    f"  memory-backed: workspace sits on {ws['fstype']} ({ws['mount']}) "
                    "- residue costs RAM, not just disk"
                )
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
    elif args.command == "explain":
        info = explain(root, registry_path, state_dir, args.path)
        if args.json:
            print(json.dumps(info, ensure_ascii=False, indent=2))
        else:
            print(f"path: {info['path']}")
            if not info.get("covered"):
                print("unregistered: no policy entry covers this path -> nothing will ever happen to it")
                print("add an entry to your policy file if you want to govern it")
                return 0
            print(f"policy entry: {info['entry_path']}  ({info['grade']} / {info['cleanup']})")
            if info.get("retention_days") is not None:
                print(f"retention: {info['retention_days']} days")
            if info.get("intent"):
                print(f"intent: {info['intent']}")
            if info.get("owner"):
                print(f"owner: {info['owner']}")
            if info.get("review_after"):
                print(f"review after: {info['review_after']}")
            if info.get("protected"):
                print("protected: skipped while a --protected-window is active")
            if info.get("remote_authoritative"):
                print("remote authoritative: source of truth lives elsewhere")
            if info.get("candidate"):
                print(
                    f"status: candidate (idle {info['age_days']} days, "
                    f"{info.get('files', '?')} files, {info.get('size', 0) / 1024:.1f} KB)"
                )
                if info.get("grade") == "G3":
                    refs = info.get("references", [])
                    if info.get("blocked_by_references"):
                        print(f"blocked: referenced in {len(refs)} file(s): {', '.join(refs)}")
                    else:
                        print("status: G3 candidate needs --approve + --approver before recycling")
            else:
                print("status: not a candidate right now")
    elif args.command == "health":
        report, _ = audit(root, registry_path, state_dir)
        hs = health_score(report)
        if args.badge:
            color = {"A": "green", "B": "yellowgreen", "C": "yellow", "D": "red"}[hs["grade"]]
            print(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "label": "workspace health",
                        "message": f"{hs['score']} {hs['grade']}",
                        "color": color,
                    }
                )
            )
        elif args.json:
            print(json.dumps(hs, ensure_ascii=False, indent=2))
        else:
            print(f"health: {hs['score']}/100 ({hs['grade']})")
            comp = hs["components"]
            print(f"  auditability: {comp['auditability']}/25   governance: {comp['governance']}/25")
            print(f"  rot burden: {comp['rot']}/35   recycle readiness: {comp['recycle']}/15")
            flags = hs["flags"]
            print(f"  candidates: {flags['candidates']}   unregistered: {flags['unregistered']}"
                  f"   disk alert: {flags['disk_alert']}   journal chain: {'OK' if flags['journal_ok'] else 'BROKEN'}")
            if hs["score"] < 90:
                print("  next: run `wm audit` for the full report, then `wm clean --grades G4` (dry-run first)")
    elif args.command == "govern":
        result = govern(
            root,
            registry_path,
            state_dir,
            args.action,
            paths=args.path,
            preview=args.preview,
            approver=args.approve_by,
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            decision = "ALLOW" if result["allowed"] else "DENY"
            print(f"{decision}: {result['action']}")
            for reason in result["reasons"]:
                print(f"  reason: {reason}")
        return 0 if result["allowed"] else 2
    elif args.command == "mcp":
        from . import mcp_server

        return mcp_server.main(root, state_dir, registry_path)
    return 0
