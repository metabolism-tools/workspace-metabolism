"""wm gate — MCP governance proxy.

Wraps any MCP stdio server and routes every ``tools/call`` through the
workspace policy before forwarding it. Denied calls never reach the target;
every decision (allow or deny) lands in the hash-chained journal via
``govern``, so the journal shows the full intent -> decision -> execution
chain.

This is a governance and audit layer, not a sandbox: a compromised or
malicious agent can bypass the proxy and talk to the target directly.
Gate governs the cooperative agent; OS-level sandboxing governs the hostile
one.

Transport: newline-delimited JSON-RPC 2.0 over stdio (the MCP stdio
transport), same as :mod:`workspace_metabolism.mcp_server`.
"""

from __future__ import annotations

import fnmatch
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .core import load_registry, govern


def _path_like(name: str) -> bool:
    """Heuristic: is an inputSchema property likely a filesystem path?"""
    n = name.lower()
    return (
        n in {"path", "paths", "file", "files", "dir", "directory", "source", "destination", "target", "uri", "url"}
        or n.endswith("_path")
        or n.endswith("path")
        or n.endswith("_file")
        or n.endswith("dir")
    )


def _extract_paths(arguments: dict, schema: dict) -> list[str]:
    """Pull path-like argument values out of a tools/call payload."""
    props = (schema or {}).get("properties") or {}
    paths: list[str] = []
    for name, value in (arguments or {}).items():
        if not _path_like(str(name)):
            continue
        if isinstance(value, str) and value.strip():
            paths.append(value.strip())
        elif isinstance(value, list):
            paths.extend(str(v) for v in value if isinstance(v, str) and v.strip())
    return paths


def _action_for(tool_name: str, registry: dict) -> str:
    """Map a tool name to an AI action via ``ai_governance.tool_patterns``.

    Unmatched tools default to ``execute`` — the most conservative action in
    the default policy (requires approval).
    """
    patterns = ((registry.get("ai_governance") or {}).get("tool_patterns") or {})
    for pattern, action in patterns.items():
        if fnmatch.fnmatch(tool_name, pattern):
            return str(action)
    return "execute"


def _deny_result(message: str) -> str:
    return json.dumps(
        {
            "content": [{"type": "text", "text": message}],
            "isError": True,
        },
        ensure_ascii=False,
    )


def gate_main(
    root: Path,
    state_dir: Path,
    registry_path: Optional[Path],
    target: list[str],
) -> int:
    """Run the governance proxy until EOF or shutdown."""
    if not target:
        raise SystemExit("gate needs a target command: wm gate --target 'python -m server'")
    if registry_path is None:
        raise SystemExit("gate needs a policy file; run `wm init` first (or pass --registry)")
    registry = load_registry(registry_path)
    print(
        "\n[wm gate] EXPERIMENTAL — audit/observe layer, NOT a sandbox.\n"
        "  A compromised or malicious agent can bypass this proxy and call the target\n"
        "  server directly. approver fields are auditable declarations, not\n"
        "  authentication. Do not rely on gate as a security boundary.\n",
        file=sys.stderr,
    )
    child = subprocess.Popen(
        target,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None,  # child stderr flows to our stderr, so server logs stay visible
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    if child.stdin is None or child.stdout is None:
        raise SystemExit("failed to start target MCP server")

    tool_schemas: dict[str, dict] = {}

    def forward(line: str) -> Optional[str]:
        """Send one line to the child and return its response line (if any)."""
        child.stdin.write(line + "\n")
        child.stdin.flush()
        response = child.stdout.readline()
        if not response:
            return None
        return response.rstrip("\n")

    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(msg, dict):
            continue
        method = msg.get("method")
        msg_id = msg.get("id")
        params = msg.get("params") or {}

        if method in ("notifications/initialized", "notifications/cancelled"):
            forward(line)
            continue
        if method in ("initialize", "ping"):
            response = forward(line)
            if response is not None:
                sys.stdout.write(response + "\n")
                sys.stdout.flush()
            continue
        if method == "tools/list":
            response = forward(line)
            if response is not None:
                try:
                    payload = json.loads(response)
                    for tool in (payload.get("result") or {}).get("tools") or []:
                        tool_schemas[tool.get("name", "")] = tool.get("inputSchema") or {}
                except (json.JSONDecodeError, TypeError):
                    pass
                sys.stdout.write(response + "\n")
                sys.stdout.flush()
            continue
        if method == "tools/call":
            name = str(params.get("name", ""))
            arguments = params.get("arguments") or {}
            action = _action_for(name, registry)
            paths = _extract_paths(arguments, tool_schemas.get(name, {}))
            preview = bool(arguments.get("preview", False))
            decision = govern(
                root,
                registry_path,
                state_dir,
                action,
                paths=paths or None,
                preview=preview,
                operator="gate",
            )
            if not decision["allowed"]:
                reasons = "; ".join(decision["reasons"])
                sys.stdout.write(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": msg_id,
                            "result": {
                                "content": [
                                    {
                                        "type": "text",
                                        "text": (
                                            f"blocked by workspace policy: {name} ({action}) — {reasons}. "
                                            f"decision_id={decision['decision_id']}"
                                        ),
                                    }
                                ],
                                "isError": True,
                            },
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                sys.stdout.flush()
                continue
            response = forward(line)
            if response is not None:
                sys.stdout.write(response + "\n")
                sys.stdout.flush()
            continue
        if method == "shutdown":
            response = forward(line)
            if response is not None:
                sys.stdout.write(response + "\n")
                sys.stdout.flush()
            break
        # Unknown methods: pass through.
        response = forward(line)
        if response is not None:
            sys.stdout.write(response + "\n")
            sys.stdout.flush()

    try:
        child.stdin.close()
        child.wait(timeout=5)
    except (BrokenPipeError, subprocess.TimeoutExpired):
        child.kill()
    return 0


def target_from_args(target_arg: str) -> list[str]:
    """Split the --target string into argv (shell-like quoting, no shell)."""
    return shlex.split(target_arg)
