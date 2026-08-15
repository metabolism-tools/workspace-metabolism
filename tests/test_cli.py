import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from workspace_metabolism.cli import main


def _make_workspace(root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (root / "logs").mkdir()
    for i in range(2):
        p = root / "logs" / f"app{i}.log"
        p.write_text("x" * 200, encoding="utf-8")
        old = datetime.now().timestamp() - 40 * 86400
        os.utime(p, (old, old))
    os.utime(root / "logs", (old, old))


def _registry(path: Path) -> Path:
    data = {
        "version": 1,
        "description": "test",
        "defaults": {"recycle_retention_days": 30, "max_item_mb": 2560},
        "never_clean": ["src", "docs"],
        "entries": [
            {"path": "src", "grade": "G2", "cleanup": "never"},
            {"path": "logs", "grade": "G4", "cleanup": "auto", "retention_days": 30},
        ],
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_cli_status_and_audit(tmp_path: Path, capsys):
    root = tmp_path / "ws"
    root.mkdir()
    _make_workspace(root)
    reg = _registry(tmp_path / "registry.json")
    state = tmp_path / "state"
    assert main(["--root", str(root), "--registry", str(reg), "--state-dir", str(state), "status"]) == 0
    assert "workspace:" in capsys.readouterr().out
    assert main(["--root", str(root), "--registry", str(reg), "--state-dir", str(state), "audit"]) == 0
    out = capsys.readouterr().out
    assert "audit done" in out
    assert (state / "journal.jsonl").exists()


def test_cli_audit_json(tmp_path: Path, capsys):
    root = tmp_path / "ws"
    root.mkdir()
    _make_workspace(root)
    reg = _registry(tmp_path / "registry.json")
    state = tmp_path / "state"
    assert main(["--root", str(root), "--registry", str(reg), "--state-dir", str(state), "audit", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert "candidates" in data
    assert data["workspace"]["files"] > 0


def test_cli_clean_dry_run_and_verify(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    _make_workspace(root)
    reg = _registry(tmp_path / "registry.json")
    state = tmp_path / "state"
    assert main(["--root", str(root), "--registry", str(reg), "--state-dir", str(state), "audit"]) == 0
    assert main(["--root", str(root), "--registry", str(reg), "--state-dir", str(state), "clean", "--grades", "G4"]) == 0
    assert (root / "logs").exists()  # dry-run: nothing moved
    assert main(["--root", str(root), "--registry", str(reg), "--state-dir", str(state), "verify"]) == 0


def test_cli_clean_execute_and_rollback(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    _make_workspace(root)
    reg = _registry(tmp_path / "registry.json")
    state = tmp_path / "state"
    assert main(["--root", str(root), "--registry", str(reg), "--state-dir", str(state), "clean", "--grades", "G4", "--yes"]) == 0
    assert not (root / "logs").exists()
    runs = sorted((state / "runs").glob("clean-*.json"))
    assert len(runs) == 1
    run_id = runs[0].stem
    assert main(["--root", str(root), "--state-dir", str(state), "rollback", run_id]) == 0
    assert (root / "logs").exists()
    assert (root / "logs" / "app0.log").exists()


def test_cli_purge_end_to_end(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    _make_workspace(root)
    reg = _registry(tmp_path / "registry.json")
    state = tmp_path / "state"
    assert main(["--root", str(root), "--registry", str(reg), "--state-dir", str(state), "clean", "--grades", "G4", "--yes"]) == 0
    old = datetime.now().timestamp() - 2 * 86400
    for batch in (state / "recycle").iterdir():
        os.utime(batch, (old, old))
    assert main(["--root", str(root), "--state-dir", str(state), "purge", "--older-than", "0", "--yes"]) == 0
    assert not any((state / "recycle").iterdir())


def test_cli_protected_window_flag(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    _make_workspace(root)
    reg = _registry(tmp_path / "registry.json")
    state = tmp_path / "state"
    # Invalid window spec must fail fast
    with pytest.raises(SystemExit):
        main(["--root", str(root), "--registry", str(reg), "--state-dir", str(state), "--protected-window", "bad", "status"])


def test_cli_requires_registry(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    with pytest.raises(SystemExit):
        main(["--root", str(root), "--state-dir", str(tmp_path / "state"), "status"])
