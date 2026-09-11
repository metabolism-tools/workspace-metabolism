import json
from pathlib import Path

import pytest

from workspace_metabolism import changes
from workspace_metabolism.cli import main
from workspace_metabolism.core import verify_journal


@pytest.fixture
def case(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "main.py").write_text("answer = 1\n", encoding="utf-8")
    (root / "keep.txt").write_text("keep\n", encoding="utf-8")
    policy = root / "metabolism.json"
    policy.write_text(json.dumps({"version": 1, "entries": [], "ai_governance": {
        "default": "deny", "protected_paths": [],
        "actions": {"write": {"allow": True, "requires_preview": True}}
    }}), encoding="utf-8")
    state = tmp_path / "state"
    prepared = changes.run_change(root, state, policy, "prepare", files=["main.py"],
                                  protected=["keep.txt"], goal="fix answer",
                                  acceptance="answer equals 2; no second pipeline")
    return root, state, policy, prepared


def call(case, command, **kwargs):
    root, state, policy, prepared = case
    return changes.run_change(root, state, policy, command, change_id=prepared["id"], **kwargs)


def proposal(case):
    draft = Path(case[3]["draft"])
    (draft / "main.py").write_text("answer = 2\n", encoding="utf-8")
    return call(case, "review")


def apply(case, review):
    return call(case, "apply", approval=review["digest"], approver="local reviewer",
                acceptance="checked answer == 2 and reviewed structure")


def test_change_roundtrip(case):
    root, state, _, _ = case
    original = (root / "main.py").read_bytes()
    review = proposal(case)
    assert "+answer = 2" in review["diff"]
    assert (root / "main.py").read_bytes() == original
    assert apply(case, review)["status"] == "applied"
    assert (root / "main.py").read_text() == "answer = 2\n"
    with pytest.raises(ValueError, match="unconsumed"):
        apply(case, review)
    assert call(case, "restore")["status"] == "restored"
    assert (root / "main.py").read_bytes() == original
    assert verify_journal(state)["chain_ok"]
    events = [json.loads(line)["action"] for line in (state / "journal.jsonl").read_text().splitlines()]
    assert "change_applied" in events and "change_restored" in events


@pytest.mark.parametrize("change", ["delete_protected", "edit_protected", "add", "delete"])
def test_scope_blocked(case, change):
    draft = Path(case[3]["draft"])
    if change == "delete_protected":
        (draft / "keep.txt").unlink()
    elif change == "edit_protected":
        (draft / "keep.txt").write_text("oops")
    elif change == "delete":
        (draft / "main.py").unlink()
    else:
        (draft / "extra.py").write_text("pass")
    with pytest.raises(ValueError):
        call(case, "review")
    assert (case[0] / "keep.txt").read_text() == "keep\n"


@pytest.mark.parametrize("target", ["original", "draft", "policy"])
def test_stale_approval(case, target):
    review = proposal(case)
    path = {"original": case[0] / "main.py", "draft": Path(case[3]["draft"]) / "main.py",
            "policy": case[2]}[target]
    path.write_text(path.read_text() + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        apply(case, review)


def test_expired(case, monkeypatch):
    review = proposal(case)
    monkeypatch.setattr(changes.time, "time", lambda: review["expires"] + 1)
    with pytest.raises(ValueError, match="expired"):
        apply(case, review)


def test_approval_and_evidence_required(case):
    review = proposal(case)
    with pytest.raises(ValueError, match="digest"):
        call(case, "apply", approval="wrong", approver="me", acceptance="checked")
    with pytest.raises(ValueError, match="evidence"):
        call(case, "apply", approval=review["digest"], approver="me")


def test_policy_denial(case):
    data = json.loads(case[2].read_text())
    data["ai_governance"]["protected_paths"] = ["main.py"]
    case[2].write_text(json.dumps(data))
    # Prepare a new task under the changed policy.
    prepared = changes.run_change(*case[:3], "prepare", files=["main.py"],
                                  goal="fix", acceptance="check")
    updated = (*case[:3], prepared)
    with pytest.raises(ValueError, match="policy denied"):
        apply(updated, proposal(updated))
    assert (case[0] / "main.py").read_text() == "answer = 1\n"


def test_restore_preserves_newer_work(case):
    apply(case, proposal(case))
    (case[0] / "main.py").write_text("newer work\n")
    with pytest.raises(ValueError, match="newer work"):
        call(case, "restore")
    assert (case[0] / "main.py").read_text() == "newer work\n"


def test_partial_failure_is_recoverable(case, monkeypatch):
    prepared = changes.run_change(*case[:3], "prepare", files=["main.py", "keep.txt"],
                                  goal="update both", acceptance="check both")
    case = (*case[:3], prepared)
    draft = Path(prepared["draft"])
    (draft / "main.py").write_text("answer = 2\n")
    (draft / "keep.txt").write_text("updated\n")
    review = call(case, "review")
    replace = changes._replace

    def failing(path, snapshot):
        if path == case[0] / "main.py":
            raise OSError("injected disk failure")
        replace(path, snapshot)

    with monkeypatch.context() as patch:
        patch.setattr(changes, "_replace", failing)
        with pytest.raises(ValueError, match="interrupted"):
            apply(case, review)
    assert (case[0] / "keep.txt").read_text() == "updated\n"
    assert call(case, "restore")["status"] == "restored"
    assert (case[0] / "keep.txt").read_text() == "keep\n"
    assert (case[0] / "main.py").read_text() == "answer = 1\n"


@pytest.mark.parametrize("name", ["../escape", "C:/escape", "a/../main.py", "a\\b", "/absolute"])
def test_bad_paths(case, name):
    with pytest.raises(ValueError):
        changes.run_change(*case[:3], "prepare", files=[name], goal="g", acceptance="a")


def test_state_must_be_separate(case):
    with pytest.raises(ValueError, match="outside"):
        changes.run_change(case[0], case[0] / "state", case[2], "prepare")


def test_cli(case, capsys):
    args = ["--root", str(case[0]), "--state-dir", str(case[1]), "change"]
    proposal(case)
    assert main(args + ["review", case[3]["id"]]) == 0
    review = json.loads(capsys.readouterr().out)
    assert main(args + ["apply", case[3]["id"], "--approve", review["digest"],
                        "--approver", "reviewer", "--acceptance-evidence", "checked"]) == 0
    assert main(args + ["restore", case[3]["id"]]) == 0
    assert main(args + ["review", "../invalid"]) == 2
