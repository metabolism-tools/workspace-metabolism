"""Standalone claim backend. Existing foreign registries require a host adapter."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import time

from .claim_guard import ClaimRejected, _overlap, _path, claim_retains_ownership, validate_claim_registry


class JsonClaimBackend:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.directory = self.root / ".coordination"
        self.path = self.directory / "registry.json"

    def _safe(self):
        for path in (self.directory, self.path, self.directory / ".wm-registry.lock"):
            if path.is_symlink():
                raise ClaimRejected("linked claim storage is unsupported")
            if path.exists():
                info = path.lstat()
                if getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
                    raise ClaimRejected("linked claim storage is unsupported")
                if path != self.directory and info.st_nlink != 1:
                    raise ClaimRejected("aliased claim storage is unsupported")

    @contextmanager
    def transaction(self):
        self._safe()
        if self.path.exists():
            self.load()  # Reject a foreign registry before creating even a lock file.
        self.directory.mkdir(exist_ok=True)
        # Stable inode and OS-owned lock: never unlink a live or supposedly stale lock.
        with (self.directory / ".wm-registry.lock").open("a+b") as stream:
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            deadline = time.monotonic() + 10
            while True:
                try:
                    stream.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise ClaimRejected("claim storage busy; no lock was broken")
                    time.sleep(0.05)
            try:
                self._safe()
                yield
            finally:
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream, fcntl.LOCK_UN)

    def load(self):
        if not self.path.exists():
            return {"version": 1, "wm_claim_backend": 1, "claims": []}
        with self.path.open("rb") as stream:
            raw = stream.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise ClaimRejected("claim registry exceeds 16 MiB; archival review required")
        registry = json.loads(raw)
        if not isinstance(registry, dict) or registry.get("wm_claim_backend") != 1:
            raise ClaimRejected("existing host claim registry requires an adapter; refusing a second authority")
        return registry

    def save(self, registry):
        raw = json.dumps(registry, ensure_ascii=False, indent=2).encode("utf-8")
        if len(raw) > 16 * 1024 * 1024:
            raise ClaimRejected("claim registry exceeds 16 MiB; archival review required")
        fd, name = tempfile.mkstemp(prefix=".registry-", suffix=".tmp", dir=self.directory)
        temporary = Path(name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)

    def cleanup_claims(self):
        """Read retention scopes; caller must hold transaction through any move."""
        self._safe()
        registry = validate_claim_registry(self.load())
        retained = []
        for claim in registry["claims"]:
            guard = claim.get("wm_guard")
            if (not isinstance(guard, dict) or guard.get("version") != 1
                    or guard.get("workspace") != str(self.root) or "pending" not in guard
                    or not (claim["files"] or claim["dirs"])):
                raise ClaimRejected("claim retention metadata requires host review")
            for name in claim["files"] + claim["dirs"]:
                _path(self.root, name)
            if claim_retains_ownership(claim):
                retained.append(claim)
        return retained


def claim_cleanup_reason(root: Path, name: str, claims: list[dict]) -> str:
    """Protect ownership and control directories, including ancestor cleanup."""
    if name == "." or ".coordination" in name.casefold().split("/"):
        return "claim control storage is protected"
    if any(_overlap(name, claim) for claim in claims):
        return "claim ownership or pending write retained"

    def unreadable(error):
        raise error

    try:
        target = root / name
        try:
            info = target.lstat()
        except FileNotFoundError:
            return ""
        if not stat.S_ISDIR(info.st_mode):
            return ""
        for _, dirs, files in os.walk(target, followlinks=False, onerror=unreadable):
            if any(p.casefold() == ".coordination" for p in dirs + files):
                return "contains claim control storage; host review required"
    except OSError:
        return "claim storage scan failed; host review required"
    return ""


def git_clean_path(root: Path, name: str) -> bool:
    """Require a Git baseline; reject tracked, staged, or untracked existing changes."""
    if (root / name).exists():
        tracked = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-v", "-z", "--", name],
            capture_output=True, timeout=15,
        )
        if tracked.returncode != 0 or not tracked.stdout.startswith(b"H "):
            return False  # Includes ignored/untracked and skip-worktree/assume-unchanged files.
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", name],
        capture_output=True, timeout=15,
    )
    return result.returncode == 0 and not result.stdout
