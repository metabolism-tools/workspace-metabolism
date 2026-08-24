"""Minimal zero-dependency MCP stdio server for workspace-metabolism.

Speaks JSON-RPC 2.0 over newline-delimited stdio (the MCP stdio transport).
Agents can run micro-metabolism themselves: audit, health, explain, verify,
and clean. Clean is a dry-run unless the caller explicitly passes
``execute=true`` -- the policy file still decides everything.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path
from typing import Any, Optional

from . import __version__
from .core import audit, clean, explain, health_score, verify

PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "wm_audit",
        "description": "Read-only workspace checkup; returns the full audit report.",
        "inputSchema": {
            "type": "object",
            "properties": {"dupes": {"type": "boolean", "description": "scan for possible duplicates"}},
        },
    },
    {
        "name": "wm_health",
        "description": "Workspace health score (0-100) with component breakdown.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "wm_explain",
        "description": "Explain what the policy says about a path (the nutrition label).",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "relative path inside the workspace"}},
            "required": ["path"],
        },
    },
    {
        "name": "wm_verify",
        "description": "Verify the journal hash chain and run manifests.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "wm_clean",
        "description": (
            "Plan or execute a policy-driven cleanup. Dry-run by default; "
            "set execute=true only when the caller is sure."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "grades": {"type": "string", "default": "G4", "description": "comma-separated grades, e.g. G4 or G3,G4"},
                "execute": {"type": "boolean", "default": False},
                "approve": {"type": "boolean", "default": False},
                "approver": {"type": "string", "description": "required for G3 execution"},
            },
        },
    },
]


def _text_result(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}]}


def _error(message: str) -> dict:
    return {"isError": True, "content": [{"type": "text", "text": message}]}


def _call_tool(name: str, params: dict, ctx: dict) -> dict:
    root: Path = ctx["root"]
    state_dir: Path = ctx["state_dir"]
    registry_path: Optional[Path] = ctx.get("registry_path")
    if registry_path is None:
        return _error("no policy file found; run `wm init` first")
    if name == "wm_audit":
        report, _ = audit(root, registry_path, state_dir, dupes=bool(params.get("dupes")))
        return _text_result(json.dumps(report, ensure_ascii=False, indent=2))
    if name == "wm_health":
        report, _ = audit(root, registry_path, state_dir)
        return _text_result(json.dumps(health_score(report), ensure_ascii=False, indent=2))
    if name == "wm_explain":
        path = str(params.get("path", ""))
        if not path:
            return _error("path is required")
        try:
            info = explain(root, registry_path, state_dir, path)
        except SystemExit as exc:
            return _error(str(exc))
        return _text_result(json.dumps(info, ensure_ascii=False, indent=2))
    if name == "wm_verify":
        return _text_result(json.dumps(verify(state_dir), ensure_ascii=False, indent=2))
    if name == "wm_clean":
        grades = {g.strip().upper() for g in str(params.get("grades", "G4")).split(",") if g.strip()}
        execute = bool(params.get("execute", False))
        approve = bool(params.get("approve", False))
        approver = str(params.get("approver", "") or "")
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                clean(
                    root,
                    registry_path,
                    state_dir,
                    grades,
                    yes=execute,
                    approve=approve,
                    approver=approver or None,
                    operator="agent",
                )
        except SystemExit as exc:
            return _error(str(exc))
        return _text_result(buffer.getvalue())
    return _error(f"unknown tool: {name}")


def handle_message(line: str, ctx: dict) -> Optional[str]:
    """Handle one JSON-RPC line; returns a response line or None for notifications."""
    try:
        msg = json.loads(line)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(msg, dict):
        return None
    method = msg.get("method")
    msg_id = msg.get("id")
    params = msg.get("params") or {}

    if method == "initialize":
        return json.dumps(
            {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "workspace-metabolism", "version": __version__},
                },
            },
            ensure_ascii=False,
        )
    if method == "ping":
        return json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {}})
    if method == "tools/list":
        return json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}, ensure_ascii=False)
    if method == "tools/call":
        name = str(params.get("name", ""))
        arguments = params.get("arguments") or {}
        try:
            result = _call_tool(name, arguments, ctx)
        except Exception as exc:  # noqa: BLE001 - report any tool failure to the client
            return json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32603, "message": f"tool call failed: {exc}"},
                },
                ensure_ascii=False,
            )
        return json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}, ensure_ascii=False)
    if method in ("notifications/initialized", "notifications/cancelled"):
        return None
    if method == "shutdown":
        return json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": None})
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"method not found: {method}"},
        },
        ensure_ascii=False,
    )


def main(root: Path, state_dir: Path, registry_path: Optional[Path]) -> int:
    """Run the stdio loop until EOF or shutdown."""
    ctx = {"root": root, "state_dir": state_dir, "registry_path": registry_path}
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        response = handle_message(line, ctx)
        if response is not None:
            sys.stdout.write(response + "\n")
            sys.stdout.flush()
            try:
                if json.loads(line).get("method") == "shutdown":
                    break
            except (json.JSONDecodeError, TypeError):
                pass
    return 0
