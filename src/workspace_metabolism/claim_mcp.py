"""Opt-in, one-document MCP editor; credentials stay in the serving process.

This restricts the tools on one stdio connection, not the client's OS permissions.
Disconnecting never releases an unfinished claim or restores a file automatically.
"""

import base64
import difflib
import hashlib
import json
from pathlib import Path
import uuid

from .claim_backend import JsonClaimBackend, git_clean_path
from .claim_guard import ClaimGuard, ClaimRejected, _identity, _path, _snapshot
from .core import govern

MAX_TEXT_BYTES = 16384


def _tool(name, description, properties=None):
    properties = properties or {}
    return {"name": name, "description": description, "inputSchema": {
        "type": "object", "properties": properties, "required": list(properties),
        "additionalProperties": False}}


TOOLS = [
    _tool("wm_edit_read", "Read the one maintenance document assigned by the host; no arbitrary paths."),
    _tool("wm_edit_begin", "Claim the assigned document. Credentials stay in this connection's server.",
          {"task": {"type": "string", "minLength": 1, "maxLength": 500}}),
    _tool("wm_edit_preview", "Prepare an exact replacement and return its diff and identifier. Does not write the document.",
          {"text": {"type": "string", "minLength": 1, "maxLength": MAX_TEXT_BYTES}}),
    _tool("wm_edit_apply", "Apply a previously previewed replacement through the claim guard. Not human approval.",
          {"preview_id": {"type": "string"}}),
    _tool("wm_edit_finish", "Close only after the host has delivered the claimed document to Git. Never commits or runs client commands."),
]


class ClaimEditor:
    def __init__(self, root, policy, state_dir, name):
        self.root = Path(root).resolve()
        if not isinstance(name, str) or Path(name).name != "maintenance.md":
            raise ClaimRejected("pilot scope must be one exact maintenance.md path")
        _path(self.root, name)
        if policy is None or not Path(policy).is_file():
            raise ClaimRejected("an existing governance policy is required")
        self.name, self.policy, self.state_dir = name, policy, state_dir
        self.backend = JsonClaimBackend(self.root)
        self.claim = None
        self.closed = False
        self.previews = {}
        self.applying = None
        self.guard = ClaimGuard(self.root, self.backend, authorize=self._authorize,
                                clean_base=lambda p: git_clean_path(self.root, p))

    def _read(self):
        snapshot = _snapshot(_path(self.root, self.name))
        raw = base64.b64decode(snapshot.get("data", ""))
        if len(raw) > MAX_TEXT_BYTES:
            raise ClaimRejected("pilot document exceeds 16 KiB")
        return snapshot, raw.decode("utf-8")

    def _authorize(self, name):
        # Called by ClaimGuard while holding the registry lock, before any write intent.
        if name != self.name or self.applying is None:
            return False
        snapshot, _ = self._read()
        if _identity(snapshot) != self.applying["base"]:
            raise ClaimRejected("preview is stale; prepare a new preview")
        return govern(self.root, self.policy, self.state_dir, "write",
                      paths=[name], preview=True)["allowed"] is True

    def call(self, name, params):
        spec = next((t for t in TOOLS if t["name"] == name), None)
        if spec is None:
            raise ClaimRejected("tool unavailable in the restricted editing profile")
        required = spec["inputSchema"]["required"]
        if not isinstance(params, dict) or set(params) != set(required):
            raise ClaimRejected("unexpected or missing arguments; paths and credentials are host-owned")
        if any(not isinstance(v, str) for v in params.values()):
            raise ClaimRejected("arguments must be strings")
        if self.closed:
            raise ClaimRejected("editing connection is already finished")
        if name == "wm_edit_read":
            snapshot, text = self._read()
            result = {"path": self.name, "text": text, **_identity(snapshot)}
        elif name == "wm_edit_begin":
            if not params["task"].strip() or len(params["task"]) > 500:
                raise ClaimRejected("task must contain 1-500 characters")
            if self.claim is None:
                self._read()
                self.claim = self.guard.begin(task=params["task"], files=[self.name])
            result = {k: v for k, v in self.claim.items() if k != "session_id"}
        else:
            if self.claim is None:
                raise ClaimRejected("begin a claim on this connection first")
            claim_id, session = self.claim["claim_id"], self.claim["session_id"]
            if name == "wm_edit_preview":
                text = params["text"]
                if not text.strip() or "\0" in text or len(text.encode("utf-8")) > MAX_TEXT_BYTES:
                    raise ClaimRejected("replacement must be nonempty UTF-8 up to 16 KiB")
                if len(self.previews) >= 16:
                    raise ClaimRejected("connection reached 16 previews; host review required")
                snapshot, before = self._read()
                preview_id = uuid.uuid4().hex
                self.previews[preview_id] = {"text": text, "base": _identity(snapshot)}
                result = {"preview_id": preview_id, "path": self.name,
                          "before_sha256": snapshot["sha256"],
                          "after_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                          "diff": "".join(difflib.unified_diff(before.splitlines(keepends=True),
                              text.splitlines(keepends=True), fromfile=self.name, tofile=self.name)),
                          "human_approval": False}
            elif name == "wm_edit_apply":
                preview_id = params["preview_id"]
                if preview_id not in self.previews:
                    raise ClaimRejected("unknown preview on this connection")
                self.applying = self.previews[preview_id]
                try:
                    result = self.guard.write(claim_id, session, path=self.name,
                                              text=self.applying["text"], operation_id=preview_id)
                finally:
                    self.applying = None
            else:
                self.guard.finish(claim_id, session, delivered=lambda c: all(
                    git_clean_path(self.root, p) for p in c["files"]))
                self.closed = True
                result = {"claim_id": claim_id, "status": "done"}
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
