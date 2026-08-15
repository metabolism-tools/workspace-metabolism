"""Core engine for workspace-metabolism.

Policy-driven file lifecycle management:

1. classify  - every path is registered in a policy registry (grades G1-G4)
2. audit     - read-only scan against the registry (candidates, unregistered, disk)
3. clean     - move expired items to a recycle area (never a direct delete)
4. rollback  - restore a cleanup run after an integrity check
5. purge     - delete recycle batches older than a threshold (the only real delete)
6. verify    - check the hash-chained journal and run manifests

Zero third-party dependencies (Python >= 3.11 standard library only).
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

GRADES = {"G1", "G2", "G3", "G4"}
ACTIONS = {"never", "auto", "approve"}
TEXT_EXTS = {
    ".py", ".md", ".sh", ".ps1", ".json", ".toml", ".yaml", ".yml",
    ".txt", ".html", ".js",
}
MAX_HASH_MB = 256
MAX_HASH_FILES = 5000
GENESIS = "GENESIS"


def utc_now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _default_state_dir_str(os_name: str, environ: dict) -> str:
    """Compute the default state directory as a plain string (testable on any OS)."""
    if os_name == "nt":
        base = environ.get("LOCALAPPDATA") or str(Path.home())
        return str(Path(base) / "workspace-metabolism")
    base = environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return str(Path(base) / "workspace-metabolism")


def default_state_dir() -> Path:
    """System cache directory, kept outside the governed workspace on purpose."""
    return Path(_default_state_dir_str(os.name, os.environ))


def parse_window(spec: str | None) -> Optional[tuple[int, int]]:
    """Parse 'HH:MM-HH:MM' into (start_minutes, end_minutes)."""
    if not spec:
        return None
    try:
        start_s, end_s = spec.split("-", 1)

        def to_minutes(s: str) -> int:
            h, m = s.strip().split(":", 1)
            return int(h) * 60 + int(m)

        start, end = to_minutes(start_s), to_minutes(end_s)
    except (ValueError, IndexError) as exc:
        raise SystemExit(f"invalid --protected-window '{spec}' (expected HH:MM-HH:MM)") from exc
    return (start, end)


def in_protected_window(now: datetime | None, window: tuple[int, int] | None) -> bool:
    if window is None:
        return False
    now = now or datetime.now()
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    start, end = window
    return start <= minutes <= end


# ---------------------------------------------------------------------------
# registry / policy
# ---------------------------------------------------------------------------


def load_registry(registry_path: Path) -> dict:
    if not registry_path.exists():
        raise SystemExit(f"registry not found: {registry_path} (see examples/registry.example.json)")
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or "entries" not in data:
        raise SystemExit(f"invalid registry format: {registry_path}")
    for entry in data["entries"]:
        path = entry.get("path")
        grade = entry.get("grade")
        cleanup = entry.get("cleanup")
        if not path or grade not in GRADES:
            raise SystemExit(f"invalid registry entry grade: {entry}")
        if cleanup not in ACTIONS:
            raise SystemExit(f"invalid registry entry cleanup: {entry}")
        if cleanup != "never" and not entry.get("retention_days"):
            raise SystemExit(f"entry requires retention_days: {path}")
    return data


def entry_covers(entry: dict, rel: Path) -> bool:
    """Whether a registry entry covers a relative path (supports * and **/ patterns)."""
    pattern = entry["path"]
    rel_s = rel.as_posix()
    if "**" in pattern:
        sub = pattern.split("**/", 1)[-1]
        return rel_s == sub or rel_s.endswith("/" + sub)
    if "*" in pattern:
        return fnmatch.fnmatch(rel_s, pattern)
    return rel_s == pattern or rel_s.startswith(pattern.rstrip("/") + "/")


def covered_by_any(registry: dict, rel: Path) -> bool:
    return any(entry_covers(e, rel) for e in registry["entries"])


def iter_entry_targets(root: Path, entry: dict) -> Iterator[tuple[Path, bool]]:
    """Expand a registry entry into concrete paths (directory or file)."""
    pattern = entry["path"]
    if "*" in pattern:
        for p in sorted(root.glob(pattern)):
            if p.exists():
                yield p, p.is_dir()
        return
    p = root / pattern
    if not p.exists():
        return
    if entry.get("scope") == "files_only":
        for f in sorted(p.iterdir()):
            if f.is_file():
                yield f, False
        return
    yield p, p.is_dir()


def collect_candidates(root: Path, registry: dict, now: datetime | None = None) -> list[dict]:
    """Items past their retention period with a cleanup action other than 'never'."""
    now = now or datetime.now()
    now_ts = now.timestamp()
    candidates: list[dict] = []
    for entry in registry["entries"]:
        if entry.get("cleanup") == "never":
            continue
        retention = entry.get("retention_days")
        if not retention:
            continue
        for target, is_dir in iter_entry_targets(root, entry):
            files, size, latest = dir_stats(target)
            if files == 0:
                continue
            age_days = (now_ts - latest) / 86400.0
            if age_days <= retention:
                continue
            candidates.append(
                {
                    "path": target.relative_to(root).as_posix(),
                    "is_dir": is_dir,
                    "grade": entry["grade"],
                    "cleanup": entry["cleanup"],
                    "retention_days": retention,
                    "age_days": round(age_days, 1),
                    "files": files,
                    "size": size,
                    "note": entry.get("note", ""),
                    "protected": bool(entry.get("protected", False)),
                    "remote_authoritative": bool(entry.get("remote_authoritative", False)),
                }
            )
    return candidates


# ---------------------------------------------------------------------------
# filesystem helpers
# ---------------------------------------------------------------------------


def dir_stats(path: Path) -> tuple[int, int, float]:
    """Return (file count, total bytes, newest mtime)."""
    total_files = 0
    total_size = 0
    latest = 0.0
    if path.is_file():
        st = path.stat()
        return 1, st.st_size, st.st_mtime
    for dirpath, dirnames, filenames in os.walk(path):
        try:
            latest = max(latest, os.stat(dirpath).st_mtime)
        except OSError:
            pass
        for name in filenames:
            fp = os.path.join(dirpath, name)
            try:
                st = os.stat(fp)
            except OSError:
                continue
            total_files += 1
            total_size += st.st_size
            latest = max(latest, st.st_mtime)
    return total_files, total_size, latest


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def item_hashes(target: Path, size: int, files: int) -> tuple[Optional[dict], str]:
    """Per-file hashes for small/medium targets; size-only for very large ones."""
    if size > MAX_HASH_MB * 1024 * 1024 or files > MAX_HASH_FILES:
        return None, "size_only"
    if target.is_file():
        return {"": sha256_file(target)}, "sha256"
    hashes: dict[str, str] = {}
    for dirpath, _, filenames in os.walk(target):
        for name in sorted(filenames):
            fp = Path(dirpath) / name
            hashes[fp.relative_to(target).as_posix()] = sha256_file(fp)
    return hashes, "sha256"


def verify_hashes(target: Path, hashes: Optional[dict], integrity: str) -> tuple[bool, str]:
    if integrity == "size_only":
        return True, "size_only (not per-file verified)"
    if target.is_file():
        expected = next(iter((hashes or {}).values())) if hashes else None
        if expected is None or sha256_file(target) != expected:
            return False, "hash mismatch"
        return True, "ok"
    for rel, expected in (hashes or {}).items():
        check = target / rel
        if not check.exists():
            return False, f"missing: {rel}"
        if sha256_file(check) != expected:
            return False, f"hash mismatch: {rel}"
    return True, "ok"


def workspace_stats(root: Path, skip_dirs: tuple[Path, ...] = ()) -> tuple[int, int]:
    total_files = 0
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dp = Path(dirpath)
        dirnames[:] = [d for d in dirnames if d != ".git"]
        if any(dp == sd or dp.is_relative_to(sd) for sd in skip_dirs):
            dirnames[:] = []
            continue
        for name in filenames:
            fp = os.path.join(dirpath, name)
            try:
                total_size += os.path.getsize(fp)
            except OSError:
                continue
            total_files += 1
    return total_files, total_size


def disk_status(root: Path) -> dict:
    usage = shutil.disk_usage(root)
    used_pct = round((1 - usage.free / usage.total) * 100, 1)
    return {
        "total_gb": round(usage.total / 1e9, 1),
        "free_gb": round(usage.free / 1e9, 1),
        "used_pct": used_pct,
    }


def find_references(root: Path, state_dir: Path | None, name: str) -> list[str]:
    """Locate code/docs references to a candidate name before G3 cleanup."""
    hits: list[str] = []
    state = Path(state_dir) if state_dir else None
    for dirpath, dirnames, filenames in os.walk(root):
        dp = Path(dirpath)
        dirnames[:] = [d for d in dirnames if d != ".git"]
        if state is not None and (dp == state or dp.is_relative_to(state)):
            dirnames[:] = []
            continue
        for fname in filenames:
            if Path(fname).suffix.lower() not in TEXT_EXTS:
                continue
            fp = dp / fname
            try:
                if fp.stat().st_size > 2 * 1024 * 1024:
                    continue
                content = fp.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if name in content:
                hits.append(fp.relative_to(root).as_posix())
    return hits


# ---------------------------------------------------------------------------
# audit journal (hash chain)
# ---------------------------------------------------------------------------


def journal_path(state_dir: Path) -> Path:
    return state_dir / "journal.jsonl"


def journal_last_hash(path: Path) -> str:
    if not path.exists():
        return GENESIS
    last: Optional[dict] = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            last = json.loads(line)
        except json.JSONDecodeError:
            continue
    return last.get("hash", GENESIS) if last else GENESIS


def journal_last_seq(path: Path) -> int:
    if not path.exists():
        return 0
    seq = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            seq = int(json.loads(line)["seq"])
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    return seq


def journal_append(
    state_dir: Path,
    action: str,
    operator: str,
    registry_sha256: Optional[str] = None,
    **fields,
) -> int:
    path = journal_path(state_dir)
    prev_hash = journal_last_hash(path)
    entry = {
        "seq": journal_last_seq(path) + 1,
        "ts": utc_now_iso(),
        "action": action,
        "operator": operator,
        "registry_sha256": registry_sha256,
        "prev_hash": prev_hash,
        **fields,
    }
    canonical = json.dumps({k: v for k, v in entry.items() if k != "hash"}, ensure_ascii=False, sort_keys=True)
    entry["hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry["seq"]


def verify_journal(state_dir: Path) -> dict:
    path = journal_path(state_dir)
    if not path.exists():
        raise SystemExit(f"journal not found: {path}")
    entries: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    prev_hash = GENESIS
    chain_ok = True
    broken_at: Optional[int] = None
    for entry in entries:
        canonical = json.dumps({k: v for k, v in entry.items() if k != "hash"}, ensure_ascii=False, sort_keys=True)
        calc = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if entry.get("prev_hash") != prev_hash or calc != entry.get("hash"):
            chain_ok = False
            broken_at = entry.get("seq")
            break
        prev_hash = entry["hash"]
    runs_dir = state_dir / "runs"
    missing_manifests = [
        e["run_id"]
        for e in entries
        if e.get("action") == "clean" and e.get("run_id") and not (runs_dir / f"{e['run_id']}.json").exists()
    ]
    return {
        "path": str(path),
        "entries": len(entries),
        "chain_ok": chain_ok,
        "broken_at": broken_at,
        "missing_manifests": missing_manifests,
        "last": entries[-5:],
    }


def verify(state_dir: Path) -> dict:
    """Public entry point: verify the journal hash chain and run manifests."""
    return verify_journal(state_dir)


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------


def last_audit_size(state_dir: Path) -> Optional[int]:
    path = journal_path(state_dir)
    if not path.exists():
        return None
    last_size: Optional[int] = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("action") == "audit" and "workspace_size" in entry:
            last_size = int(entry["workspace_size"])
    return last_size


def audit(
    root: Path,
    registry_path: Path,
    state_dir: Path,
    dupes: bool = False,
    operator: str = "manual",
) -> tuple[dict, Path]:
    registry = load_registry(registry_path)
    state_dir.mkdir(parents=True, exist_ok=True)
    candidates = collect_candidates(root, registry)
    skip = (state_dir,) if state_dir.is_relative_to(root) else ()
    total_files, total_size = workspace_stats(root, skip_dirs=skip)
    reg_sha = sha256_file(registry_path)
    disk = disk_status(root)
    defaults = registry.get("defaults", {})
    alert_free_gb = float(defaults.get("disk_alert_free_gb", 20))
    alert_free_pct = float(defaults.get("disk_alert_free_pct", 15))
    disk_alert = disk["free_gb"] < alert_free_gb or (100 - disk["used_pct"]) < alert_free_pct
    prev_size = last_audit_size(state_dir)
    growth_mb = round((total_size - prev_size) / 1024 / 1024, 1) if prev_size is not None else None

    unregistered: list[str] = []
    for child in sorted(root.iterdir()):
        rel = child.relative_to(root)
        name = rel.as_posix()
        if name in registry.get("never_clean", []):
            continue
        if name == ".git":
            continue
        if state_dir.is_relative_to(root) and rel == state_dir.relative_to(root):
            continue
        if covered_by_any(registry, rel):
            continue
        unregistered.append(name)

    dup_hits: list[tuple[str, list[str]]] = []
    if dupes:
        dupe_dirs = [root / d for d in defaults.get("dupe_scan_dirs", [])]
        by_key: dict[tuple[str, int], list[str]] = {}
        for area in dupe_dirs:
            if not area.exists():
                continue
            for dirpath, _, filenames in os.walk(area):
                for fname in filenames:
                    fp = Path(dirpath) / fname
                    try:
                        sz = fp.stat().st_size
                    except OSError:
                        continue
                    if sz == 0:
                        continue
                    by_key.setdefault((fname, sz), []).append(fp.relative_to(root).as_posix())
        for (fname, sz), paths in by_key.items():
            if len(paths) > 1:
                dup_hits.append((f"{fname} ({sz} B)", paths[:10]))
        dup_hits.sort(key=lambda x: -len(x[1]))
        dup_hits = dup_hits[:20]

    try:
        reg_rel = str(registry_path.relative_to(root))
    except ValueError:
        reg_rel = str(registry_path)

    report = {
        "run_id": f"audit-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "ts": now_str(),
        "workspace": {"files": total_files, "size": total_size},
        "disk": {**disk, "alert": disk_alert, "alert_free_gb": alert_free_gb, "alert_free_pct": alert_free_pct},
        "growth_mb_since_last_audit": growth_mb,
        "candidates": candidates,
        "unregistered": unregistered,
        "dup_hits": dup_hits,
        "registry_path": reg_rel,
    }

    journal_append(
        state_dir,
        "audit",
        operator,
        registry_sha256=reg_sha,
        run_id=report["run_id"],
        workspace_size=total_size,
        candidates=len(candidates),
        unregistered=len(unregistered),
        disk_free_gb=disk["free_gb"],
        disk_used_pct=disk["used_pct"],
        disk_alert=disk_alert,
        growth_mb=growth_mb,
    )

    journal_state = verify_journal(state_dir)
    recycle_files, recycle_size = recycle_stats(state_dir)
    g3_mb = sum(c["size"] for c in candidates if c["grade"] == "G3") / 1024 / 1024
    g4_mb = sum(c["size"] for c in candidates if c["grade"] == "G4") / 1024 / 1024
    report["summary"] = {
        "files": total_files,
        "size_mb": round(total_size / 1024 / 1024, 1),
        "growth_mb": growth_mb,
        "candidates": len(candidates),
        "candidates_g4_mb": round(g4_mb, 1),
        "candidates_g3_mb": round(g3_mb, 1),
        "unregistered": len(unregistered),
        "disk_alert": disk_alert,
        "recycle_files": recycle_files,
        "recycle_mb": round(recycle_size / 1024 / 1024, 1),
        "recycle_ratio_pct": round(recycle_size / total_size * 100, 1) if total_size else 0.0,
        "journal_entries": journal_state["entries"],
        "journal_chain_ok": journal_state["chain_ok"],
    }

    reports_dir = state_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    report_path.write_text(render_report(report, root), encoding="utf-8")

    runs_dir = state_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    json_path = runs_dir / f"{report['run_id']}.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report, report_path


def render_report(report: dict, root: Path) -> str:
    disk = report.get("disk", {})
    growth = report.get("growth_mb_since_last_audit")
    lines = [
        f"# Metabolism audit report {report['ts']}",
        "",
        f"- workspace: {report['workspace']['files']} files, {report['workspace']['size']/1024/1024:.1f} MB",
        f"- disk: {disk.get('free_gb')} GB free / {disk.get('total_gb')} GB total"
        f" ({disk.get('used_pct')}% used), alert threshold free<{disk.get('alert_free_gb')}GB or <{disk.get('alert_free_pct')}%"
        f" -> {'ALERT' if disk.get('alert') else 'normal'}",
    ]
    if growth is not None:
        lines.append(f"- vs last audit: {'growth' if growth >= 0 else 'shrink'} {abs(growth)} MB")
    lines.append(f"- registry: {report['registry_path']}")
    summary = report.get("summary")
    if summary:
        chain = "OK" if summary["journal_chain_ok"] else "BROKEN"
        lines.append(
            f"- recycle: {summary['recycle_files']} files, {summary['recycle_mb']} MB "
            f"({summary['recycle_ratio_pct']}% of workspace)"
        )
        lines.append(f"- journal: {summary['journal_entries']} entries, chain {chain}")
    lines.append("")
    lines.append("## Cleanable candidates (past retention)")
    lines.append("")
    if not report["candidates"]:
        lines.append("(none)")
    for c in report["candidates"]:
        extra = " (remote authoritative)" if c.get("remote_authoritative") else ""
        note = f"; {c['note']}" if c.get("note") else ""
        lines.append(
            f"- [{c['grade']}/{c['cleanup']}] {c['path']} "
            f"({c['files']} files, {c['size']/1024/1024:.1f} MB, idle {c['age_days']} days){extra}{note}"
        )
    lines.append("")
    lines.append("## Unregistered (outside the registry)")
    lines.append("")
    lines.append("、".join(report["unregistered"]) if report["unregistered"] else "(none)")
    lines.append("")
    if report["dup_hits"]:
        lines.append("## Possible duplicates (same name+size, not hash-verified)")
        lines.append("")
        for key, paths in report["dup_hits"]:
            lines.append(f"- {key}")
            for p in paths:
                lines.append(f"  - `{p}`")
        lines.append("")
    lines.append("## Suggested commands")
    lines.append("")
    g4 = [c for c in report["candidates"] if c["grade"] == "G4"]
    g3 = [c for c in report["candidates"] if c["grade"] == "G3"]
    if g4:
        lines.append(f"- auto-clean G4 ({sum(c['size'] for c in g4)/1024/1024:.0f} MB): `wm clean --grades G4 --yes`")
    if g3:
        lines.append(
            f"- approved G3 ({sum(c['size'] for c in g3)/1024/1024:.0f} MB): "
            "`wm clean --grades G3 --approve --approver <name> --yes`"
        )
    lines.append("- rollback: `wm rollback <run_id>`")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# clean / rollback / purge / status
# ---------------------------------------------------------------------------


def plan_items(
    root: Path,
    registry: dict,
    grades: set[str],
    state_dir: Path,
    now: datetime | None = None,
    window: tuple[int, int] | None = None,
) -> list[dict]:
    now = now or datetime.now()
    max_mb = registry.get("defaults", {}).get("max_item_mb", 2560)
    window_active = in_protected_window(now, window)
    never_clean = registry.get("never_clean", [])
    never_registry = {"entries": [{"path": p, "grade": "G1", "cleanup": "never"} for p in never_clean]}
    items: list[dict] = []
    for c in collect_candidates(root, registry, now):
        if c["grade"] not in grades:
            continue
        rel = Path(c["path"])
        reason = ""
        if c["path"] in never_clean or covered_by_any(never_registry, rel):
            reason = "protected"
        elif c["size"] > max_mb * 1024 * 1024:
            reason = f"exceeds single-item limit ({max_mb} MB)"
        elif c.get("protected") and window_active:
            reason = "inside protected window"
        elif c["grade"] == "G3":
            refs = find_references(root, state_dir, rel.name)
            if refs:
                reason = f"referenced in {len(refs)} file(s)"
                c["references"] = refs[:5]
        c["reason"] = reason
        items.append(c)
    return items


def clean(
    root: Path,
    registry_path: Path,
    state_dir: Path,
    grades: set[str],
    yes: bool = False,
    approve: bool = False,
    approver: Optional[str] = None,
    operator: str = "manual",
    window: tuple[int, int] | None = None,
) -> None:
    registry = load_registry(registry_path)
    if "G3" in grades and not approve:
        raise SystemExit("G3 cleanup requires approval (--approve)")
    items = plan_items(root, registry, grades, state_dir, window=window)
    allowed_cleanup = set()
    if "G4" in grades:
        allowed_cleanup.add("auto")
    if "G3" in grades and approve:
        allowed_cleanup.add("approve")
    todo = [it for it in items if it["cleanup"] in allowed_cleanup and not it["reason"]]
    blocked = [it for it in items if it["reason"]]
    if any(it["grade"] == "G3" for it in todo) and not approver:
        raise SystemExit("G3 cleanup requires --approver (audit trail)")
    size_todo = sum(it["size"] for it in todo)
    print(
        f"clean plan ({'dry-run' if not yes else 'executing'}): {len(todo)} item(s), "
        f"{size_todo/1024/1024:.1f} MB; blocked {len(blocked)}"
    )
    for it in todo:
        print(f"  [{it['grade']}] {it['path']} ({it['files']} files, {it['size']/1024/1024:.1f} MB)")
    for it in blocked:
        print(f"  [blocked] {it['path']} -> {it['reason']}")
    if not yes:
        print("--yes not given; dry-run only, nothing was moved.")
        return
    if not todo:
        print("nothing to do.")
        return

    run_id = f"clean-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    recycle = state_dir / "recycle" / run_id
    runs_dir = state_dir / "runs"
    manifest = {"run_id": run_id, "ts": now_str(), "items": []}
    moved_ok = 0
    for it in todo:
        src = root / it["path"]
        dst = recycle / it["path"]
        try:
            if dst.exists():
                print(f"  [skip] {it['path']}: target already exists in recycle")
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            hashes, integrity = item_hashes(src, it["size"], it["files"])
            shutil.move(str(src), str(dst))
            files, size, _ = dir_stats(dst)
            manifest["items"].append(
                {
                    "path": it["path"],
                    "is_dir": it["is_dir"],
                    "grade": it["grade"],
                    "cleanup": it["cleanup"],
                    "size": size,
                    "files": files,
                    "hashes": hashes,
                    "integrity": integrity,
                    "moved_at": now_str(),
                }
            )
            moved_ok += 1
            print(f"  [recycled] {it['path']} -> {dst}")
        except Exception as exc:  # noqa: BLE001
            print(f"  [error] {it['path']}: {exc}")
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / f"{run_id}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    journal_append(
        state_dir,
        "clean",
        operator,
        registry_sha256=sha256_file(registry_path),
        run_id=run_id,
        grades=sorted(grades),
        items=moved_ok,
        size=sum(it["size"] for it in todo),
        approver=approver,
    )
    print(f"done: {moved_ok}/{len(todo)} item(s) moved to recycle. rollback: wm rollback {run_id}")


def rollback(root: Path, state_dir: Path, run_id: str, dry: bool = False, operator: str = "manual") -> None:
    manifest_path = state_dir / "runs" / f"{run_id}.json"
    if not manifest_path.exists():
        raise SystemExit(f"run manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    recycle = state_dir / "recycle" / run_id
    ok = 0
    for it in reversed(manifest["items"]):
        src = recycle / it["path"]
        dst = root / it["path"]
        if not src.exists():
            print(f"  [missing] {it['path']} not in recycle")
            continue
        verified, msg = verify_hashes(src, it.get("hashes"), it.get("integrity", "size_only"))
        if not verified:
            print(f"  [refused] {it['path']} integrity check failed ({msg}); skipped")
            continue
        if dst.exists():
            print(f"  [refused] {it['path']} already exists at original location; skipped")
            continue
        if dry:
            print(f"  [dry-run] restore {it['path']}")
            ok += 1
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        ok += 1
        print(f"  [restored] {it['path']}")
    if not dry:
        journal_append(state_dir, "rollback", operator, run_id=run_id, restored=ok)
    print(f"rollback {'dry-run' if dry else 'completed'}: {ok}/{len(manifest['items'])}")


def purge(state_dir: Path, older_than_days: int = 30, yes: bool = False, operator: str = "manual") -> None:
    recycle = state_dir / "recycle"
    if not recycle.exists():
        print("recycle area is empty.")
        return
    cutoff = datetime.now().timestamp() - older_than_days * 86400
    candidates: list[tuple[Path, float]] = []
    for run_dir in sorted(recycle.iterdir()):
        if not run_dir.is_dir():
            continue
        try:
            mtime = run_dir.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            candidates.append((run_dir, mtime))
    if not candidates:
        print(f"no recycle batches older than {older_than_days} days.")
        return
    total = 0
    for run_dir, _ in candidates:
        files, size, _ = dir_stats(run_dir)
        total += size
        print(f"  {run_dir.name}: {files} files, {size/1024/1024:.1f} MB")
    if not yes:
        print("--yes not given; preview only.")
        return
    for run_dir, _ in candidates:
        resolved = run_dir.resolve()
        if not str(resolved).startswith(str(recycle.resolve())):
            print(f"  [refused] {run_dir} outside recycle area")
            continue
        shutil.rmtree(resolved)
        print(f"  [deleted] {run_dir.name}")
    journal_append(
        state_dir,
        "purge",
        operator,
        batches=[r.name for r, _ in candidates],
        size=total,
    )
    print(f"purge done; freed {total/1024/1024:.1f} MB")


def status(root: Path, registry_path: Path, state_dir: Path) -> None:
    registry = load_registry(registry_path)
    skip = (state_dir,) if state_dir.is_relative_to(root) else ()
    files, size = workspace_stats(root, skip_dirs=skip)
    print(f"workspace: {files} files, {size/1024/1024:.1f} MB")
    recycle_files, recycle_size = recycle_stats(state_dir)
    print(
        f"recycle: {recycle_files} files, {recycle_size/1024/1024:.1f} MB "
        f"(retention {registry.get('defaults', {}).get('recycle_retention_days', 30)} days before purge)"
    )
    runs_dir = state_dir / "runs"
    if runs_dir.exists():
        runs = sorted(runs_dir.glob("*.json"))
        print(f"runs: {len(runs)}")
        for r in runs[-5:]:
            print(f"  {r.stem}")
    candidates = collect_candidates(root, registry)
    g4 = sum(c["size"] for c in candidates if c["grade"] == "G4")
    g3 = sum(c["size"] for c in candidates if c["grade"] == "G3")
    print(f"pending candidates: G4 {g4/1024/1024:.1f} MB, G3 {g3/1024/1024:.1f} MB")


def recycle_stats(state_dir: Path) -> tuple[int, int]:
    """Return (file count, total bytes) currently held in the recycle area."""
    recycle = state_dir / "recycle"
    files = size = 0
    if recycle.exists():
        for batch in recycle.iterdir():
            if batch.is_dir():
                f, s, _ = dir_stats(batch)
                files += f
                size += s
    return files, size
