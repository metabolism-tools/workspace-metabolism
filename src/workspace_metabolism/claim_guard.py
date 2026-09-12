"""Cooperative claim-before-write engine, using a host's existing claim backend.

The backend supplies transaction(), load(), and save(registry). Its transaction
must exclude ALL writers to that registry. Caller-supplied sessions are not
authenticated identities; a host adapter must bind them to its runner. This
module neither changes OS permissions nor controls writes outside its entry point.
"""

from __future__ import annotations

import base64
import fnmatch
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
import tempfile
import time
import uuid

MAX_FILE_BYTES = 1024 * 1024


class ClaimRejected(ValueError):
    pass


def _path(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or name != PurePosixPath(name).as_posix() or (
        PurePosixPath(name).is_absolute() or any(c in name for c in "\\:*?[]\x00")
        or any(p in (".", "..") or p.endswith((".", " ")) for p in name.split("/"))
        or any(p.split(".")[0].upper() in {
            "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        } for p in name.split("/"))
    ):
        raise ClaimRejected("an exact relative path is required")
    if name.split("/")[0].casefold() in {".git", ".coordination"}:
        raise ClaimRejected("control files cannot be edited through claims")
    target = root
    for part in name.split("/"):
        target = target / part
        try:
            info = target.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0
        ):
            raise ClaimRejected("linked paths are unsupported")
    if not target.resolve().is_relative_to(root):
        raise ClaimRejected("path leaves workspace")
    return target


def _snapshot(path: Path) -> dict:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"exists": False, "sha256": None}
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_FILE_BYTES:
        raise ClaimRejected("only unlinked regular UTF-8 files up to 1 MiB are supported")
    with path.open("rb") as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES or b"\0" in data:
        raise ClaimRejected("file is too large or binary")
    data.decode("utf-8")
    return {"exists": True, "sha256": hashlib.sha256(data).hexdigest(),
            "mode": stat.S_IMODE(info.st_mode), "data": base64.b64encode(data).decode("ascii")}


def _identity(snapshot: dict) -> dict:
    return {k: v for k, v in snapshot.items() if k != "data"}


def _overlap(name: str, other: dict) -> bool:
    # Conservative case folding also prevents cross-platform duplicate ownership.
    name = name.casefold()
    patterns = list(other.get("files", [])) + list(other.get("dirs", []))
    for pattern in patterns:
        pattern = pattern.replace("\\", "/").rstrip("/").casefold()
        if fnmatch.fnmatchcase(name, pattern) or name.startswith(pattern + "/") or pattern.startswith(name + "/"):
            return True
    return False


def claim_retains_ownership(claim: dict) -> bool:
    guard = claim.get("wm_guard")
    return claim["status"] not in {"done", "closed", "abandon"} or (
        isinstance(guard, dict) and guard.get("pending") is not None
    )


def validate_claim_registry(registry):
    """Validate common registry structure without treating unknown scope as empty."""
    if not isinstance(registry, dict) or registry.get("version") != 1 or not isinstance(registry.get("claims"), list):
        raise ClaimRejected("invalid claim registry; refusing to reset it")
    if any(not isinstance(c, dict) or not isinstance(c.get("id"), str) or not c["id"]
           or not isinstance(c.get("status"), str) or not c["status"]
           for c in registry["claims"]):
        raise ClaimRejected("invalid claim record")
    for claim in registry["claims"]:
        for field in ("files", "dirs"):
            if not isinstance(claim.get(field), list) or any(
                not isinstance(p, str) or not p.strip() for p in claim[field]
            ):
                raise ClaimRejected("invalid claim scope; refusing to assume it is unoccupied")
    if len({c["id"] for c in registry["claims"]}) != len(registry["claims"]):
        raise ClaimRejected("duplicate claim id")
    return registry


class ClaimGuard:
    """Single-file create/replace with durable intent and fail-closed lifecycle.

    authorize(path) must enforce the host's applicable write policy. clean_base
    must reject unexplained pre-existing changes (e.g. compare to Git HEAD).
    Neither callback is inferred from a claim or from file retention grades.
    No deletion, rename, arbitrary shell, auto-commit, takeover, or auto-restore.
    """

    def __init__(self, root: Path, backend, *, authorize, clean_base, clock=time.time):
        self.root = root.resolve()
        self.backend = backend
        self.authorize = authorize
        self.clean_base = clean_base
        self.clock = clock

    def _load(self):
        return validate_claim_registry(self.backend.load())

    def _owned(self, registry, claim_id, session):
        matches = [c for c in registry["claims"] if c["id"] == claim_id]
        if not matches or matches[0].get("wm_guard", {}).get("session_id") != session:
            raise ClaimRejected("claim/session mismatch")
        claim = matches[0]
        if claim["wm_guard"].get("workspace") != str(self.root):
            raise ClaimRejected("claim belongs to a different workspace")
        if claim["status"] != "active":
            raise ClaimRejected("claim is not active")
        return claim

    def _live(self, claim):
        guard = claim["wm_guard"]
        if guard.get("pending"):
            raise ClaimRejected("recovery_required: prior write has no completion receipt")
        if self.clock() >= guard["expires_at"]:
            raise ClaimRejected("claim expired; owning session must explicitly resume")

    def _prepare_files(self, registry, files, *, exclude=None):
        if not isinstance(files, list) or not 1 <= len(files) <= 32:
            raise ClaimRejected("claim requires 1-32 exact file paths")
        bases = {}
        keys = set()
        for name in files:
            path = _path(self.root, name)
            if name.casefold() in keys:
                raise ClaimRejected("duplicate or case-aliased path")
            keys.add(name.casefold())
            for other in registry["claims"]:
                if other["id"] != exclude and claim_retains_ownership(other) and _overlap(name, other):
                    raise ClaimRejected(f"path occupied: {name} by {other['id']}")
            if not self.clean_base(name):
                raise ClaimRejected(f"baseline_unattributed: {name}")
            bases[name] = _identity(_snapshot(path))
        return bases

    @staticmethod
    def _ttl(ttl):
        if type(ttl) is not int or not 1 <= ttl <= 1800:
            raise ClaimRejected("lease must be 1-1800 seconds")

    def begin(self, *, task: str, files: list[str], ttl=1800) -> dict:
        self._ttl(ttl)
        if not isinstance(task, str) or not task.strip():
            raise ClaimRejected("task is required")
        with self.backend.transaction():
            registry = self._load()
            bases = self._prepare_files(registry, files)
            now = self.clock()
            claim = {"id": "wm-" + uuid.uuid4().hex, "tool": "wm", "task": task,
                     "status": "active", "files": list(bases), "dirs": [],
                     "wm_guard": {"version": 1, "workspace": str(self.root), "session_id": uuid.uuid4().hex,
                                  "generation": 1, "expires_at": now + ttl,
                                  "base": bases, "current": dict(bases), "pending": None,
                                  "receipts": []}}
            registry["claims"].append(claim)
            self.backend.save(registry)
            return {"claim_id": claim["id"], "session_id": claim["wm_guard"]["session_id"],
                    "expires_at": now + ttl, "files": list(bases)}

    def expand(self, claim_id, session, files):
        if not isinstance(files, list) or not files or any(not isinstance(n, str) for n in files):
            raise ClaimRejected("expansion requires exact file paths")
        with self.backend.transaction():
            registry = self._load()
            claim = self._owned(registry, claim_id, session)
            self._live(claim)
            if len(claim["files"]) + len(files) > 32:
                raise ClaimRejected("claim exceeds 32 files")
            if {n.casefold() for n in files} & {n.casefold() for n in claim["files"]}:
                raise ClaimRejected("path is already claimed")
            bases = self._prepare_files(registry, files, exclude=claim_id)
            claim["files"].extend(bases)
            claim["wm_guard"]["base"].update(bases)
            claim["wm_guard"]["current"].update(bases)
            self.backend.save(registry)

    def renew(self, claim_id, session, ttl=1800):
        self._ttl(ttl)
        with self.backend.transaction():
            registry = self._load()
            claim = self._owned(registry, claim_id, session)
            self._live(claim)
            claim["wm_guard"]["expires_at"] = self.clock() + ttl
            self.backend.save(registry)

    def resume(self, claim_id, session, ttl=1800):
        """Explicit same-owner continuation; rotate the session, never adopt outside edits."""
        self._ttl(ttl)
        with self.backend.transaction():
            registry = self._load()
            claim = self._owned(registry, claim_id, session)
            guard = claim["wm_guard"]
            if guard.get("pending"):
                raise ClaimRejected("recovery_required: reconcile the pending write first")
            for name, expected in guard["current"].items():
                if _identity(_snapshot(_path(self.root, name))) != expected:
                    raise ClaimRejected("file changed outside this claim; cannot resume")
            continuations = guard.setdefault("continuations", [])
            if len(continuations) >= 64:
                raise ClaimRejected("claim reached 64 continuations")
            now = self.clock()
            generation = guard["generation"] + 1
            continuations.append({"from_generation": guard["generation"], "to_generation": generation,
                                  "at": now, "was_expired": now >= guard["expires_at"]})
            guard.update(session_id=uuid.uuid4().hex, generation=generation, expires_at=now + ttl)
            self.backend.save(registry)
            return {"claim_id": claim_id, "session_id": guard["session_id"],
                    "generation": generation, "expires_at": now + ttl}

    def recover(self, claim_id, session):
        """Reconcile an uncertain write by observation only; never change target bytes.

        Matching the intended result is not proof of who wrote it. Unknown contents
        retain the pending intent and ownership. Lease renewal is a separate action.
        """
        with self.backend.transaction():
            registry = self._load()
            claim = self._owned(registry, claim_id, session)
            guard = claim["wm_guard"]
            pending = guard.get("pending")
            if pending is None:
                return {"status": "no_pending", "files_written": 0}
            if (not isinstance(pending, dict) or not isinstance(pending.get("request"), dict)
                    or not isinstance(pending.get("before"), dict)
                    or not {"path", "sha256"} <= pending["request"].keys()
                    or not {"exists", "sha256"} <= pending["before"].keys()
                    or not isinstance(pending.get("operation_id"), str) or "at" not in pending):
                raise ClaimRejected("invalid pending intent; recovery requires host review")
            path = pending["request"]["path"]
            if path not in guard["current"] or _identity(pending["before"]) != guard["current"][path]:
                raise ClaimRejected("pending intent does not match the recorded baseline")
            for name, expected in guard["current"].items():
                if name != path and _identity(_snapshot(_path(self.root, name))) != expected:
                    raise ClaimRejected("another claimed file changed; recovery blocked")
            observed = _identity(_snapshot(_path(self.root, path)))
            before = pending["before"]
            if observed == _identity(before):
                outcome = "original_observed"
            elif (observed["exists"] and observed["sha256"] == pending["request"]["sha256"]
                  and (not before["exists"] or observed["mode"] == before["mode"])):
                outcome = "intended_observed"
            else:
                raise ClaimRejected("unrecognized file state; evidence and ownership retained")
            recoveries = guard.setdefault("recoveries", [])
            if len(recoveries) >= 64:
                raise ClaimRejected("claim reached 64 recovery records")
            at = self.clock()
            event = {"operation_id": pending["operation_id"], "request": pending["request"],
                     "before": before, "observed": observed, "outcome": outcome,
                     "intent_at": pending["at"], "at": at}
            if outcome == "intended_observed":
                if len(guard["receipts"]) >= 64 or any(
                    r["operation_id"] == pending["operation_id"] for r in guard["receipts"]
                ):
                    raise ClaimRejected("pending intent conflicts with receipt history")
                guard["receipts"].append({"operation_id": pending["operation_id"],
                    "request": pending["request"], "before": before, "after": observed,
                    "at": at, "observation_only": True, "recovered": True})
                event["before"] = _identity(before)  # Original bytes are retained once, in the receipt.
                guard["current"][path] = observed
            recoveries.append(event)
            guard["pending"] = None
            self.backend.save(registry)
            return {"status": "reconciled", "outcome": outcome, "files_written": 0,
                    "operation_id": pending["operation_id"], "observed": observed}

    def write(self, claim_id, session, *, path, text, operation_id):
        if not isinstance(operation_id, str) or not operation_id or len(operation_id) > 128:
            raise ClaimRejected("operation_id is required (up to 128 characters)")
        if not isinstance(text, str) or "\0" in text or len(text.encode("utf-8")) > MAX_FILE_BYTES:
            raise ClaimRejected("replacement must be UTF-8 text up to 1 MiB")
        data = text.encode("utf-8")
        request = {"path": path, "sha256": hashlib.sha256(data).hexdigest()}
        with self.backend.transaction():
            registry = self._load()
            claim = self._owned(registry, claim_id, session)
            self._live(claim)
            guard = claim["wm_guard"]
            if path not in guard["current"]:
                raise ClaimRejected("path is outside claimed scope")
            target = _path(self.root, path)
            before = _snapshot(target)
            if _identity(before) != guard["current"][path]:
                raise ClaimRejected("file changed outside this claim")
            for receipt in guard["receipts"]:
                if receipt["operation_id"] == operation_id:
                    if receipt["request"] != request:
                        raise ClaimRejected("operation_id reused with different content")
                    return dict({k: v for k, v in receipt.items() if k != "before"}, replayed=True)
            if any(event["operation_id"] == operation_id and event["request"] != request
                   for event in guard.get("recoveries", [])):
                raise ClaimRejected("operation_id reused with different content after recovery")
            if len(guard["receipts"]) >= 64 or len(guard.get("recoveries", [])) >= 64:
                raise ClaimRejected("claim reached its write/recovery record limit")
            if self.authorize(path) is not True:
                raise ClaimRejected("host policy denied write")
            evidence_size = sum(len(r["before"].get("data", "")) for r in (
                guard["receipts"] + guard.get("recoveries", [])))
            if evidence_size + len(before.get("data", "")) > 8 * 1024 * 1024:
                raise ClaimRejected("claim recovery evidence exceeds 8 MiB")
            # Persist intent and recoverable original bytes BEFORE changing the target.
            guard["pending"] = {"operation_id": operation_id, "request": request,
                                "before": before, "at": self.clock()}
            self.backend.save(registry)
            if self.clock() >= guard["expires_at"]:
                raise ClaimRejected("claim expired after intent; recovery check required")
            if _identity(_snapshot(_path(self.root, path))) != _identity(before):
                raise ClaimRejected("file changed before replacement; recovery check required")
            self._replace(target, data, before)
            after = _snapshot(_path(self.root, path))
            if after["sha256"] != request["sha256"]:
                raise ClaimRejected("recovery_required: write result mismatch")
            receipt = {"operation_id": operation_id, "request": request,
                       "before": before, "after": _identity(after), "at": self.clock()}
            guard["current"][path] = _identity(after)
            guard["receipts"].append(receipt)
            guard["pending"] = None
            self.backend.save(registry)
            # Do not return original source contents to an ordinary tool caller.
            return {k: v for k, v in receipt.items() if k != "before"}

    @staticmethod
    def _replace(target, data, before):
        if not before["exists"]:
            # Parent creation is not implicit: callers must separately arrange it.
            with target.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            return
        fd, name = tempfile.mkstemp(prefix=".wm-claim-", dir=target.parent)
        temporary = Path(name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.chmod(before["mode"])
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)

    def finish(self, claim_id, session, *, delivered):
        """Release only after a host-verified delivery; does not commit or delete evidence."""
        with self.backend.transaction():
            registry = self._load()
            claim = self._owned(registry, claim_id, session)
            self._live(claim)
            for name, current in claim["wm_guard"]["current"].items():
                if _identity(_snapshot(_path(self.root, name))) != current:
                    raise ClaimRejected("file changed before delivery")
            if not delivered(claim):
                raise ClaimRejected("delivery not verified; ownership retained")
            claim["status"] = "done"
            claim["wm_guard"]["closed_at"] = self.clock()
            self.backend.save(registry)
