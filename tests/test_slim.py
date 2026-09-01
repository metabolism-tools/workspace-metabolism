"""Tests for the slim (in-place SQLite trimming) capability."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workspace_metabolism.core import db_slim_policy, slim  # noqa: E402
from workspace_metabolism.core import journal_path  # noqa: E402


def _make_db(path: Path, n_old: int = 4, n_new: int = 2) -> None:
    con = sqlite3.connect(str(path))
    con.execute("create table epochs (epoch_id text, created_at text)")
    con.execute("create table work_units (work_unit_id text, epoch_id text, payload_json text)")
    for i in range(n_old):
        con.execute("insert into epochs values (?, ?)", (f"e{i}", f"2026-08-0{i + 1}T00:00:00"))
        big = json.dumps({"metrics": {"ic": 0.1}, "factor_observations": [{"date": "2026-08-01", "value": i} for _ in range(50)]})
        con.execute("insert into work_units values (?, ?, ?)", (f"u{i}", f"e{i}", big))
    for i in range(n_new):
        con.execute("insert into epochs values (?, ?)", (f"en{i}", f"2026-08-3{i + 1}T00:00:00"))
        small = json.dumps({"metrics": {"ic": 0.2}})
        con.execute("insert into work_units values (?, ?, ?)", (f"un{i}", f"en{i}", small))
    con.commit()
    con.close()


def _policy(tmp_path: Path) -> Path:
    p = tmp_path / "metabolism.json"
    p.write_text(json.dumps({
        "version": 1,
        "entries": [{
            "path": "data/app.db", "category": "C5", "grade": "G2", "cleanup": "never",
            "db_slim": {
                "table": "work_units",
                "blob_column": "payload_json",
                "strip_keys": ["factor_observations"],
                "keep_recent": {"table": "epochs", "column": "created_at", "n": 2},
                "vacuum_min_gb": 0.0,
            },
        }],
    }), encoding="utf-8")
    return p


def test_slim_dry_run_reports_and_keeps_recent(tmp_path: Path) -> None:
    db = tmp_path / "data" / "app.db"
    db.parent.mkdir(parents=True)
    _make_db(db, n_old=4, n_new=2)
    report = slim(db, _policy(tmp_path), tmp_path / "state", yes=False)
    assert report["status"] == "dry_run"
    assert report["rows_scanned"] == 6
    assert report["rows_stripped"] == 4  # only old epochs; newest 2 kept
    assert report["reclaimed_bytes"] > 0
    # dry-run must not change anything
    con = sqlite3.connect(str(db))
    blob = con.execute("select payload_json from work_units where work_unit_id='u0'").fetchone()[0]
    con.close()
    assert "factor_observations" in blob
    # journaled
    j = json.loads(journal_path(tmp_path / "state").read_text(encoding="utf-8").splitlines()[-1])
    assert j["action"] == "slim" and j["status"] == "dry_run"


def test_slim_execute_strips_and_journals(tmp_path: Path) -> None:
    db = tmp_path / "data" / "app.db"
    db.parent.mkdir(parents=True)
    _make_db(db, n_old=4, n_new=2)
    report = slim(db, _policy(tmp_path), tmp_path / "state", yes=True)
    assert report["status"] == "ok"
    assert report["rows_stripped"] == 4
    assert report["vacuum_done"] is True
    con = sqlite3.connect(str(db))
    old_blob = json.loads(con.execute("select payload_json from work_units where work_unit_id='u0'").fetchone()[0])
    new_blob = json.loads(con.execute("select payload_json from work_units where work_unit_id='un0'").fetchone()[0])
    con.close()
    assert "factor_observations" not in old_blob
    assert "factor_observations" not in new_blob  # new rows have no such key anyway
    assert old_blob["metrics"]["ic"] == 0.1
    j = json.loads(journal_path(tmp_path / "state").read_text(encoding="utf-8").splitlines()[-1])
    assert j["action"] == "slim" and j["status"] == "ok" and j["rows_stripped"] == 4


def test_slim_policy_lookup(tmp_path: Path) -> None:
    reg = _policy(tmp_path)
    import json as _json
    policy = db_slim_policy(_json.loads(reg.read_text(encoding="utf-8")), Path("/x/data/app.db"))
    assert policy["table"] == "work_units"
    assert policy["blob_column"] == "payload_json"
    assert policy["strip_keys"] == ["factor_observations"]
    assert policy["keep_recent"]["n"] == 2


def test_slim_policy_generic_entry_does_not_shadow_specific(tmp_path: Path) -> None:
    """A generic `data` entry must not shadow the specific `data/app.db` entry."""
    reg = tmp_path / "metabolism.json"
    reg.write_text(json.dumps({
        "version": 1,
        "entries": [
            {"path": "data", "grade": "G2", "cleanup": "never"},
            {"path": "data/app.db", "grade": "G2", "cleanup": "never",
             "db_slim": {"table": "sessions", "blob_column": "payload_json",
                         "strip_keys": ["factor_observations"]}},
        ],
    }), encoding="utf-8")
    import json as _json
    policy = db_slim_policy(_json.loads(reg.read_text(encoding="utf-8")), Path("/ws/data/app.db"))
    assert policy["table"] == "sessions", policy
    # 无 db_slim 的泛条目不应误配给其他库
    policy2 = db_slim_policy(_json.loads(reg.read_text(encoding="utf-8")), Path("/ws/data/other.db"))
    assert policy2["table"] is None


def test_slim_policy_directory_entry_matches_db_inside(tmp_path: Path) -> None:
    """A directory entry (data/research/work_ledger) must match a DB inside it."""
    reg = tmp_path / "metabolism.json"
    reg.write_text(json.dumps({
        "version": 1,
        "entries": [
            {"path": "data", "grade": "G2", "cleanup": "never"},
            {"path": "data/research/work_ledger", "grade": "G2", "cleanup": "never",
             "db_slim": {"table": "research_work_unit", "blob_column": "checkpoint_json",
                         "strip_keys": ["ic_by_session"]}},
        ],
    }), encoding="utf-8")
    import json as _json
    reg_data = _json.loads(reg.read_text(encoding="utf-8"))
    db = Path("/opt/dongzhu/quant_v10/data/research/work_ledger/marathon.db")
    policy = db_slim_policy(reg_data, db)
    assert policy["table"] == "research_work_unit", policy
    assert policy["blob_column"] == "checkpoint_json"
    assert policy["strip_keys"] == ["ic_by_session"]


def test_slim_requires_table_and_keys(tmp_path: Path) -> None:
    db = tmp_path / "app.db"
    _make_db(db)
    with pytest.raises(SystemExit):
        slim(db, None, tmp_path / "state", yes=False)


def test_slim_db_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="database not found"):
        slim(tmp_path / "nope.db", None, tmp_path / "state", yes=False)


def test_slim_unknown_blob_column_raises(tmp_path: Path) -> None:
    db = tmp_path / "app.db"
    _make_db(db)
    reg = tmp_path / "metabolism.json"
    reg.write_text(json.dumps({"version": 1, "entries": [{
        "path": "app.db", "grade": "G2", "cleanup": "never",
        "db_slim": {"table": "work_units", "blob_column": "no_such_col", "strip_keys": ["x"]},
    }]}), encoding="utf-8")
    with pytest.raises(SystemExit, match="not in table"):
        slim(db, reg, tmp_path / "state", yes=False)


def test_slim_unknown_keep_column_raises(tmp_path: Path) -> None:
    db = tmp_path / "app.db"
    _make_db(db)
    reg = tmp_path / "metabolism.json"
    reg.write_text(json.dumps({"version": 1, "entries": [{
        "path": "app.db", "grade": "G2", "cleanup": "never",
        "db_slim": {"table": "work_units", "blob_column": "payload_json",
                    "strip_keys": ["factor_observations"],
                    "keep_recent": {"table": "epochs", "column": "no_such", "n": 2}},
    }]}), encoding="utf-8")
    with pytest.raises(SystemExit, match="not in keep table"):
        slim(db, reg, tmp_path / "state", yes=False)


def test_slim_invalid_identifier_raises(tmp_path: Path) -> None:
    db = tmp_path / "app.db"
    _make_db(db)
    with pytest.raises(SystemExit, match="invalid identifier"):
        slim(db, None, tmp_path / "state", yes=False, table="bad;name", blob_column="payload_json", strip_keys=("x",))


def test_slim_skips_corrupt_and_missing_key_blobs(tmp_path: Path) -> None:
    """Invalid JSON / non-dict blobs and blobs without the strip key must not crash or change."""
    db = tmp_path / "app.db"
    con = sqlite3.connect(str(db))
    con.execute("create table t (payload_json text)")
    con.execute("insert into t values (?)", ("not json at all",))
    con.execute("insert into t values (?)", (json.dumps(["list", "not dict"]),))
    con.execute("insert into t values (?)", (json.dumps({"a": 1}),))  # no strip key
    con.commit()
    con.close()
    reg = tmp_path / "metabolism.json"
    reg.write_text(json.dumps({"version": 1, "entries": [{
        "path": "app.db", "grade": "G2", "cleanup": "never",
        "db_slim": {"table": "t", "blob_column": "payload_json", "strip_keys": ["factor_observations"]},
    }]}), encoding="utf-8")
    report = slim(db, reg, tmp_path / "state", yes=True)
    assert report["status"] == "ok"
    assert report["rows_scanned"] == 3
    assert report["rows_stripped"] == 0  # nothing had the key; invalid blobs skipped
    con = sqlite3.connect(str(db))
    assert con.execute("select count(*) from t").fetchone()[0] == 3
    con.close()
