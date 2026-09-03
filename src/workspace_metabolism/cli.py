"""Command-line interface for workspace-metabolism."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .core import (
    append_policy_entries,
    audit,
    clean,
    default_state_dir,
    doctor,
    explain,
    govern,
    health_score,
    init_policy,
    load_registry,
    parse_window,
    POLICY_FILENAMES,
    purge,
    rollback,
    scan_residue,
    slim,
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
        try:
            if candidate.exists():
                return candidate.resolve()
        except OSError:
            # unreadable path (e.g. another user's home): treat as absent
            continue
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wm",
        description=(
            "Policy-driven file lifecycle management: classify, audit, "
            "clean (recyclable), rollback, purge with a hash-chained audit trail. "
            "NOTE: global options (--root, --state-dir, --registry, "
            "--protected-window) must come BEFORE the subcommand, e.g. "
            "`wm --registry policy.json slim --db ledger.db --yes`."
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
    p_clean.add_argument("--decision-id", help="link this run to a wm govern decision_id")
    p_clean.add_argument("--auto", action="store_true", help="mark the run as scheduled")

    p_roll = sub.add_parser("rollback", help="restore one cleanup run from the recycle area")
    p_roll.add_argument("run_id")
    p_roll.add_argument("--dry-run", action="store_true")
    p_roll.add_argument("--decision-id", help="link this run to a wm govern decision_id")

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
    p_doctor.add_argument(
        "--residue",
        action="store_true",
        help="also scan for common agent byproducts (caches, traces) the policy does not govern yet",
    )
    p_doctor.add_argument(
        "--apply-policy",
        action="store_true",
        help="with --residue: append the suggested policy entries (creates the policy file if missing)",
    )

    p_govern = sub.add_parser("govern", help="check whether an AI action is allowed by policy")
    p_govern.add_argument("action", help="read, write, execute, delete or network")
    p_govern.add_argument("--path", action="append", default=[], help="path involved in the action; repeatable")
    p_govern.add_argument("--preview", action="store_true", help="confirm that a dry-run or preview was completed")
    p_govern.add_argument("--approve-by", help="human approver identity")
    p_govern.add_argument("--json", action="store_true", help="print the decision as JSON")

    p_slim = sub.add_parser(
        "slim",
        help="trim heavy JSON fields out of a registered SQLite database in place "
             "(journaled; dry-run by default)",
    )
    p_slim.add_argument("--db", required=True, help="path to the SQLite database")
    p_slim.add_argument("--table", help="table holding the JSON blob (override entry.db_slim.table)")
    p_slim.add_argument("--blob-column", help="JSON blob column (override entry.db_slim.blob_column)")
    p_slim.add_argument("--strip-keys", help="comma-separated JSON keys to strip (override entry.db_slim.strip_keys)")
    p_slim.add_argument("--keep-recent", type=int, help="keep the newest N distinct reference values untouched")
    p_slim.add_argument("--keep-table", help="reference table for --keep-recent")
    p_slim.add_argument("--keep-column", help="reference column for --keep-recent")
    p_slim.add_argument("--vacuum-min-gb", type=float, help="VACUUM only when reclaim >= this many GB")
    p_slim.add_argument("--yes", action="store_true", help="execute instead of dry-run")
    p_slim.add_argument("--decision-id", help="link this run to a wm govern decision_id")

    p_gate = sub.add_parser(
        "gate",
        help="run an MCP governance proxy: every tool call is checked against the policy first",
    )
    p_gate.add_argument(
        "--target",
        required=True,
        help="command that starts the MCP server to wrap, e.g. 'python -m my_server'",
    )

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
        residue = None
        if args.residue:
            registry_dict = None
            if registry_path is not None:
                try:
                    registry_dict = load_registry(registry_path)
                except SystemExit:
                    registry_dict = None
            residue = scan_residue(root, registry_dict)
            if args.apply_policy:
                if registry_path is None:
                    init_policy(root, root / POLICY_FILENAMES[0])
                    registry_path = root / POLICY_FILENAMES[0]
                    result["registry_present"] = True
                    result["registry_valid"] = True
                    result["missing_registry"] = False
                residue["policy_added"] = append_policy_entries(
                    registry_path, residue.get("suggestions", [])
                )
        if args.json:
            out = dict(result)
            if residue is not None:
                out["residue"] = residue
            print(json.dumps(out, ensure_ascii=False, indent=2))
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
            if residue is not None:
                hits = residue.get("hits", [])
                total_bytes = sum(h.get("size_bytes", 0) for h in hits)
                print(
                    f"\nRESIDUE: {len(hits)} byproduct(s) not governed by the policy "
                    f"({total_bytes / 1024 / 1024:.1f} MB)"
                )
                for h in hits[:20]:
                    extra = "" if not h.get("size_partial") else " (size partial)"
                    print(
                        f"  - {h['path']} ({h['files']} file(s), "
                        f"{h['size_bytes'] / 1024 / 1024:.1f} MB){extra} "
                        f"-> suggest {h['suggested_entry']['path']} "
                        f"{h['suggested_entry']['grade']}"
                    )
                if len(hits) > 20:
                    print(f"  ... and {len(hits) - 20} more")
                for w in residue.get("warnings", []):
                    print(f"WARNING: {w}")
                if args.apply_policy:
                    added = residue.get("policy_added", [])
                    if added:
                        print(f"ADDED to policy: {', '.join(added)}")
                        print("NEXT: commit the policy change; run `wm audit` to see grades")
                    else:
                        print("POLICY: nothing to add (suggestions already present or nothing found)")
                else:
                    print(
                        "NEXT: review above, then run `wm doctor --residue --apply-policy` "
                        "to adopt the suggestions as policy entries"
                    )
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
            decision_id=args.decision_id,
        )
    elif args.command == "rollback":
        rollback(root, state_dir, args.run_id, dry=args.dry_run, operator=operator, decision_id=args.decision_id)
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
    elif args.command == "gate":
        from .gate import gate_main, target_from_args

        return gate_main(root, state_dir, registry_path, target_from_args(args.target))
    elif args.command == "slim":
        strip = tuple(k.strip() for k in args.strip_keys.split(",") if k.strip()) if args.strip_keys else ()
        report = slim(
            Path(args.db),
            registry_path,
            state_dir,
            table=args.table,
            blob_column=args.blob_column,
            strip_keys=strip,
            keep_recent=args.keep_recent,
            keep_table=args.keep_table,
            keep_column=args.keep_column,
            vacuum_min_gb=args.vacuum_min_gb,
            yes=args.yes,
            operator=operator,
            decision_id=args.decision_id,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if report["status"] == "ok":
            print(
                f"slim done: {report['rows_stripped']} row(s) stripped, "
                f"{report['size_before_bytes']} -> {report['size_after_bytes']} bytes "
                f"(reclaimed {report['reclaimed_gb']} GB)"
                + (", VACUUM applied" if report["vacuum_done"] else "")
                + "; journaled (action=slim)"
            )
        else:
            print(
                f"dry-run: {report['rows_stripped']} row(s) would be stripped, "
                f"{report['reclaimed_gb']} GB reclaimable; re-run with --yes to execute"
            )
    return 0
