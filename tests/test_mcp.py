import json

from workspace_metabolism.mcp_server import handle_message


def _ctx(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    (root / "logs").mkdir()
    reg = tmp_path / "registry.json"
    reg.write_text(
        json.dumps(
            {
                "version": 1,
                "defaults": {},
                "never_clean": [],
                "entries": [
                    {"path": "logs", "grade": "G4", "cleanup": "auto", "retention_days": 30}
                ],
            }
        ),
        encoding="utf-8",
    )
    return {"root": root, "state_dir": tmp_path / "state", "registry_path": reg}


def test_initialize():
    resp = json.loads(handle_message('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}', {}))
    assert resp["result"]["protocolVersion"] == "2024-11-05"
    assert resp["result"]["serverInfo"]["name"] == "workspace-metabolism"


def test_tools_list():
    resp = json.loads(handle_message('{"jsonrpc":"2.0","id":2,"method":"tools/list"}', {}))
    names = {t["name"] for t in resp["result"]["tools"]}
    assert names == {
        "wm_audit",
        "wm_health",
        "wm_explain",
        "wm_verify",
        "wm_clean",
        "wm_govern",
        "wm_init",
        "wm_rollback",
    }


def test_tool_call_health(tmp_path):
    resp = json.loads(
        handle_message(
            '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"wm_health","arguments":{}}}',
            _ctx(tmp_path),
        )
    )
    assert '"score"' in resp["result"]["content"][0]["text"]


def test_tool_call_clean_is_dry_run_by_default(tmp_path):
    resp = json.loads(
        handle_message(
            '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"wm_clean","arguments":{"grades":"G4"}}}',
            _ctx(tmp_path),
        )
    )
    assert "dry-run" in resp["result"]["content"][0]["text"]


def test_tool_call_explain(tmp_path):
    resp = json.loads(
        handle_message(
            '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"wm_explain","arguments":{"path":"logs"}}}',
            _ctx(tmp_path),
        )
    )
    assert '"covered": true' in resp["result"]["content"][0]["text"]


def test_tool_call_govern_denies_write_without_preview(tmp_path):
    ctx = _ctx(tmp_path)
    data = json.loads(ctx["registry_path"].read_text(encoding="utf-8"))
    data["ai_governance"] = {
        "default": "deny",
        "actions": {"write": {"allow": True, "requires_preview": True}},
    }
    ctx["registry_path"].write_text(json.dumps(data), encoding="utf-8")
    resp = json.loads(
        handle_message(
            '{"jsonrpc":"2.0","id":14,"method":"tools/call","params":{"name":"wm_govern","arguments":{"action":"write","paths":["README.md"]}}}',
            ctx,
        )
    )
    text = resp["result"]["content"][0]["text"]
    assert '"allowed": false' in text
    assert "a preview is required" in text


def test_tool_call_unknown_tool():
    resp = json.loads(
        handle_message(
            '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"nope","arguments":{}}}',
            {"root": None, "state_dir": None, "registry_path": None},
        )
    )
    assert resp["result"]["isError"] is True


def test_missing_registry_returns_error(tmp_path):
    ctx = {"root": tmp_path, "state_dir": tmp_path / "state", "registry_path": None}
    resp = json.loads(
        handle_message(
            '{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"wm_health","arguments":{}}}',
            ctx,
        )
    )
    assert "wm init" in resp["result"]["content"][0]["text"]


def test_wm_init_creates_policy_and_enables_audit(tmp_path):
    ctx = {"root": tmp_path, "state_dir": tmp_path / "state", "registry_path": None}
    resp = json.loads(
        handle_message(
            '{"jsonrpc":"2.0","id":9,"method":"tools/call","params":{"name":"wm_init","arguments":{}}}',
            ctx,
        )
    )
    assert "created policy file" in resp["result"]["content"][0]["text"]
    assert (tmp_path / "metabolism.json").exists()
    # Auto-discovery: a subsequent audit works in the same session.
    resp2 = json.loads(
        handle_message(
            '{"jsonrpc":"2.0","id":10,"method":"tools/call","params":{"name":"wm_health","arguments":{}}}',
            ctx,
        )
    )
    assert '"score"' in resp2["result"]["content"][0]["text"]


def test_wm_init_refuses_overwrite_without_force(tmp_path):
    (tmp_path / "metabolism.json").write_text("{}", encoding="utf-8")
    ctx = {"root": tmp_path, "state_dir": tmp_path / "state", "registry_path": None}
    resp = json.loads(
        handle_message(
            '{"jsonrpc":"2.0","id":11,"method":"tools/call","params":{"name":"wm_init","arguments":{}}}',
            ctx,
        )
    )
    assert resp["result"]["isError"] is True
    assert "already exists" in resp["result"]["content"][0]["text"]


def test_wm_rollback_unknown_run_returns_error(tmp_path):
    ctx = {"root": tmp_path, "state_dir": tmp_path / "state", "registry_path": None}
    resp = json.loads(
        handle_message(
            '{"jsonrpc":"2.0","id":12,"method":"tools/call","params":{"name":"wm_rollback","arguments":{"run_id":"clean-00000000-000000-000000"}}}',
            ctx,
        )
    )
    assert resp["result"]["isError"] is True
    assert "run manifest not found" in resp["result"]["content"][0]["text"]


def test_wm_rollback_requires_run_id(tmp_path):
    ctx = {"root": tmp_path, "state_dir": tmp_path / "state", "registry_path": None}
    resp = json.loads(
        handle_message(
            '{"jsonrpc":"2.0","id":13,"method":"tools/call","params":{"name":"wm_rollback","arguments":{}}}',
            ctx,
        )
    )
    assert resp["result"]["isError"] is True
    assert "run_id is required" in resp["result"]["content"][0]["text"]


def test_shutdown():
    resp = json.loads(handle_message('{"jsonrpc":"2.0","id":8,"method":"shutdown"}', {}))
    assert resp["result"] is None
