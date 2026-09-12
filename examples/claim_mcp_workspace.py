"""Prepare an independent fixture for interactive MCP editing; never edits for the AI."""

import json
from pathlib import Path
import subprocess
import tempfile


def prepare_workspace():
    base = Path(tempfile.mkdtemp(prefix="wm-mcp-edit-"))
    root = base / "workspace"
    root.mkdir()
    (root / "maintenance.md").write_bytes(
        b"# Maintenance Record\n\nStatus: pending an assistant-authored update.\n")
    (root / "other.md").write_bytes(b"Unassigned document. Do not edit.\n")
    (root / ".gitignore").write_bytes(b".coordination/\n")
    (root / "metabolism.json").write_text(json.dumps({
        "version": 1, "entries": [], "ai_governance": {
            "default": "deny", "actions": {"write": {"allow": True, "requires_preview": True}}}
    }), encoding="utf-8")
    hooks = base / "empty-hooks"
    hooks.mkdir()

    def git(*args):
        subprocess.run(["git", "-C", str(root), *args], check=True,
                       capture_output=True, timeout=20)

    git("init")
    git("config", "user.name", "WM MCP Pilot")
    git("config", "user.email", "pilot@example.invalid")
    git("config", "commit.gpgsign", "false")
    git("config", "core.autocrlf", "false")
    git("config", "core.hooksPath", str(hooks))  # Only this newly created fixture.
    git("add", "maintenance.md", "other.md", "metabolism.json", ".gitignore")
    git("commit", "-m", "Independent MCP editing baseline")
    return {"root": str(root), "state_dir": str(base / "state"), "claim_file": "maintenance.md"}


if __name__ == "__main__":
    print(json.dumps(prepare_workspace()))
