import json
import os
from datetime import datetime
from pathlib import Path

import pytest

import workspace_metabolism.core as m


def make_old_dir(root: Path, name: str, days: int = 60) -> Path:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    for i in range(3):
        (d / f"f{i}.json").write_text("x" * 100, encoding="utf-8")
    old = datetime.now().timestamp() - days * 86400
    for f in d.rglob("*"):
        os.utime(f, (old, old))
    os.utime(d, (old, old))
    return d


def write_registry(path: Path, entries: list[dict], never_clean: list[str] | None = None) -> None:
    data = {
        "version": 1,
        "description": "test",
        "defaults": {"recycle_retention_days": 30, "max_item_mb": 2560},
        "never_clean": never_clean or ["keep_g2", "docs"],
        "entries": entries,
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def env(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    state = tmp_path / "state"
    return root, state


def base_registry(tmp_path: Path) -> Path:
    reg = tmp_path / "registry.json"
    write_registry(
        reg,
        [
            {"path": "cache_g4", "grade": "G4", "cleanup": "auto", "retention_days": 30},
            {"path": "keep_g2", "grade": "G2", "cleanup": "never"},
            {"path": "staging_g3", "grade": "G3", "cleanup": "approve", "retention_days": 30},
        ],
    )
    return reg


def test_registry_validation_rejects_bad_grade(tmp_path: Path):
    reg = tmp_path / "r.json"
    write_registry(reg, [{"path": "x", "grade": "G9", "cleanup": "auto", "retention_days": 1}])
    with pytest.raises(SystemExit):
        m.load_registry(reg)


def test_registry_requires_retention_for_cleanable(tmp_path: Path):
    reg = tmp_path / "r.json"
    write_registry(reg, [{"path": "x", "grade": "G4", "cleanup": "auto"}])
    with pytest.raises(SystemExit):
        m.load_registry(reg)


def test_audit_finds_expired_candidates_and_unregistered(env, tmp_path: Path):
    root, state = env
    make_old_dir(root, "cache_g4")
    make_old_dir(root, "keep_g2")
    make_old_dir(root, "new_stuff")
    report, _ = m.audit(root, base_registry(tmp_path), state)
    paths = {c["path"] for c in report["candidates"]}
    assert "cache_g4" in paths
    assert "keep_g2" not in paths
    assert "new_stuff" in report["unregistered"]
    assert "disk" in report


def test_audit_tracks_growth(env, tmp_path: Path):
    root, state = env
    reg = base_registry(tmp_path)
    m.audit(root, reg, state)
    (root / "extra").mkdir()
    (root / "extra" / "big.bin").write_bytes(b"x" * (2 * 1024 * 1024))
    report, _ = m.audit(root, reg, state)
    assert report["growth_mb_since_last_audit"] is not None
    assert report["growth_mb_since_last_audit"] > 0


def test_clean_moves_to_recycle_and_rollback_restores(env, tmp_path: Path):
    root, state = env
    src = make_old_dir(root, "cache_g4")
    content = (src / "f0.json").read_text(encoding="utf-8")
    reg = base_registry(tmp_path)
    m.clean(root, reg, state, {"G4"}, yes=True)
    assert not src.exists()
    runs = sorted((state / "runs").glob("*.json"))
    assert len(runs) == 1
    m.rollback(root, state, runs[0].stem)
    assert src.exists()
    assert (src / "f0.json").read_text(encoding="utf-8") == content


def test_single_file_clean_rollback(env, tmp_path: Path):
    root, state = env
    d = root / "cache_g4"
    d.mkdir()
    target = d / "old.log"
    target.write_text("old", encoding="utf-8")
    old = datetime.now().timestamp() - 40 * 86400
    os.utime(target, (old, old))
    os.utime(d, (old, old))
    reg = base_registry(tmp_path)
    m.clean(root, reg, state, {"G4"}, yes=True)
    assert not target.exists()
    runs = sorted((state / "runs").glob("*.json"))
    m.rollback(root, state, runs[0].stem)
    assert target.read_text(encoding="utf-8") == "old"


def test_clean_never_touches_never_clean(env, tmp_path: Path):
    root, state = env
    make_old_dir(root, "keep_g2")
    reg = base_registry(tmp_path)
    m.clean(root, reg, state, {"G4", "G3"}, yes=True, approve=True, approver="tester")
    assert (root / "keep_g2").exists()


def test_clean_dry_run_moves_nothing(env, tmp_path: Path):
    root, state = env
    src = make_old_dir(root, "cache_g4")
    reg = base_registry(tmp_path)
    m.clean(root, reg, state, {"G4"})
    assert src.exists()
    assert not (state / "recycle").exists()


def test_g3_requires_approve(env, tmp_path: Path):
    root, state = env
    make_old_dir(root, "staging_g3")
    reg = base_registry(tmp_path)
    with pytest.raises(SystemExit):
        m.clean(root, reg, state, {"G3"}, yes=True)


def test_g3_requires_approver(env, tmp_path: Path):
    root, state = env
    make_old_dir(root, "staging_g3")
    reg = base_registry(tmp_path)
    with pytest.raises(SystemExit):
        m.clean(root, reg, state, {"G3"}, yes=True, approve=True)


def test_protected_window_blocks_when_active(env, tmp_path: Path):
    root, state = env
    make_old_dir(root, "staging_g3")
    reg = tmp_path / "registry.json"
    write_registry(
        reg,
        [{"path": "staging_g3", "grade": "G3", "cleanup": "approve", "retention_days": 30, "protected": True}],
    )
    now = datetime(2026, 8, 14, 10, 0)  # Friday
    items = m.plan_items(root, m.load_registry(reg), {"G3"}, state, now=now, window=(0, 1439))
    assert items[0]["reason"] == "inside protected window"


def test_no_window_no_block(env, tmp_path: Path):
    root, state = env
    make_old_dir(root, "staging_g3")
    reg = base_registry(tmp_path)
    items = m.plan_items(root, m.load_registry(reg), {"G3"}, state)
    assert items and not items[0]["reason"]


def test_reference_check_blocks_g3(env, tmp_path: Path):
    root, state = env
    make_old_dir(root, "staging_g3")
    (root / "docs").mkdir()
    (root / "docs" / "notes.md").write_text("see staging_g3 for details", encoding="utf-8")
    reg = base_registry(tmp_path)
    items = m.plan_items(root, m.load_registry(reg), {"G3"}, state)
    assert "referenced" in items[0]["reason"]


def test_journal_chain_and_verify_tamper_detection(env, tmp_path: Path):
    root, state = env
    reg = base_registry(tmp_path)
    m.audit(root, reg, state)
    journal = state / "journal.jsonl"
    assert journal.exists()
    assert m.verify_journal(state)["chain_ok"]
    lines = journal.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[0])
    entry["workspace_size"] = 999999
    lines[0] = json.dumps(entry, ensure_ascii=False)
    journal.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert not m.verify_journal(state)["chain_ok"]


def _age_recycle_batches(state: Path, days: int = 2) -> None:
    old = datetime.now().timestamp() - days * 86400
    for batch in (state / "recycle").iterdir():
        if batch.is_dir():
            os.utime(batch, (old, old))


def test_purge_removes_expired_batches(env, tmp_path: Path):
    root, state = env
    make_old_dir(root, "cache_g4")
    reg = base_registry(tmp_path)
    m.clean(root, reg, state, {"G4"}, yes=True)
    _age_recycle_batches(state)
    m.purge(state, older_than_days=0, yes=True)
    assert not any((state / "recycle").iterdir())


def test_purge_requires_yes(env, tmp_path: Path):
    root, state = env
    make_old_dir(root, "cache_g4")
    reg = base_registry(tmp_path)
    m.clean(root, reg, state, {"G4"}, yes=True)
    _age_recycle_batches(state)
    m.purge(state, older_than_days=0)
    assert any((state / "recycle").iterdir())


def test_dupe_scan(env, tmp_path: Path):
    root, state = env
    reg = tmp_path / "registry.json"
    write_registry(
        reg,
        [{"path": "tmp", "grade": "G4", "cleanup": "auto", "retention_days": 30, "scope": "files_only"}],
        never_clean=["docs"],
    )
    for area in ("tmp", "cache"):
        (root / area).mkdir(parents=True, exist_ok=True)
        (root / area / "same.bin").write_bytes(b"1234")
    data = json.loads(reg.read_text(encoding="utf-8"))
    data["defaults"]["dupe_scan_dirs"] = ["tmp", "cache"]
    reg.write_text(json.dumps(data), encoding="utf-8")
    report, _ = m.audit(root, reg, state, dupes=True)
    assert any("same.bin" in key for key, _ in report["dup_hits"])


def test_default_state_dir_outside_root(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    sd = m.default_state_dir()
    assert str(sd).startswith(str(tmp_path / "appdata"))
    assert sd.name == "workspace-metabolism"
