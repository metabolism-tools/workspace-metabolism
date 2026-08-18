import json
import os
import shutil
import subprocess
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


def test_registry_missing_file_raises(tmp_path: Path):
    with pytest.raises(SystemExit):
        m.load_registry(tmp_path / "nope.json")


def test_registry_rejects_invalid_cleanup(tmp_path: Path):
    reg = tmp_path / "r.json"
    write_registry(reg, [{"path": "x", "grade": "G4", "cleanup": "sometimes", "retention_days": 1}])
    with pytest.raises(SystemExit):
        m.load_registry(reg)


def test_registry_rejects_missing_entries(tmp_path: Path):
    reg = tmp_path / "r.json"
    reg.write_text(json.dumps({"version": 1, "defaults": {}}), encoding="utf-8")
    with pytest.raises(SystemExit):
        m.load_registry(reg)


def test_registry_rejects_entry_without_path(tmp_path: Path):
    reg = tmp_path / "r.json"
    write_registry(reg, [{"grade": "G4", "cleanup": "auto", "retention_days": 1}])
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


def test_audit_summary_includes_journal_and_recycle(env, tmp_path: Path):
    root, state = env
    make_old_dir(root, "cache_g4")
    reg = base_registry(tmp_path)
    report, _ = m.audit(root, reg, state)
    s = report["summary"]
    assert s["journal_entries"] >= 1
    assert s["journal_chain_ok"] is True
    assert s["candidates"] >= 1
    assert s["recycle_files"] == 0
    m.clean(root, reg, state, {"G4"}, yes=True)
    report2, _ = m.audit(root, reg, state)
    assert report2["summary"]["recycle_files"] > 0


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


def test_clean_skips_oversized_item(env, tmp_path: Path):
    root, state = env
    make_old_dir(root, "cache_g4")
    reg = tmp_path / "registry.json"
    write_registry(
        reg,
        [{"path": "cache_g4", "grade": "G4", "cleanup": "auto", "retention_days": 30}],
        never_clean=["docs"],
    )
    data = json.loads(reg.read_text(encoding="utf-8"))
    data["defaults"]["max_item_mb"] = 0  # anything > 0 MB is blocked
    reg.write_text(json.dumps(data), encoding="utf-8")
    items = m.plan_items(root, m.load_registry(reg), {"G4"}, state)
    assert "exceeds single-item limit" in items[0]["reason"]
    assert (root / "cache_g4").exists()


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


def test_glob_nested_pycache_candidate(env, tmp_path: Path):
    root, state = env
    d = root / "src" / "sub" / "__pycache__"
    d.mkdir(parents=True)
    (d / "mod.cpython-312.pyc").write_bytes(b"x" * 100)
    old = datetime.now().timestamp() - 40 * 86400
    for f in d.rglob("*"):
        os.utime(f, (old, old))
    os.utime(d, (old, old))
    assert d.exists()
    reg = tmp_path / "registry.json"
    write_registry(
        reg,
        [{"path": "**/__pycache__", "grade": "G4", "cleanup": "auto", "retention_days": 30}],
        never_clean=["src", "docs"],
    )
    report, _ = m.audit(root, reg, state)
    paths = {c["path"] for c in report["candidates"]}
    assert "src/sub/__pycache__" in paths


def test_files_only_scope(env, tmp_path: Path):
    root, state = env
    tmp = root / "tmp"
    tmp.mkdir()
    (tmp / "a.log").write_text("x", encoding="utf-8")
    (tmp / "sub").mkdir()
    (tmp / "sub" / "b.log").write_text("y", encoding="utf-8")
    old = datetime.now().timestamp() - 40 * 86400
    for f in tmp.rglob("*"):
        os.utime(f, (old, old))
    os.utime(tmp, (old, old))
    reg = tmp_path / "registry.json"
    write_registry(
        reg,
        [{"path": "tmp", "grade": "G4", "cleanup": "auto", "retention_days": 30, "scope": "files_only"}],
        never_clean=["docs"],
    )
    report, _ = m.audit(root, reg, state)
    paths = {c["path"] for c in report["candidates"]}
    assert "tmp/a.log" in paths
    assert "tmp/sub/b.log" not in paths


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


def test_verify_missing_journal_raises(env):
    _, state = env
    with pytest.raises(SystemExit):
        m.verify_journal(state)


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


def test_rollback_refuses_when_destination_exists(env, tmp_path: Path):
    root, state = env
    make_old_dir(root, "cache_g4")
    reg = base_registry(tmp_path)
    m.clean(root, reg, state, {"G4"}, yes=True)
    runs = sorted((state / "runs").glob("clean-*.json"))
    run_id = runs[0].stem
    (root / "cache_g4").mkdir()
    (root / "cache_g4" / "f0.json").write_text("new content", encoding="utf-8")
    m.rollback(root, state, run_id)
    assert (root / "cache_g4" / "f0.json").read_text(encoding="utf-8") == "new content"
    assert (state / "recycle" / run_id / "cache_g4").exists()


def test_rollback_refuses_hash_mismatch(env, tmp_path: Path):
    root, state = env
    make_old_dir(root, "cache_g4")
    reg = base_registry(tmp_path)
    m.clean(root, reg, state, {"G4"}, yes=True)
    runs = sorted((state / "runs").glob("clean-*.json"))
    run_id = runs[0].stem
    recycled_file = state / "recycle" / run_id / "cache_g4" / "f0.json"
    recycled_file.write_text("tampered", encoding="utf-8")
    m.rollback(root, state, run_id)
    assert not (root / "cache_g4").exists()
    assert recycled_file.exists()


def test_size_only_integrity_for_large_items(env, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(m, "MAX_HASH_MB", 0)  # force the size-only branch
    root, state = env
    make_old_dir(root, "cache_g4")
    reg = base_registry(tmp_path)
    m.clean(root, reg, state, {"G4"}, yes=True)
    runs = sorted((state / "runs").glob("clean-*.json"))
    manifest = json.loads(runs[0].read_text(encoding="utf-8"))
    assert manifest["items"][0]["integrity"] == "size_only"
    m.rollback(root, state, runs[0].stem)
    assert (root / "cache_g4").exists()


def test_clean_run_ids_unique_within_same_second(env, tmp_path: Path):
    """Two rapid cleans must not overwrite the same run manifest."""
    root, state = env
    make_old_dir(root, "cache_g4")
    reg = base_registry(tmp_path)
    m.clean(root, reg, state, {"G4"}, yes=True)
    make_old_dir(root, "cache_g4")
    m.clean(root, reg, state, {"G4"}, yes=True)
    runs = sorted((state / "runs").glob("clean-*.json"))
    assert len(runs) == 2
    assert runs[0].stem != runs[1].stem
    for run in runs:
        assert (state / "recycle" / run.stem / "cache_g4").exists()


def test_audit_run_ids_unique_within_same_second(env, tmp_path: Path):
    """Two rapid audits must not overwrite the same run report."""
    root, state = env
    reg = base_registry(tmp_path)
    m.audit(root, reg, state)
    m.audit(root, reg, state)
    runs = sorted((state / "runs").glob("audit-*.json"))
    assert len(runs) == 2
    assert runs[0].stem != runs[1].stem


def test_init_policy_scaffolds_standard_file(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    for name in ("src", "docs", "logs", "tmp", "cache", "archive"):
        (root / name).mkdir()
    path = m.init_policy(root, root / "metabolism.json")
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert "metabolism.json" in data["never_clean"]
    paths = {e["path"] for e in data["entries"]}
    assert {"src", "docs", "logs", "tmp", "cache", "archive", "**/__pycache__"} <= paths
    logs = next(e for e in data["entries"] if e["path"] == "logs")
    assert logs["grade"] == "G4" and logs["retention_days"] == 30
    archive = next(e for e in data["entries"] if e["path"] == "archive")
    assert archive["grade"] == "G3" and archive["cleanup"] == "approve"


def test_init_policy_refuses_overwrite(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    target = root / "metabolism.json"
    target.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit):
        m.init_policy(root, target)
    m.init_policy(root, target, force=True)


def test_health_score_formula():
    healthy = {
        "summary": {
            "files": 5,
            "candidates": 0,
            "unregistered": 0,
            "disk_alert": False,
            "recycle_files": 3,
            "journal_chain_ok": True,
        }
    }
    hs = m.health_score(healthy)
    assert hs["score"] == 100
    assert hs["grade"] == "A"
    rotten = {
        "summary": {
            "files": 10,
            "candidates": 10,
            "unregistered": 5,
            "disk_alert": True,
            "recycle_files": 0,
            "journal_chain_ok": False,
        }
    }
    hs2 = m.health_score(rotten)
    assert hs2["score"] == 10
    assert hs2["grade"] == "D"


def test_explain_covered_candidate(env, tmp_path: Path):
    root, state = env
    make_old_dir(root, "cache_g4")
    reg = base_registry(tmp_path)
    info = m.explain(root, reg, state, "cache_g4")
    assert info["covered"] is True
    assert info["managed"] is True
    assert info["grade"] == "G4"
    assert info["candidate"] is True
    assert info["age_days"] > 30


def test_explain_uncovered(env, tmp_path: Path):
    root, state = env
    (root / "misc").mkdir()
    (root / "misc" / "f.txt").write_text("x", encoding="utf-8")
    reg = base_registry(tmp_path)
    info = m.explain(root, reg, state, "misc")
    assert info["covered"] is False
    assert info["managed"] is False


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


def test_dupe_scan_off_by_default(env, tmp_path: Path):
    root, state = env
    for area in ("tmp", "cache"):
        (root / area).mkdir(parents=True, exist_ok=True)
        (root / area / "same.bin").write_bytes(b"1234")
    reg = tmp_path / "registry.json"
    write_registry(
        reg,
        [{"path": "tmp", "grade": "G4", "cleanup": "auto", "retention_days": 30, "scope": "files_only"}],
        never_clean=["docs"],
    )
    data = json.loads(reg.read_text(encoding="utf-8"))
    data["defaults"]["dupe_scan_dirs"] = ["tmp", "cache"]
    reg.write_text(json.dumps(data), encoding="utf-8")
    report, _ = m.audit(root, reg, state)
    assert report["dup_hits"] == []


def test_remote_authoritative_marker(env, tmp_path: Path):
    root, state = env
    make_old_dir(root, "staging_g3")
    reg = tmp_path / "registry.json"
    write_registry(
        reg,
        [{"path": "staging_g3", "grade": "G3", "cleanup": "approve", "retention_days": 30, "remote_authoritative": True}],
    )
    report, _ = m.audit(root, reg, state)
    assert report["candidates"][0]["remote_authoritative"] is True
    rendered = m.render_report(report, root)
    assert "remote authoritative" in rendered


def test_unregistered_excludes_never_clean_and_git(env, tmp_path: Path):
    root, state = env
    (root / ".git").mkdir()
    (root / "docs").mkdir()
    (root / "unregistered_dir").mkdir()
    reg = base_registry(tmp_path)
    report, _ = m.audit(root, reg, state)
    assert "unregistered_dir" in report["unregistered"]
    assert ".git" not in report["unregistered"]
    assert "docs" not in report["unregistered"]


def test_protected_window_skips_weekend(env, tmp_path: Path):
    root, state = env
    make_old_dir(root, "staging_g3")
    reg = tmp_path / "registry.json"
    write_registry(
        reg,
        [{"path": "staging_g3", "grade": "G3", "cleanup": "approve", "retention_days": 30, "protected": True}],
    )
    saturday = datetime(2026, 8, 15, 10, 0)
    items = m.plan_items(root, m.load_registry(reg), {"G3"}, state, now=saturday, window=(0, 1439))
    assert not items[0]["reason"]


def test_parse_window():
    assert m.parse_window("09:25-15:00") == (565, 900)
    assert m.parse_window(None) is None
    with pytest.raises(SystemExit):
        m.parse_window("not-a-window")


def test_default_state_dir_windows(tmp_path: Path):
    s = m._default_state_dir_str("nt", {"LOCALAPPDATA": str(tmp_path / "appdata")})
    assert s.startswith(str(tmp_path / "appdata"))
    assert s.endswith("workspace-metabolism")


def test_default_state_dir_posix_xdg(tmp_path: Path):
    s = m._default_state_dir_str("posix", {"XDG_CACHE_HOME": str(tmp_path / "xdg")})
    assert s.startswith(str(tmp_path / "xdg"))
    assert s.endswith("workspace-metabolism")


def test_default_state_dir_falls_back_to_home(tmp_path: Path):
    home = str(tmp_path / "home")
    s = m._default_state_dir_str("posix", {})
    assert s.endswith("workspace-metabolism")
    assert home not in s  # real home is used, not the fake one; just sanity-check shape


# ---------------------------------------------------------------------------
# sensitive files (secrets/keys/credentials)
# ---------------------------------------------------------------------------


def test_registry_rejects_sensitive_g4(tmp_path: Path):
    reg = tmp_path / "r.json"
    write_registry(reg, [{"path": ".env", "grade": "G4", "cleanup": "auto", "retention_days": 1}])
    with pytest.raises(SystemExit, match="sensitive"):
        m.load_registry(reg)


def test_registry_allows_sensitive_as_g1(tmp_path: Path):
    reg = tmp_path / "r.json"
    write_registry(reg, [{"path": ".env", "grade": "G1", "cleanup": "never"}])
    assert m.load_registry(reg)["entries"][0]["grade"] == "G1"


def test_is_sensitive_path_matches_names():
    assert m.is_sensitive_path(".env")
    assert m.is_sensitive_path("sub/.env.local")
    assert m.is_sensitive_path("creds/aws-credentials.json")
    assert m.is_sensitive_path("logs/token.txt")
    assert not m.is_sensitive_path("src/main.py")
    assert not m.is_sensitive_path("docs/notes.md")


def test_audit_reports_sensitive_files(env, tmp_path: Path):
    root, state = env
    (root / ".env").write_text("TOKEN=secret", encoding="utf-8")
    logs = root / "logs"
    logs.mkdir()
    (logs / "token.txt").write_text("x", encoding="utf-8")
    reg = base_registry(tmp_path)
    report, _ = m.audit(root, reg, state)
    paths = {s["path"] for s in report["sensitive"]}
    assert ".env" in paths
    assert "logs/token.txt" in paths
    assert report["summary"]["sensitive"] >= 2
    rendered = m.render_report(report, root)
    assert "## Sensitive files" in rendered
    assert "`.env`" in rendered


def test_clean_blocks_candidate_with_sensitive_files(env, tmp_path: Path):
    root, state = env
    src = make_old_dir(root, "cache_g4")
    sensitive = src / "token.txt"
    sensitive.write_text("x", encoding="utf-8")
    old = datetime.now().timestamp() - 40 * 86400
    os.utime(sensitive, (old, old))
    os.utime(src, (old, old))
    reg = base_registry(tmp_path)
    items = m.plan_items(root, m.load_registry(reg), {"G4"}, state)
    assert items and items[0]["reason"] == "contains sensitive files"
    m.clean(root, reg, state, {"G4"}, yes=True)
    assert src.exists()


def test_init_policy_never_clean_includes_sensitive(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    path = m.init_policy(root, root / "metabolism.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert ".env" in data["never_clean"]
    assert "*.pem" in data["never_clean"]


# ---------------------------------------------------------------------------
# git-aware classification (tracked files are controlled by git)
# ---------------------------------------------------------------------------


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(
        [
            "git", "-C", str(root),
            "-c", "user.email=wm-test@example.com", "-c", "user.name=wm-test",
            "commit", "-qm", "init",
        ],
        check=True,
    )


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_git_tracked_files_lists_repo_content(env, tmp_path: Path):
    root, state = env
    (root / "tracked.py").write_text("x = 1", encoding="utf-8")
    _git_init(root)
    tracked = m.git_tracked_files(root)
    assert tracked is not None
    assert "tracked.py" in tracked


def test_git_tracked_files_returns_none_without_git(env):
    root, _ = env
    assert m.git_tracked_files(root) is None


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_audit_git_aware_unregistered_skips_tracked(env, tmp_path: Path):
    root, state = env
    (root / "tracked.py").write_text("x = 1", encoding="utf-8")
    (root / "untracked_dir").mkdir()
    _git_init(root)
    (root / "untracked_dir" / "new.txt").write_text("y", encoding="utf-8")
    reg = base_registry(tmp_path)
    report, _ = m.audit(root, reg, state)
    assert report["git"]["repo"] is True
    assert report["git"]["tracked_files"] >= 1
    assert "tracked.py" not in report["unregistered"]
    assert "untracked_dir" in report["unregistered"]


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_clean_blocks_candidate_with_git_tracked_files(env, tmp_path: Path):
    root, state = env
    make_old_dir(root, "cache_g4")
    _git_init(root)
    reg = base_registry(tmp_path)
    items = m.plan_items(root, m.load_registry(reg), {"G4"}, state)
    assert items and items[0]["reason"] == "contains git-tracked files"
    m.clean(root, reg, state, {"G4"}, yes=True)
    assert (root / "cache_g4").exists()
