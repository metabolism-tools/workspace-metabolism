"""Experimental, cooperative local change review. Not a security sandbox."""

from __future__ import annotations

import base64
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tempfile
import time
import uuid

from .core import govern, journal_append, load_registry, state_operation_lock


def _digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _path(root: Path, name: str) -> Path:
    parts = PurePosixPath(name).parts
    if not parts or name != PurePosixPath(name).as_posix() or any(
        p in (".", "..") or ":" in p or "\\" in p or p.endswith((" ", "."))
        for p in parts
    ) or PurePosixPath(name).is_absolute():
        raise ValueError(f"invalid relative file path: {name}")
    current = root
    for part in parts:
        current = current / part
        attributes = getattr(current.lstat(), "st_file_attributes", 0) if current.exists() else 0
        if current.is_symlink() or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise ValueError(f"linked paths are unsupported: {name}")
    if not current.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"path leaves workspace: {name}")
    return current


def _snapshot(path: Path) -> dict:
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 1024 * 1024:
        raise ValueError(f"only ordinary files up to 1 MiB are supported: {path}")
    data = path.read_bytes()
    data.decode("utf-8")
    if b"\0" in data:
        raise ValueError(f"binary file is unsupported: {path}")
    return {"data": base64.b64encode(data).decode("ascii"), "mode": stat.S_IMODE(info.st_mode)}


def _replace(path: Path, snapshot: dict) -> None:
    fd, name = tempfile.mkstemp(prefix=".wm-change-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(base64.b64decode(snapshot["data"], validate=True))
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(snapshot["mode"])
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _save(bundle: Path, manifest: dict) -> None:
    _replace(bundle / "manifest.json", {
        "data": base64.b64encode(json.dumps(manifest, indent=2).encode()).decode(),
        "mode": 0o600,
    })


def _event(state: Path, manifest: dict, action: str, **fields) -> None:
    with state_operation_lock(state, "change-event"):
        journal_append(state, "change_" + action, "manual", manifest["policy_hash"],
                       change_id=manifest["id"], **fields)


def _current(root: Path, manifest: dict) -> dict:
    return {name: _snapshot(_path(root, name)) for name in manifest["base"]}


def _policy_hash(policy: Path) -> str:
    return hashlib.sha256(policy.read_bytes()).hexdigest()


def _review(root: Path, bundle: Path, manifest: dict) -> dict:
    if manifest["status"] not in ("prepared", "reviewed"):
        raise ValueError("this change is already consumed; prepare a new change")
    if _current(root, manifest) != manifest["base"]:
        raise ValueError("original files changed; prepare a new change")
    if _policy_hash(Path(manifest["policy"])) != manifest["policy_hash"]:
        raise ValueError("policy changed; prepare a new change")
    draft = bundle / "draft"
    found = set()
    for directory, dirs, files in os.walk(draft, followlinks=False):
        for name in dirs + files:
            relative = (Path(directory) / name).relative_to(draft).as_posix()
            _path(draft, relative)
        found.update((Path(directory) / name).relative_to(draft).as_posix() for name in files)
    if found != set(manifest["base"]):
        raise ValueError("added or deleted files are not allowed (including protected files)")
    after = _current(draft, manifest)
    changes = {name: value for name, value in after.items() if value != manifest["base"][name]}
    if not changes:
        raise ValueError("no changes to review")
    for name in changes:
        if name in manifest["protected"]:
            raise ValueError(f"protected file changed: {name}")
        if after[name]["mode"] != manifest["base"][name]["mode"]:
            raise ValueError(f"file mode changes are unsupported: {name}")
    diff = ""
    for name in changes:
        before_text = base64.b64decode(manifest["base"][name]["data"]).decode("utf-8")
        after_text = base64.b64decode(after[name]["data"]).decode("utf-8")
        diff += "".join(difflib.unified_diff(before_text.splitlines(keepends=True),
                                           after_text.splitlines(keepends=True),
                                           fromfile="before/" + name, tofile="after/" + name))
    return {"contract": manifest["contract"], "base": manifest["base"],
            "protected": manifest["protected"], "policy_hash": manifest["policy_hash"],
            "change_id": manifest["id"], "root": manifest["root"],
            "after": after, "diff": diff, "expires": time.time() + 3600}


def run_change(root: Path, state: Path, policy: Path | None, command: str, *,
               change_id: str | None = None, files: list[str] | None = None,
               protected: list[str] | None = None, goal: str = "", acceptance: str = "",
               approval: str = "", approver: str = "") -> dict:
    """Run one step. Caller must keep the original workspace idle during writes."""
    root, state = root.resolve(), state.resolve()
    if state.is_relative_to(root) or root.is_relative_to(state):
        raise ValueError("change state must be outside and separate from the workspace")
    store = state / "changes"
    with state_operation_lock(store, "change-" + command):
        if command == "prepare":
            if not policy or not goal.strip() or not acceptance.strip():
                raise ValueError("prepare requires a policy, goal and acceptance criteria")
            load_registry(policy)
            names = sorted(set((files or []) + (protected or [])))
            if not names or len(names) > 100:
                raise ValueError("select between 1 and 100 existing UTF-8 files")
            base = {name: _snapshot(_path(root, name)) for name in names}
            if len({os.path.normcase(str(_path(root, name))) for name in names}) != len(names):
                raise ValueError("duplicate file aliases are unsupported")
            if any(_path(root, name).resolve() == policy.resolve() or name.split('/')[0].lower() == '.git'
                   for name in names):
                raise ValueError("policy and Git metadata cannot be change targets")
            change_id = uuid.uuid4().hex
            bundle = store / change_id
            (bundle / "draft").mkdir(parents=True)
            manifest = {"id": change_id, "root": str(root), "policy": str(policy.resolve()),
                        "policy_hash": _policy_hash(policy), "base": base,
                        "protected": sorted(set(protected or [])), "status": "prepared",
                        "contract": {"goal": goal, "acceptance": acceptance}}
            for name, value in base.items():
                target = _path(bundle / "draft", name)
                target.parent.mkdir(parents=True, exist_ok=True)
                _replace(target, value)
            _save(bundle, manifest)
            _event(state, manifest, "prepared", contract=manifest["contract"], files=names)
            return {"id": change_id, "draft": str(bundle / "draft"), "status": "prepared"}
        if not change_id or len(change_id) != 32 or any(c not in "0123456789abcdef" for c in change_id):
            raise ValueError("invalid change ID")
        bundle = store / change_id
        manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
        if manifest["root"] != str(root):
            raise ValueError("change belongs to a different workspace")
        if command == "review":
            review = _review(root, bundle, manifest)
            manifest.update(status="reviewed", review=review, digest=_digest(review))
            _save(bundle, manifest)
            _event(state, manifest, "reviewed", digest=manifest["digest"])
            return {"id": change_id, "digest": manifest["digest"], "diff": review["diff"],
                    "acceptance": manifest["contract"]["acceptance"], "expires": review["expires"]}
        if command == "apply":
            review = manifest.get("review", {})
            if manifest["status"] != "reviewed" or not approval or approval != _digest(review):
                raise ValueError("apply requires the exact unconsumed review digest")
            if not approver.strip() or not acceptance.strip():
                raise ValueError("provide an approver declaration and actual acceptance evidence")
            if time.time() > review["expires"]:
                raise ValueError("review expired; review again")
            fresh = _review(root, bundle, manifest)
            fresh["expires"] = review["expires"]
            if fresh != review:
                raise ValueError("proposal changed; review again")
            changed = [n for n in review["after"] if review["after"][n] != manifest["base"][n]]
            registry = load_registry(Path(manifest["policy"]))
            for protected_path in (registry.get("ai_governance") or {}).get("protected_paths", []):
                protected_target = (root / protected_path).resolve()
                if any(_path(root, n).resolve().is_relative_to(protected_target) for n in changed):
                    raise ValueError(f"policy denied: protected path {protected_path}")
            decision = govern(root, Path(manifest["policy"]), state, "write", paths=changed,
                              preview=True, approver=approver, operator="change")
            if not decision["allowed"]:
                raise ValueError("policy denied: " + "; ".join(decision["reasons"]))
            if decision["policy_sha256"] != manifest["policy_hash"]:
                raise ValueError("policy changed; prepare a new change")
            if _current(root, manifest) != manifest["base"]:
                raise ValueError("original files changed; prepare a new change")
            manifest.update(status="applying", approver=approver, evidence=acceptance)
            _save(bundle, manifest)
            _event(state, manifest, "applying", digest=approval, approver=approver,
                   acceptance_evidence=acceptance, decision_id=decision["decision_id"])
            try:
                for name in changed:
                    target = _path(root, name)
                    if _snapshot(target) != manifest["base"][name]:
                        raise ValueError(f"concurrent change detected: {name}")
                    _replace(target, review["after"][name])
                if _current(root, manifest) != review["after"]:
                    raise ValueError("post-write verification failed")
            except Exception as exc:
                manifest["status"] = "recovery_required"
                manifest["error"] = str(exc)
                _save(bundle, manifest)
                _event(state, manifest, "recovery_required", error=str(exc))
                raise ValueError("apply interrupted; use restore; backups retained") from exc
            manifest["status"] = "applied"
        elif command == "restore":
            if manifest["status"] not in ("applied", "applying", "recovery_required", "restoring"):
                raise ValueError("only applied or interrupted changes can be restored")
            after = manifest["review"]["after"]
            current = _current(root, manifest)
            if any(current[n] not in (manifest["base"][n], after[n]) for n in current):
                raise ValueError("files changed after apply; restore would overwrite newer work")
            manifest["status"] = "restoring"
            _save(bundle, manifest)
            for name in current:
                if current[name] != manifest["base"][name]:
                    target = _path(root, name)
                    if _snapshot(target) != current[name]:
                        raise ValueError("concurrent change during restore; backups retained")
                    _replace(target, manifest["base"][name])
            if _current(root, manifest) != manifest["base"]:
                raise ValueError("restore verification failed; backups retained")
            manifest["status"] = "restored"
        else:
            raise ValueError(f"unknown change command: {command}")
        _save(bundle, manifest)
        _event(state, manifest, manifest["status"], digest=manifest.get("digest"))
        return {"id": change_id, "status": manifest["status"]}
