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

import contextlib
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterator, Optional

GRADES = {"G1", "G2", "G3", "G4"}
ACTIONS = {"never", "auto", "approve"}
AI_ACTIONS = {"read", "write", "execute", "delete", "network"}
TEXT_EXTS = {
    ".py", ".md", ".sh", ".ps1", ".json", ".toml", ".yaml", ".yml",
    ".txt", ".html", ".js",
}
SCHEMA_URL = "https://raw.githubusercontent.com/metabolism-tools/workspace-metabolism/main/schema/metabolism.schema.json"
POLICY_FILENAMES = ("metabolism.json", ".wm.json")
MAX_HASH_MB = 256
MAX_HASH_FILES = 5000
GENESIS = "GENESIS"
# Files that look like secrets/keys/credentials. Used two ways: (a) audit
# reports them in a dedicated "Sensitive files" section, (b) load_registry
# refuses to register a matching entry path as G4 auto-clean. Advisory
# matching by basename; false positives only ever produce a warning or a
# validation error with a clear message, never a deletion.
SENSITIVE_PATTERNS = (
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "*.keystore",
    "*credential*", "*secret*", "*token*", "*password*", "*.htpasswd",
    "id_rsa", "id_ed25519", ".netrc", ".npmrc",
)


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
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid registry JSON: {registry_path} ({exc})") from exc
    if data.get("version") != 1 or "entries" not in data:
        raise SystemExit(f"invalid registry format: {registry_path}")
    for entry in data["entries"]:
        path = entry.get("path")
        grade = entry.get("grade")
        cleanup = entry.get("cleanup")
        if not path or grade not in GRADES:
            raise SystemExit(f"invalid registry entry grade: {entry}")
        _validate_policy_path(path)
        if cleanup not in ACTIONS:
            raise SystemExit(f"invalid registry entry cleanup: {entry}")
        if cleanup != "never" and not entry.get("retention_days"):
            raise SystemExit(f"entry requires retention_days: {path}")
        if grade == "G4" and cleanup == "auto" and is_sensitive_path(path):
            raise SystemExit(
                f"refusing G4 auto-clean for sensitive path: {path} "
                "(secrets/keys/credentials must never be auto-cleaned; use G1/G2/G3)"
            )
    ai_governance = data.get("ai_governance")
    if ai_governance is not None:
        if not isinstance(ai_governance, dict):
            raise SystemExit("invalid ai_governance: expected an object")
        default = ai_governance.get("default", "deny")
        if default not in {"allow", "deny"}:
            raise SystemExit("invalid ai_governance.default: expected allow or deny")
        for protected_path in ai_governance.get("protected_paths", []):
            _validate_policy_path(str(protected_path))
        actions = ai_governance.get("actions", {})
        if not isinstance(actions, dict):
            raise SystemExit("invalid ai_governance.actions: expected an object")
        for action, rule in actions.items():
            if action not in AI_ACTIONS or not isinstance(rule, dict):
                raise SystemExit(f"invalid ai_governance action: {action}")
            for field in ("allow", "requires_preview", "requires_approval"):
                if field in rule and not isinstance(rule[field], bool):
                    raise SystemExit(f"invalid ai_governance.{action}.{field}: expected boolean")
    return data


def init_policy(root: Path, path: Path, force: bool = False) -> Path:
    """Scaffold a metabolism.json policy file for a workspace (like `git init`)."""
    if path.exists() and not force:
        raise SystemExit(f"policy already exists: {path} (use --force to overwrite)")
    path.parent.mkdir(parents=True, exist_ok=True)
    never_clean = [
        ".git", "README.md", "LICENSE", "metabolism.json", ".wm.json",
        "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
        "package.json", "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
        "Makefile", "MANIFEST.in", ".gitignore", "Dockerfile",
        "docker-compose.yml", "compose.yaml", "justfile", ".github", ".venv",
        "CONTRIBUTING.md", "ROADMAP.md", "CHANGELOG.md", "SECURITY.md",
        "AGENTS.md", "NOTICE",
        # sensitive by default: secrets/keys/credentials are never auto-cleaned
        ".env", ".env.*", "*.pem", "*.key", "id_rsa", "id_ed25519",
        ".netrc", ".npmrc",
    ]
    keep_dirs = {
        "src", "docs", "tests", "test", "app", "lib", "include", "config",
        "examples", "scripts", "tools", "knowledge", "schema",
    }
    g4_dirs = {
        "logs": 30, "tmp": 7, "cache": 30, ".pytest_cache": 30,
        ".mypy_cache": 30, ".ruff_cache": 30, ".tox": 30, "dist": 90,
        "build": 90,
    }
    g3_dirs = {"archive": 60, "deprecated": 60, "staging": 60, "old": 90}
    entries: list[dict] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name == ".git" or child.name in never_clean:
            continue
        name = child.name
        if name in g4_dirs:
            entries.append(
                {
                    "path": name, "grade": "G4", "cleanup": "auto",
                    "retention_days": g4_dirs[name],
                    "intent": "high-churn byproduct",
                }
            )
        elif name in g3_dirs:
            entries.append(
                {
                    "path": name, "grade": "G3", "cleanup": "approve",
                    "retention_days": g3_dirs[name],
                    "intent": "older material; human approval before recycle",
                }
            )
        elif name in keep_dirs:
            entries.append(
                {
                    "path": name, "grade": "G2", "cleanup": "never",
                    "intent": "source or docs; always keep",
                }
            )
    entries.append(
        {
            "path": "**/__pycache__", "grade": "G4", "cleanup": "auto",
            "retention_days": 30, "intent": "python bytecode cache",
        }
    )
    policy = {
        "version": 1,
        "$schema": SCHEMA_URL,
        "description": f"workspace-metabolism policy for {root.name}",
        "ai_governance": {
            "default": "deny",
            "actions": {
                "read": {"allow": True},
                "write": {"allow": True, "requires_preview": True},
                "execute": {"allow": True, "requires_approval": True},
                "delete": {"allow": False, "requires_approval": True},
                "network": {"allow": False, "requires_approval": True},
            },
        },
        "defaults": {
            "recycle_retention_days": 30,
            "max_item_mb": 2560,
            "disk_alert_free_gb": 20,
            "disk_alert_free_pct": 15,
            "dupe_scan_dirs": ["tmp", "cache"],
        },
        "never_clean": never_clean,
        "entries": entries,
    }
    path.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def govern(
    root: Path,
    registry_path: Path,
    state_dir: Path,
    action: str,
    paths: list[str] | None = None,
    preview: bool = False,
    approver: str | None = None,
    operator: str = "agent",
) -> dict:
    """Evaluate an AI action against the policy and record the decision.

    This is intentionally a decision point, not an execution engine. Callers
    must still perform the actual work through their own controlled tool.
    """
    registry = load_registry(registry_path)
    action = str(action).strip().lower()
    requested_paths = []
    for raw_path in (paths or []):
        path = str(raw_path).replace("\\", "/").strip()
        if path:
            _validate_policy_path(path)
            requested_paths.append(path)
    governance = registry.get("ai_governance") or {}
    default = str(governance.get("default", "deny")).lower()
    rule = (governance.get("actions") or {}).get(action)
    reasons: list[str] = []
    if action not in AI_ACTIONS or not isinstance(rule, dict):
        allowed = default == "allow"
        reasons.append("unknown action is denied by default" if not allowed else "allowed by policy default")
    else:
        allowed = bool(rule.get("allow", default == "allow"))
        if not allowed:
            reasons.append("action is disabled by policy")
        if rule.get("requires_preview") and not preview:
            allowed = False
            reasons.append("a preview is required")
        if rule.get("requires_approval") and not approver:
            allowed = False
            reasons.append("human approval is required")

    protected = [str(p).replace("\\", "/").rstrip("/") for p in governance.get("protected_paths", [])]
    matched_protected = [
        path for path in requested_paths
        if any(path == pattern or path.startswith(pattern.rstrip("/") + "/") for pattern in protected)
    ]
    if matched_protected:
        allowed = False
        reasons.append(f"protected path requested: {', '.join(matched_protected)}")
    if allowed and not reasons:
        reasons.append("allowed by policy")

    result = {
        "allowed": allowed,
        "action": action,
        "paths": requested_paths,
        "preview": preview,
        "approver": approver,
        "reasons": reasons,
        "policy": str(registry_path),
        "policy_sha256": sha256_file(registry_path),
    }
    with state_operation_lock(state_dir, "govern"):
        journal_append(
            state_dir,
            "govern",
            operator,
            registry_sha256=result["policy_sha256"],
            decision="allow" if allowed else "deny",
            governed_action=action,
            paths=requested_paths,
            preview=preview,
            approver=approver,
            reasons=reasons,
        )
    return result


def _validate_policy_path(path: str) -> None:
    """Reject policy paths that can escape the workspace or refer to the root."""
    raw = str(path).replace("\\", "/").strip()
    if not raw or raw == ".":
        raise SystemExit(f"invalid registry entry path: {path!r}")
    if PurePosixPath(raw).is_absolute() or PureWindowsPath(raw).is_absolute() or PureWindowsPath(raw).drive:
        raise SystemExit(f"invalid registry entry path must be relative: {path!r}")
    if any(part == ".." for part in PurePosixPath(raw).parts):
        raise SystemExit(f"invalid registry entry path must not contain '..': {path!r}")


def ensure_within_root(root: Path, target: Path, label: str = "path") -> Path:
    """Resolve a target and refuse it if it escapes the given root."""
    root_resolved = root.resolve()
    target_resolved = target.resolve()
    try:
        target_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise SystemExit(f"refusing {label} outside workspace: {target}") from exc
    return target_resolved


@contextlib.contextmanager
def state_operation_lock(state_dir: Path, operation: str):
    """Best-effort exclusive lock for state-changing operations."""
    state_dir.mkdir(parents=True, exist_ok=True)
    lock_path = state_dir / ".wm.lock"
    payload = {
        "operation": operation,
        "pid": os.getpid(),
        "ts": utc_now_iso(),
    }
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        details = ""
        try:
            details = lock_path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            pass
        msg = f"state directory is busy: {lock_path} already exists"
        if details:
            msg += f" ({details})"
        raise SystemExit(msg) from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            fh.write("\n")
        yield lock_path
    finally:
        try:
            lock_path.unlink()
        except OSError:
            pass


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


def entry_specificity(entry: dict) -> int:
    """Number of path segments in a plain entry; glob entries sort as their literal depth."""
    pattern = str(entry.get("path", "")).strip("/").replace("\\", "/")
    return len(PurePosixPath(pattern).parts)


def most_specific_entry(registry: dict, rel: Path) -> Optional[dict]:
    """The covering entry with the longest path; generic entries never shadow specific ones.

    Mirrors ``db_slim_policy``'s longest-match-wins rule so every policy lookup
    (explain, planning) agrees on which entry governs a path.
    """
    best: Optional[dict] = None
    best_len = -1
    for e in registry.get("entries", []):
        if not entry_covers(e, rel):
            continue
        n = entry_specificity(e)
        if n > best_len:
            best, best_len = e, n
    return best


def covered_by_any(registry: dict, rel: Path) -> bool:
    return any(entry_covers(e, rel) for e in registry["entries"])


def is_sensitive_path(rel: Path | str) -> bool:
    """Whether a relative path looks like a sensitive file (secrets, keys, credentials).

    Matches on the basename and on the full relative path against
    SENSITIVE_PATTERNS; used for advisory reporting and for refusing G4
    auto-clean registration, never for deletion by itself.
    """
    rel_s = rel.as_posix() if isinstance(rel, Path) else rel
    base = rel_s.rsplit("/", 1)[-1]
    return any(
        fnmatch.fnmatch(base, pattern) or fnmatch.fnmatch(rel_s, pattern)
        for pattern in SENSITIVE_PATTERNS
    )


def sensitive_under(root: Path, rel: Path) -> bool:
    """Whether a candidate target (file or tree) contains any sensitive file."""
    target = root / rel
    if target.is_file():
        return is_sensitive_path(rel)
    if not target.is_dir():
        return False
    for dirpath, dirnames, filenames in os.walk(target):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for fname in filenames:
            if is_sensitive_path(Path(dirpath).relative_to(root) / fname):
                return True
    return False


def scan_sensitive_files(root: Path, state_dir: Path | None = None) -> list[dict]:
    """Find workspace files whose names match sensitive patterns (secrets/keys)."""
    hits: list[dict] = []
    state = Path(state_dir) if state_dir else None
    for dirpath, dirnames, filenames in os.walk(root):
        dp = Path(dirpath)
        dirnames[:] = [d for d in dirnames if d != ".git"]
        if state is not None and (dp == state or dp.is_relative_to(state)):
            dirnames[:] = []
            continue
        for fname in filenames:
            rel = dp.relative_to(root) / fname
            if not is_sensitive_path(rel):
                continue
            try:
                size = (dp / fname).stat().st_size
            except OSError:
                size = 0
            hits.append({"path": rel.as_posix(), "size": size})
    return sorted(hits, key=lambda hit: hit["path"])


def git_tracked_files(root: Path) -> Optional[set[str]]:
    """Set of git-tracked relative posix paths, or None when not a git repo.

    Uses `git ls-files -z` via subprocess; returns None (and callers fall
    back to pure policy matching) when there is no .git directory, git is
    not installed, or the command fails. Git is optional, never required.
    """
    if not (root / ".git").exists():
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    raw = proc.stdout.decode("utf-8", errors="replace")
    return {p for p in raw.split("\0") if p}


def tracked_under(tracked: set[str], rel_s: str) -> bool:
    """Whether any tracked path equals a candidate path or lives under it."""
    return any(p == rel_s or p.startswith(rel_s + "/") for p in tracked)


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
                    "owner": entry.get("owner", ""),
                    "intent": entry.get("intent", ""),
                    "review_after": entry.get("review_after", ""),
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


# Memory-backed filesystems: residue stored there costs RAM, not just disk
# (e.g. /tmp on modern Linux is tmpfs; the Claude Code /tmp/claude-*-cwd leak
# is a memory leak on such systems, not merely disk clutter).
MEMORY_FS_TYPES = ("tmpfs", "ramfs")


def parse_mounts(text: str) -> dict[str, str]:
    """Parse a /proc/mounts-style table into {mountpoint: fstype}.

    Only memory-backed filesystem types (tmpfs, ramfs) are kept. Pure
    function over text so it can be unit-tested on any OS.
    """
    mounts: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        mountpoint, fstype = parts[1], parts[2]
        if fstype in MEMORY_FS_TYPES:
            mounts[mountpoint] = fstype
    return mounts


def memory_backed_mounts() -> dict[str, str]:
    """Memory-backed mounts on this machine; {} where none are visible.

    Linux reads /proc/self/mounts; macOS and Windows have no tmpfs/ramfs
    by default and return {} (the feature degrades to a no-op there).
    """
    if os.name == "nt":
        return {}
    proc = Path("/proc/self/mounts")
    if not proc.exists():
        return {}
    try:
        return parse_mounts(proc.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return {}


def _match_memory_mount(target: str, mounts: dict[str, str]) -> Optional[dict]:
    """Longest-prefix match of a POSIX path against memory-backed mounts."""
    best: Optional[tuple[int, str, str]] = None
    for mountpoint, fstype in mounts.items():
        mp = mountpoint.rstrip("/") or "/"
        if mp == "/":
            # the root mount covers every absolute path; the naive
            # target.startswith(mp + "/") would demand "//" and never match
            matched = target.startswith("/")
        else:
            matched = target == mp or target.startswith(mp + "/")
        if matched and (best is None or len(mp) > best[0]):
            best = (len(mp), mp, fstype)
    if best is None:
        return None
    return {"mount": best[1], "fstype": best[2]}


def memory_backed_info(path: Path | str, mounts: dict[str, str] | None = None) -> Optional[dict]:
    """If a path lives on a memory-backed filesystem, describe it.

    Returns {"mount": mountpoint, "fstype": fstype} for the longest matching
    mount prefix, else None. Mount points are compared as POSIX paths; the
    caller normally passes the dict from memory_backed_mounts().
    """
    mounts = mounts if mounts is not None else memory_backed_mounts()
    if not mounts:
        return None
    target = Path(path).resolve().as_posix()
    return _match_memory_mount(target, mounts)


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


def health_score(report: dict) -> dict:
    """0-100 workspace health score from an audit report.

    Four weighted components: auditability (25), governance (25), rot burden
    (35) and recycle readiness (15). See docs/narrative.md for the rationale.
    """
    summary = report.get("summary", {})
    total_files = max(int(summary.get("files", 0)), 1)
    auditability = 25 if summary.get("journal_chain_ok") else 0
    governance = max(
        0,
        25 - 5 * int(summary.get("unregistered", 0)) - (10 if summary.get("disk_alert") else 0),
    )
    candidate_ratio = min(1.0, int(summary.get("candidates", 0)) / total_files)
    rot = round(35 * (1 - candidate_ratio))
    recycle = 15 if int(summary.get("recycle_files", 0)) > 0 else 10
    score = auditability + governance + rot + recycle
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D"
    return {
        "score": score,
        "grade": grade,
        "components": {
            "auditability": auditability,
            "governance": governance,
            "rot": rot,
            "recycle": recycle,
        },
        "flags": {
            "journal_ok": bool(summary.get("journal_chain_ok")),
            "unregistered": int(summary.get("unregistered", 0)),
            "disk_alert": bool(summary.get("disk_alert")),
            "candidates": int(summary.get("candidates", 0)),
            "recycle_files": int(summary.get("recycle_files", 0)),
        },
    }


def _audit_unlocked(
    root: Path,
    registry_path: Path,
    state_dir: Path,
    dupes: bool = False,
    operator: str = "manual",
) -> tuple[dict, Path]:
    registry = load_registry(registry_path)
    state_dir.mkdir(parents=True, exist_ok=True)
    root = root.resolve()
    state_dir = state_dir.resolve()
    registry_path = registry_path.resolve()
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

    # git-aware classification: in a git repo, tracked files are controlled
    # by git (effectively G2), so they are not "unregistered" drift
    tracked = git_tracked_files(root)
    if tracked is not None:
        unregistered = [
            name
            for name in unregistered
            if not any(p == name or p.startswith(name + "/") for p in tracked)
        ]

    sensitive = scan_sensitive_files(root, state_dir)

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

    # memory-backed awareness: residue on tmpfs/ramfs costs RAM, not just disk
    mem_mounts = memory_backed_mounts()
    mem_workspace = memory_backed_info(root, mem_mounts)
    mem_candidates = []
    for c in candidates:
        info = memory_backed_info(root / c["path"], mem_mounts)
        if info:
            mem_candidates.append(
                {**info, "path": c["path"], "files": c["files"], "size": c["size"]}
            )
    memory = {
        "mounts": mem_mounts,
        "workspace": mem_workspace,
        "candidates": mem_candidates,
        "candidates_on_memory": len(mem_candidates),
        "candidates_on_memory_mb": round(
            sum(c["size"] for c in mem_candidates) / 1024 / 1024, 1
        ),
    }

    report = {
        "run_id": f"audit-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}",
        "ts": now_str(),
        "workspace": {"files": total_files, "size": total_size},
        "disk": {**disk, "alert": disk_alert, "alert_free_gb": alert_free_gb, "alert_free_pct": alert_free_pct},
        "growth_mb_since_last_audit": growth_mb,
        "candidates": candidates,
        "unregistered": unregistered,
        "sensitive": sensitive,
        "git": {"repo": tracked is not None, "tracked_files": len(tracked) if tracked else 0},
        "dup_hits": dup_hits,
        "memory": memory,
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
        sensitive=len(sensitive),
        disk_free_gb=disk["free_gb"],
        disk_used_pct=disk["used_pct"],
        disk_alert=disk_alert,
        growth_mb=growth_mb,
        memory_candidates=len(mem_candidates),
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
        "sensitive": len(sensitive),
        "disk_alert": disk_alert,
        "memory_candidates": len(mem_candidates),
        "workspace_on_memory": bool(mem_workspace),
        "recycle_files": recycle_files,
        "recycle_mb": round(recycle_size / 1024 / 1024, 1),
        "recycle_ratio_pct": round(recycle_size / total_size * 100, 1) if total_size else 0.0,
        "journal_entries": journal_state["entries"],
        "journal_chain_ok": journal_state["chain_ok"],
    }
    hs = health_score(report)
    report["summary"]["health_score"] = hs["score"]
    report["summary"]["health_grade"] = hs["grade"]
    report["health"] = hs

    reports_dir = state_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    report_path.write_text(render_report(report, root), encoding="utf-8")

    runs_dir = state_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    json_path = runs_dir / f"{report['run_id']}.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report, report_path


def audit(
    root: Path,
    registry_path: Path,
    state_dir: Path,
    dupes: bool = False,
    operator: str = "manual",
) -> tuple[dict, Path]:
    """Run an audit while serializing journal/report writes."""
    with state_operation_lock(state_dir, "audit"):
        return _audit_unlocked(root, registry_path, state_dir, dupes=dupes, operator=operator)


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
    mem = report.get("memory") or {}
    if mem.get("workspace"):
        ws = mem["workspace"]
        lines.append(
            f"- memory-backed workspace: {ws['mount']} ({ws['fstype']}) "
            "- residue here costs RAM, not just disk"
        )
    if mem.get("candidates_on_memory"):
        lines.append(
            f"- memory-backed candidates: {mem['candidates_on_memory']} item(s), "
            f"{mem['candidates_on_memory_mb']} MB on {mem['workspace']['fstype'] if mem.get('workspace') else 'tmpfs/ramfs'} "
            "(RAM, not disk)"
        )
    summary = report.get("summary")
    if summary:
        chain = "OK" if summary["journal_chain_ok"] else "BROKEN"
        lines.append(
            f"- recycle: {summary['recycle_files']} files, {summary['recycle_mb']} MB "
            f"({summary['recycle_ratio_pct']}% of workspace)"
        )
        if "health_score" in summary:
            lines.append(
                f"- health: {summary['health_score']}/100 ({summary['health_grade']})"
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
    if report["sensitive"]:
        lines.append("## Sensitive files (secrets/keys/credentials - never auto-clean these)")
        lines.append("")
        for s in report["sensitive"]:
            lines.append(f"- `{s['path']}` ({s['size']/1024:.1f} KB)")
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
    root = root.resolve()
    state_dir = state_dir.resolve()
    now = now or datetime.now()
    max_mb = registry.get("defaults", {}).get("max_item_mb", 2560)
    window_active = in_protected_window(now, window)
    never_clean = registry.get("never_clean", [])
    never_registry = {"entries": [{"path": p, "grade": "G1", "cleanup": "never"} for p in never_clean]}
    tracked = git_tracked_files(root)
    items: list[dict] = []
    for c in collect_candidates(root, registry, now):
        if c["grade"] not in grades:
            continue
        rel = Path(c["path"])
        reason = ""
        if c["path"] in never_clean or covered_by_any(never_registry, rel):
            reason = "protected"
        elif any(
            e.get("cleanup") == "never"
            and "*" not in str(e.get("path", ""))
            and entry_specificity(e) > entry_specificity({"path": c["path"]})
            and entry_covers({"path": c["path"]}, Path(str(e["path"]).strip("/")))
            for e in registry["entries"]
        ):
            reason = "contains a path protected by a more specific entry"
        elif c["size"] > max_mb * 1024 * 1024:
            reason = f"exceeds single-item limit ({max_mb} MB)"
        elif c.get("protected") and window_active:
            reason = "inside protected window"
        elif tracked is not None and tracked_under(tracked, c["path"]):
            reason = "contains git-tracked files"
        elif sensitive_under(root, rel):
            reason = "contains sensitive files"
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
    root = root.resolve()
    state_dir = state_dir.resolve()
    registry_path = registry_path.resolve()
    registry = load_registry(registry_path)
    if "G3" in grades and not approve:
        raise SystemExit("G3 cleanup requires approval (--approve)")
    with state_operation_lock(state_dir, "clean"):
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

        run_id = f"clean-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
        recycle = state_dir / "recycle" / run_id
        runs_dir = state_dir / "runs"
        manifest = {"run_id": run_id, "ts": now_str(), "items": []}
        moved_ok = 0
        for it in todo:
            src = ensure_within_root(root, root / it["path"], "clean source")
            dst = ensure_within_root(recycle, recycle / it["path"], "recycle target")
            try:
                if dst.exists():
                    print(f"  [skip] {it['path']}: target already exists in recycle")
                    continue
                if not src.exists():
                    print(f"  [skip] {it['path']}: source missing before move")
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


def explain(root: Path, registry_path: Path, state_dir: Path, rel_path: str) -> dict:
    """Explain what the policy says about one path (the 'nutrition label')."""
    registry = load_registry(registry_path)
    rel = Path(rel_path)
    target = root / rel
    if not target.exists():
        raise SystemExit(f"path not found: {rel}")
    rel_s = rel.as_posix()
    entry = most_specific_entry(registry, rel)
    if entry is None:
        return {"path": rel_s, "covered": False, "managed": False}
    info = {
        "path": rel_s,
        "covered": True,
        "managed": entry.get("cleanup") != "never",
        "entry_path": entry["path"],
        "grade": entry["grade"],
        "cleanup": entry.get("cleanup"),
        "retention_days": entry.get("retention_days"),
        "scope": entry.get("scope"),
        "protected": bool(entry.get("protected", False)),
        "remote_authoritative": bool(entry.get("remote_authoritative", False)),
        "category": entry.get("category", ""),
        "note": entry.get("note", ""),
        "owner": entry.get("owner", ""),
        "intent": entry.get("intent", ""),
        "review_after": entry.get("review_after", ""),
    }
    candidates = collect_candidates(root, registry)
    hit = next(
        (c for c in candidates if rel_s == c["path"] or rel_s.startswith(c["path"] + "/")),
        None,
    )
    if hit:
        info["candidate"] = True
        info["candidate_path"] = hit["path"]
        info["age_days"] = hit["age_days"]
        info["files"] = hit["files"]
        info["size"] = hit["size"]
        if hit["grade"] == "G3":
            refs = find_references(root, state_dir, Path(hit["path"]).name)
            info["references"] = refs[:5]
            info["blocked_by_references"] = bool(refs)
    else:
        info["candidate"] = False
    return info


def rollback(root: Path, state_dir: Path, run_id: str, dry: bool = False, operator: str = "manual") -> None:
    root = root.resolve()
    state_dir = state_dir.resolve()
    with state_operation_lock(state_dir, "rollback"):
        manifest_path = state_dir / "runs" / f"{run_id}.json"
        if not manifest_path.exists():
            raise SystemExit(f"run manifest not found: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        recycle = state_dir / "recycle" / run_id
        ok = 0
        for it in reversed(manifest["items"]):
            src = ensure_within_root(recycle, recycle / it["path"], "recycle source")
            dst = ensure_within_root(root, root / it["path"], "restore target")
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
    state_dir = state_dir.resolve()
    with state_operation_lock(state_dir, "purge"):
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
            resolved = ensure_within_root(recycle, run_dir, "recycle batch")
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


# ---------------------------------------------------------------------------
# slim — in-place SQLite trimming (v0.3.0)
# ---------------------------------------------------------------------------

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _valid_identifier(name: str) -> bool:
    return bool(_IDENTIFIER_RE.match(name))


def db_slim_policy(registry: dict | None, db_path: Path) -> dict:
    """Policy for a registered SQLite database (registry entry ``db_slim``).

    The entry matching the database path may carry a ``db_slim`` block::

        {"path": "data/app.db", "grade": "G2", "cleanup": "never",
         "db_slim": {
             "table": "sessions",
             "blob_column": "payload_json",
             "strip_keys": ["factor_observations"],
             "keep_recent": {"table": "epochs", "column": "created_at", "n": 3},
             "vacuum_min_gb": 1.0
         }}

    ``keep_recent`` keeps rows whose reference value is among the newest N
    distinct values of the reference column untouched (e.g. the newest N
    epochs). Matching is path-segment precise (a generic ``data`` entry must
    not shadow ``data/app.db``) and the longest matching entry wins.
    Everything not specified falls back to safe defaults.
    """
    default: dict = {
        "table": None,
        "blob_column": None,
        "strip_keys": [],
        "keep_recent": None,
        "vacuum_min_gb": 1.0,
    }
    if not registry:
        return default
    rel_parts = tuple(PurePosixPath(str(db_path).replace("\\", "/")).parts)
    best: tuple[int, dict] = (-1, default)
    for entry in registry.get("entries", []):
        p = str(entry.get("path", "")).strip("/").replace("\\", "/")
        if not p:
            continue
        p_parts = tuple(PurePosixPath(p).parts)
        if len(p_parts) > len(rel_parts):
            continue
        if rel_parts[-len(p_parts):] == p_parts and len(p_parts) > best[0]:
            policy = dict(default)
            policy.update(entry.get("db_slim") or {})
            best = (len(p_parts), policy)
    return best[1]


def slim(
    db_path: Path,
    registry_path: Path | None,
    state_dir: Path,
    *,
    table: str | None = None,
    blob_column: str | None = None,
    strip_keys: tuple[str, ...] = (),
    keep_recent: int | None = None,
    keep_table: str | None = None,
    keep_column: str | None = None,
    vacuum_min_gb: float | None = None,
    yes: bool = False,
    operator: str = "manual",
) -> dict:
    """Trim heavy JSON fields out of a registered SQLite database in place.

    The DB-internal analogue of ``clean``: no rows are deleted and the file
    itself is never removed — only the JSON blob in one column is rewritten,
    dropping the policy-listed keys. Rows whose reference value is among the
    newest ``keep_recent`` distinct values are skipped. When the reclaimed
    space exceeds ``vacuum_min_gb`` and ``--yes`` is given, ``VACUUM``
    reclaims the freed pages. Every run lands in the hash-chained journal
    (action ``slim``). Dry-run by default; identifiers are validated against
    the database schema (no free-form SQL).
    """
    db_path = db_path.resolve()
    if not db_path.is_file():
        raise SystemExit(f"database not found: {db_path}")

    registry = load_registry(registry_path) if registry_path else None
    policy = db_slim_policy(registry, db_path)
    table = table or policy.get("table")
    blob_column = blob_column or policy.get("blob_column")
    if strip_keys:
        keys = list(strip_keys)
    else:
        keys = list(policy.get("strip_keys") or [])
    keep_n = keep_recent if keep_recent is not None else (
        (policy.get("keep_recent") or {}).get("n") if policy.get("keep_recent") else None
    )
    keep_tbl = keep_table or ((policy.get("keep_recent") or {}).get("table") if policy.get("keep_recent") else None)
    keep_col = keep_column or ((policy.get("keep_recent") or {}).get("column") if policy.get("keep_recent") else None)
    vmin = vacuum_min_gb if vacuum_min_gb is not None else (
        float(policy["vacuum_min_gb"]) if policy.get("vacuum_min_gb") is not None else 1.0
    )

    if not table or not blob_column:
        raise SystemExit(
            "slim needs a table and blob column: set entry.db_slim in the policy "
            "or pass --table/--blob-column"
        )
    if not keys:
        raise SystemExit("slim needs at least one --strip-keys (or entry.db_slim.strip_keys)")
    for name in (table, blob_column, keep_tbl or "", keep_col or ""):
        if name and not _valid_identifier(name):
            raise SystemExit(f"invalid identifier: {name!r}")

    import sqlite3

    con = sqlite3.connect(str(db_path))
    try:
        con.execute("PRAGMA busy_timeout = 30000")
        cols = {row[1] for row in con.execute(f'PRAGMA table_info("{table}")')}
        if blob_column not in cols:
            raise SystemExit(f"column {blob_column!r} not in table {table!r}: {sorted(cols)}")
        if keep_tbl:
            kcols = {row[1] for row in con.execute(f'PRAGMA table_info("{keep_tbl}")')}
            if keep_col not in kcols:
                raise SystemExit(f"column {keep_col!r} not in keep table {keep_tbl!r}: {sorted(kcols)}")
            recent_values = {
                row[0] for row in con.execute(
                    f'SELECT DISTINCT "{keep_col}" FROM "{keep_tbl}" '
                    f'ORDER BY "{keep_col}" DESC LIMIT ?',
                    (int(keep_n),),
                )
            }
        else:
            recent_values = set()

        size_before = db_path.stat().st_size
        rows_scanned = 0
        rows_stripped = 0
        bytes_before = 0
        bytes_after = 0
        cursor = con.execute(
            f'SELECT rowid, "{blob_column}" FROM "{table}"'
        )
        updated: list[tuple] = []
        while True:
            batch = cursor.fetchmany(500)
            if not batch:
                break
            for rid, blob in batch:
                rows_scanned += 1
                if blob is None:
                    continue
                try:
                    obj = json.loads(blob)
                except (ValueError, TypeError):
                    continue
                if not isinstance(obj, dict):
                    continue
                before = len(blob)
                new_obj = {k: v for k, v in obj.items() if k not in keys}
                if len(new_obj) != len(obj):
                    if keep_tbl and str(obj.get(keep_col)) in recent_values:
                        continue
                    bytes_before += before
                    bytes_after += len(json.dumps(new_obj, ensure_ascii=False))
                    rows_stripped += 1
                    if yes:
                        updated.append((json.dumps(new_obj, ensure_ascii=False), rid))
        if yes and updated:
            con.executemany(f'UPDATE "{table}" SET "{blob_column}" = ? WHERE rowid = ?', updated)
            con.commit()
        reclaimed = max(0, bytes_before - bytes_after)
        vacuum_done = False
        if yes and reclaimed / 1e9 >= vmin:
            con.execute("VACUUM")
            con.commit()
            vacuum_done = True
        size_after = db_path.stat().st_size
    finally:
        con.close()

    report = {
        "status": "ok" if yes else "dry_run",
        "db": str(db_path),
        "table": table,
        "blob_column": blob_column,
        "strip_keys": keys,
        "keep_recent": {"table": keep_tbl, "column": keep_col, "n": keep_n} if keep_tbl else None,
        "rows_scanned": rows_scanned,
        "rows_stripped": rows_stripped,
        "size_before_bytes": size_before,
        "size_after_bytes": size_after,
        "reclaimed_bytes": reclaimed,
        "reclaimed_gb": round(reclaimed / 1e9, 3),
        "vacuum_done": vacuum_done,
        "vacuum_min_gb": vmin,
    }
    journal_append(
        state_dir,
        "slim",
        operator,
        registry_sha256=(
            hashlib.sha256(registry_path.read_bytes()).hexdigest() if registry_path else None
        ),
        **report,
    )
    return {"action": "slim", **report}


def doctor(root: Path, registry_path: Path | None, state_dir: Path) -> dict:
    """Run a read-only readiness check for the workspace."""
    root = root.resolve()
    state_dir = state_dir.resolve()
    registry = None
    registry_error = None
    if registry_path is not None:
        registry_path = registry_path.resolve()
        try:
            registry = load_registry(registry_path)
        except SystemExit as exc:
            registry_error = str(exc)
    has_git = (root / ".git").exists()
    tracked = git_tracked_files(root) if has_git else None
    writable = os.access(root, os.W_OK)
    state_writable = os.access(state_dir.parent if state_dir.exists() else state_dir.parent, os.W_OK)
    lock_path = state_dir / ".wm.lock"
    lock_busy = lock_path.exists()
    missing_registry = registry_path is None
    unregistered = None
    sensitive = None
    candidates = None
    if registry is not None:
        candidates = len(collect_candidates(root, registry))
        sensitive = len(scan_sensitive_files(root, state_dir))
        unregistered = 0
        for child in sorted(root.iterdir()):
            rel = child.relative_to(root)
            name = rel.as_posix()
            if name in registry.get("never_clean", []) or name == ".git":
                continue
            if state_dir.is_relative_to(root) and rel == state_dir.relative_to(root):
                continue
            if not covered_by_any(registry, rel):
                unregistered += 1
        tracked_for_audit = git_tracked_files(root)
        if tracked_for_audit is not None:
            unregistered = max(
                0,
                unregistered - sum(
                    1
                    for child in root.iterdir()
                    if any(
                        p == child.name or p.startswith(child.name + "/")
                        for p in tracked_for_audit
                    )
                ),
            )
    result = {
        "root": str(root),
        "state_dir": str(state_dir),
        "root_writable": writable,
        "state_dir_writable": state_writable,
        "lock_path": str(lock_path),
        "lock_busy": lock_busy,
        "git_repo": has_git,
        "git_tracked_files": len(tracked) if tracked else 0,
        "registry_path": str(registry_path) if registry_path else None,
        "registry_present": registry_path is not None,
        "registry_valid": registry is not None if registry_path is not None else False,
        "registry_error": registry_error,
        "missing_registry": missing_registry,
        "workspace_on_memory": bool(memory_backed_info(root)),
        "state_on_memory": bool(memory_backed_info(state_dir)),
        "unregistered": unregistered,
        "sensitive": sensitive,
        "candidates": candidates,
    }
    return result


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
