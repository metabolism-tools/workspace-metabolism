"""Tests for wm gate — the MCP governance proxy."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from workspace_metabolism.core import journal_path
from workspace_metabolism.gate import gate_main


FAKE_TARGET = r'''
import json
import sys

for raw in sys.stdin:
    line = raw.strip()
    if not line:
        continue
    msg = json.loads(line)
    m = msg.get("method")
    rid = msg.get("id")
    if m == "initialize":
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "serverInfo": {"name": "fake", "version": "1.0"}}}) + "\n")
        sys.stdout.flush()
    elif m == "tools/list":
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": {"tools": [
            {"name": "fake_read", "inputSchema": {"type": "object",
             "properties": {"path": {"type": "string"}}}},
            {"name": "fake_write", "inputSchema": {"type": "object",
             "properties": {"path": {"type": "string"}}}},
        ]}}) + "\n")
        sys.stdout.flush()
    elif m == "tools/call":
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": {
            "content": [{"type": "text", "text": "executed"}]}}) + "\n")
        sys.stdout.flush()
    elif m == "shutdown":
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": None}) + "\n")
        sys.stdout.flush()
        break
'''


def _policy(tmp_path: Path) -> Path:
    p = tmp_path / "metabolism.json"
    p.write_text(json.dumps({
        "version": 1,
        "ai_governance": {
            "default": "deny",
            "tool_patterns": {"fake_read": "read", "fake_write": "write"},
            "actions": {
                "read": {"allow": True},
                "write": {"allow": True, "requires_preview": True},
                "execute": {"allow": False},
            },
        },
        "entries": [],
    }), encoding="utf-8")
    return p


def _run_gate(tmp_path: Path, stdin_lines: list[str]) -> list[str]:
    """Run gate_main with fake stdio and return its output lines."""
    target = tmp_path / "fake_target.py"
    target.write_text(FAKE_TARGET, encoding="utf-8")
    stdin = io.StringIO("\n".join(stdin_lines) + "\n")
    stdout = io.StringIO()
    old_in, old_out = sys.stdin, sys.stdout
    sys.stdin, sys.stdout = stdin, stdout
    try:
        gate_main(
            tmp_path / "ws",
            tmp_path / "state",
            _policy(tmp_path),
            [sys.executable, str(target)],
        )
    finally:
        sys.stdin, sys.stdout = old_in, old_out
    return stdout.getvalue().splitlines()


def test_gate_relays_read_blocks_write_without_preview(tmp_path: Path) -> None:
    out = _run_gate(tmp_path, [
        '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}',
        '{"jsonrpc":"2.0","id":2,"method":"tools/list"}',
        '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"fake_read","arguments":{"path":"a.txt"}}}',
        '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"fake_write","arguments":{"path":"b.txt"}}}',
        '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"fake_write","arguments":{"path":"b.txt","preview":true}}}',
        '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"fake_unknown","arguments":{}}}',
        '{"jsonrpc":"2.0","id":7,"method":"shutdown"}',
    ])
    by_id = {json.loads(l)["id"]: json.loads(l) for l in out if l.strip().startswith("{")}
    # initialize and tools/list relayed
    assert by_id[1]["result"]["serverInfo"]["name"] == "fake"
    assert by_id[2]["result"]["tools"][0]["name"] == "fake_read"
    # read allowed -> relayed to target
    assert by_id[3]["result"]["content"][0]["text"] == "executed"
    # write without preview -> blocked by gate, never reaches target
    assert by_id[4]["result"]["isError"] is True
    assert "blocked by workspace policy" in by_id[4]["result"]["content"][0]["text"]
    assert "decision_id=" in by_id[4]["result"]["content"][0]["text"]
    # write with preview -> allowed -> relayed
    assert by_id[5]["result"]["content"][0]["text"] == "executed"
    # unknown tool -> action execute -> denied by default
    assert by_id[6]["result"]["isError"] is True
    # shutdown relayed
    assert by_id[7]["result"] is None

    # journal holds the decisions with decision ids
    entries = [
        json.loads(l) for l in journal_path(tmp_path / "state").read_text(encoding="utf-8").splitlines() if l.strip()
    ]
    governs = [e for e in entries if e["action"] == "govern"]
    assert len(governs) == 4  # read allow, write deny, write preview allow, unknown deny
    # read: allow; write (no preview): deny; write (preview): allow; unknown: deny
    decisions = [g["decision"] for g in governs]
    assert decisions.count("allow") == 2
    assert decisions.count("deny") == 2
    assert all(g.get("decision_id", "").startswith("govern-") for g in governs)
