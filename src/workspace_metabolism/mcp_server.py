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
from .core import POLICY_FILENAMES, audit, clean, explain, health_score, init_policy, rollback, verify

PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "wm_audit",
        "description": (
            "Run a read-only workspace audit and return the complete report as JSON: every path the policy "
            "covers, its grade (G1-G4), its cleanup state, and any anomalies. Use this at the start of a "
            "session to see what the metabolism policy says about the workspace, or before planning any "
            "cleanup. Never moves or modifies any files; if no policy file exists it reports that instead of "
            "failing."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "dupes": {
                    "type": "boolean",
                    "description": "When true, additionally scan for possible duplicate files (slower).",
                }
            },
        },
    },
    {
        "name": "wm_health",
        "description": (
            "Compute the workspace health score (0-100) and return it with the per-component breakdown "
            "(coverage, compliance, cleanliness) as JSON. Use this to quantify in one number how well the "
            "workspace follows its policy, e.g. for CI gates or session-end reporting. Read-only; requires a "
            "policy file — if none exists it returns an error telling you to run 'wm init'."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "wm_explain",
        "description": (
            "Return the 'nutrition label' for one path: the grade the policy assigns (G1-G4), why it is "
            "graded that way, and what cleanup would do to it. Use this when you or the user ask why a "
            "specific file or directory is (or is not) cleanup-worthy. Read-only; fails with a clear message "
            "if the path is outside the workspace or the policy is missing."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to explain, relative to the workspace root (e.g. 'logs' or 'src/util.py').",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "wm_verify",
        "description": (
            "Verify the integrity of the audit trail: check that the hash-chained journal has not been "
            "tampered with and that run manifests are consistent, returning pass/fail per check with details "
            "as JSON. Use this before trusting any previous clean/rollback history, or after suspecting "
            "manual edits to the journal. Read-only."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "wm_clean",
        "description": (
            "Plan or execute a policy-driven cleanup. By default it is a dry-run: returns the exact plan "
            "(what would be moved to the recycle area, with per-file SHA-256 hashes) and changes nothing. "
            "Pass execute=true to apply the plan: items are moved to a recycle area, never deleted by "
            "pattern, and every action lands in the hash-chained journal so rollback is possible. Use it "
            "when the workspace has accumulated policy-expired byproducts. Do NOT set execute=true without "
            "first running a dry-run and confirming the plan; G3 execution additionally requires approve=true "
            "and an approver."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "grades": {
                    "type": "string",
                    "default": "G4",
                    "description": "Comma-separated grades to clean, e.g. 'G4' or 'G3,G4'. Defaults to G4, the most aggressive auto-cleanable grade.",
                },
                "execute": {
                    "type": "boolean",
                    "default": False,
                    "description": "When false (default) this is a dry-run and nothing changes; set true to actually move files to the recycle area.",
                },
                "approve": {
                    "type": "boolean",
                    "default": False,
                    "description": "Human approval gate; required together with 'approver' for G3-grade execution.",
                },
                "approver": {
                    "type": "string",
                    "description": "Name of the person or system approving G3 execution; required when grades include G3 and is recorded in the audit journal.",
                },
            },
        },
    },
    {
        "name": "wm_init",
        "description": (
            "Scaffold the metabolism.json policy file for this workspace (like git init): scans the "
            "workspace and generates a policy that grades every directory G1-G4 with safe defaults — "
            "source, docs, tests, secrets, dotfiles and version control are never auto-cleaned. Use this "
            "once, when no policy file exists, before the first audit or clean; after it succeeds, "
            "wm_audit and wm_clean can operate. Fails without writing anything if a policy already "
            "exists and force is not set."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "force": {
                    "type": "boolean",
                    "default": False,
                    "description": "Overwrite an existing policy file instead of failing. Only set this when you explicitly want to regenerate the whole policy from scratch — a hand-tuned policy with custom entries will be replaced.",
                }
            },
        },
    },
    {
        "name": "wm_rollback",
        "description": (
            "Restore the items of a previous wm_clean run from the recycle area back to their original "
            "locations. Every item is verified against its recorded SHA-256 hashes first; items that fail "
            "the integrity check, are missing, or would overwrite an existing file are skipped with a "
            "reason. Use this to undo a cleanup you just executed, passing the run id printed by "
            "wm_clean. Dry-run by default; set execute=true to actually restore. Fails with a clear "
            "message if the run id is unknown."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {
                    "type": "string",
                    "description": "The cleanup run id to restore, as printed by wm_clean, e.g. 'clean-20260831-153000-123456'.",
                },
                "execute": {
                    "type": "boolean",
                    "default": False,
                    "description": "When false (default) this is a dry-run preview and nothing changes; set true to actually restore the files.",
                },
            },
            "required": ["run_id"],
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
    if name == "wm_init":
        force = bool(params.get("force", False))
        try:
            created = init_policy(root, root / POLICY_FILENAMES[0], force=force)
        except SystemExit as exc:
            return _error(str(exc))
        return _text_result(f"created policy file: {created}")
    if name == "wm_rollback":
        run_id = str(params.get("run_id", "")).strip()
        if not run_id:
            return _error("run_id is required")
        execute = bool(params.get("execute", False))
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                rollback(root, state_dir, run_id, dry=not execute, operator="agent")
        except SystemExit as exc:
            return _error(str(exc))
        return _text_result(buffer.getvalue())
    if registry_path is None and root is not None:
        # Auto-discover the policy if it appeared after the server started (e.g. via wm_init).
        for policy_name in POLICY_FILENAMES:
            candidate = root / policy_name
            if candidate.exists():
                registry_path = candidate
                break
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
