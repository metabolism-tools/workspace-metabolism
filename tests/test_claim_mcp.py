import io
import json
import subprocess

import pytest

from workspace_metabolism.claim_guard import ClaimRejected
from workspace_metabolism.claim_mcp import ClaimEditor
from workspace_metabolism.mcp_server import handle_message, main


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@pytest.fixture
def editor(tmp_path):
    (tmp_path / "maintenance.md").write_bytes(b"# Maintenance\n\nPending.\n")
    (tmp_path / ".gitignore").write_text(".coordination/\n.wm/\n", encoding="utf-8")
    policy = tmp_path / "metabolism.json"
    policy.write_text(json.dumps({"version": 1, "entries": [], "ai_governance": {
        "default": "deny", "actions": {"write": {"allow": True, "requires_preview": True}}}}))
    git(tmp_path, "init")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "commit.gpgsign", "false")
    hooks = tmp_path / ".git" / "empty-hooks"
    hooks.mkdir()
    git(tmp_path, "config", "core.hooksPath", str(hooks))
    git(tmp_path, "add", "maintenance.md", "metabolism.json", ".gitignore")
    git(tmp_path, "commit", "-m", "Fixture baseline")
    return ClaimEditor(tmp_path, policy, tmp_path / ".wm", "maintenance.md")


def call(editor, name, params=None):
    reply = editor.call(name, {} if params is None else params)
    return json.loads(reply["content"][0]["text"])


def begin(editor):
    return call(editor, "wm_edit_begin", {"task": "Maintain the test record"})


def preview(editor, text="# Maintenance\n\nReviewed.\n"):
    return call(editor, "wm_edit_preview", {"text": text})


def apply(editor, proposal):
    return call(editor, "wm_edit_apply", {"preview_id": proposal["preview_id"]})


def test_full_flow_and_no_credentials(editor):
    assert call(editor, "wm_edit_read")["text"].endswith("Pending.\n")
    registered = begin(editor)
    assert begin(editor) == registered
    proposed = preview(editor)
    assert "Pending." in (editor.root / "maintenance.md").read_text()
    assert proposed["human_approval"] is False
    assert "+Reviewed." in proposed["diff"]
    receipt = apply(editor, proposed)
    assert receipt["after"]["sha256"] == proposed["after_sha256"]
    before = (editor.root / "maintenance.md").stat().st_mtime_ns
    assert apply(editor, proposed)["replayed"] is True
    assert (editor.root / "maintenance.md").stat().st_mtime_ns == before
    with pytest.raises(ClaimRejected, match="delivery"):
        call(editor, "wm_edit_finish")
    git(editor.root, "add", "maintenance.md")
    git(editor.root, "commit", "-m", "Host delivers the document")
    assert call(editor, "wm_edit_finish")["status"] == "done"
    assert editor.claim["session_id"] not in json.dumps([registered, proposed, receipt])
    assert "before" not in receipt
    with pytest.raises(ClaimRejected, match="finished"):
        call(editor, "wm_edit_begin", {"task": "again"})


@pytest.mark.parametrize("name", ["wm_clean", "wm_init", "wm_rollback", "wm_govern", "execute", "delete"])
def test_other_tools_are_not_available(editor, name):
    message = {"id": 1, "method": "tools/call", "params": {"name": name, "arguments": {}}}
    reply = json.loads(handle_message(json.dumps(message), {"claim_editor": editor}))
    assert "unavailable" in reply["error"]["message"]
    assert not editor.backend.path.exists()


def test_catalog_is_restricted(editor):
    result = json.loads(handle_message('{"id":1,"method":"tools/list"}', {"claim_editor": editor}))
    names = {t["name"] for t in result["result"]["tools"]}
    assert names == {"wm_edit_read", "wm_edit_begin", "wm_edit_preview", "wm_edit_apply", "wm_edit_finish"}


@pytest.mark.parametrize("params", [{"path": "other.md"}, {"session_id": "forged"}, [], None])
def test_argument_smuggling_rejected(editor, params):
    msg = {"id": 1, "method": "tools/call", "params": {"name": "wm_edit_read", "arguments": params}}
    assert "error" in json.loads(handle_message(json.dumps(msg), {"claim_editor": editor}))


@pytest.mark.parametrize("name", ["../maintenance.md", "./maintenance.md", "folder/../maintenance.md", ".git/maintenance.md", "src/app.py", "AGENTS.md"])
def test_startup_scope_rejected(editor, name):
    with pytest.raises(ClaimRejected):
        ClaimEditor(editor.root, editor.policy, editor.state_dir, name)


def test_claim_required_and_conflict(editor):
    with pytest.raises(ClaimRejected, match="begin"):
        preview(editor)
    begin(editor)
    other = ClaimEditor(editor.root, editor.policy, editor.state_dir, editor.name)
    with pytest.raises(ClaimRejected, match="occupied"):
        begin(other)
    assert len(editor.backend.load()["claims"]) == 1


def test_preview_bound_to_connection(editor):
    begin(editor)
    with pytest.raises(ClaimRejected, match="unknown preview"):
        apply(editor, {"preview_id": "forged"})
    proposed = preview(editor)
    other = ClaimEditor(editor.root, editor.policy, editor.state_dir, editor.name)
    with pytest.raises(ClaimRejected, match="begin"):
        apply(other, proposed)


def test_external_change_preserved(editor):
    begin(editor)
    proposed = preview(editor)
    (editor.root / editor.name).write_text("External change\n")
    with pytest.raises(ClaimRejected, match="outside"):
        apply(editor, proposed)
    assert (editor.root / editor.name).read_text() == "External change\n"


def test_stale_preview_after_own_write_rejected(editor):
    begin(editor)
    first, second = preview(editor, "First\n"), preview(editor, "Second\n")
    apply(editor, first)
    with pytest.raises(ClaimRejected, match="stale"):
        apply(editor, second)
    assert (editor.root / editor.name).read_text() == "First\n"


def test_policy_rechecked_at_write(editor):
    begin(editor)
    proposed = preview(editor)
    data = json.loads(editor.policy.read_text())
    data["ai_governance"]["actions"]["write"]["allow"] = False
    editor.policy.write_text(json.dumps(data))
    with pytest.raises(ClaimRejected, match="policy"):
        apply(editor, proposed)
    assert "Pending." in (editor.root / editor.name).read_text()


@pytest.mark.parametrize("text", ["", "\0", "   ", "a" * 16385, "\u6c49" * 6000, 123],
                         ids=["empty", "nul", "spaces", "large", "multibyte-large", "integer"])
def test_invalid_replacement(editor, text):
    begin(editor)
    with pytest.raises(ClaimRejected):
        preview(editor, text)


def test_preview_limit(editor):
    begin(editor)
    for _ in range(16):
        preview(editor)
    with pytest.raises(ClaimRejected, match="16 previews"):
        preview(editor)


def test_notification_cannot_begin(editor):
    msg = {"method": "tools/call", "params": {"name": "wm_edit_begin", "arguments": {"task": "task"}}}
    assert "error" in json.loads(handle_message(json.dumps(msg), {"claim_editor": editor}))
    assert not editor.backend.path.exists()


def test_disconnect_retains_unfinished_claim(editor, monkeypatch):
    msg = {"id": 1, "method": "tools/call", "params": {"name": "wm_edit_begin", "arguments": {"task": "task"}}}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(msg) + "\n"))
    output = io.StringIO()
    monkeypatch.setattr("sys.stdout", output)
    assert main(editor.root, editor.state_dir, editor.policy, claim_file=editor.name) == 0
    record = editor.backend.load()["claims"][0]
    assert record["status"] == "active"
    assert record["wm_guard"]["session_id"] not in output.getvalue()
    with pytest.raises(ClaimRejected, match="occupied"):
        begin(editor)


def test_oversized_stdio_request_closes(editor, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("x" * (128 * 1024 + 1)))
    assert main(editor.root, editor.state_dir, editor.policy, claim_file=editor.name) == 2
    assert not editor.backend.path.exists()


def test_approval_rule_cannot_be_satisfied_by_preview(editor):
    data = json.loads(editor.policy.read_text())
    data["ai_governance"]["actions"]["write"]["requires_approval"] = True
    editor.policy.write_text(json.dumps(data))
    begin(editor)
    with pytest.raises(ClaimRejected, match="policy"):
        apply(editor, preview(editor))


def test_expired_connection_cannot_write(editor):
    begin(editor)
    proposed = preview(editor)
    editor.guard.clock = lambda: editor.claim["expires_at"] + 1
    with pytest.raises(ClaimRejected, match="expired"):
        apply(editor, proposed)


def test_missing_policy_rejects_startup(editor):
    with pytest.raises(ClaimRejected, match="policy"):
        ClaimEditor(editor.root, None, editor.state_dir, editor.name)


def test_failed_receipt_keeps_intent_and_blocks_retry(editor, monkeypatch):
    begin(editor)
    proposed = preview(editor)
    original_save = editor.backend.save
    count = 0

    def failing_save(registry):
        nonlocal count
        count += 1
        if count == 2:
            raise OSError("injected receipt save failure")
        original_save(registry)

    monkeypatch.setattr(editor.backend, "save", failing_save)
    with pytest.raises(OSError, match="injected"):
        apply(editor, proposed)
    record = editor.backend.load()["claims"][0]
    assert record["wm_guard"]["pending"] is not None
    with pytest.raises(ClaimRejected, match="recovery_required"):
        apply(editor, proposed)
