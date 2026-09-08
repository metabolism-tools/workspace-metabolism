import json
import sqlite3
import pytest
from workspace_metabolism.core import slim


def setup(tmp_path, *, legacy=False):
    db = tmp_path / "app.db"
    with sqlite3.connect(db) as con:
        con.execute("create table epochs (epoch_id text primary key, created_at text)")
        con.execute("create table units (epoch_id text, payload text)")
        for key, date in [("old", "2025-01-01"), ("new", "2025-02-01")]:
            con.execute("insert into epochs values (?, ?)", (key, date))
            con.execute("insert into units values (?, ?)", (key, json.dumps({"heavy": [1,2], "evidence": [3,4]})))
    keep = {"table":"epochs", "column":"created_at", "n":1}
    if not legacy:
        keep.update(key_column="epoch_id", row_column="epoch_id")
    policy = {"version":1, "entries":[{"path":"app.db", "grade":"G2", "cleanup":"never", "db_slim":{
        "table":"units", "blob_column":"payload", "strip_keys":["heavy"],
        "protected_keys":["evidence"], "keep_recent":keep, "vacuum_min_gb":999}}]}
    reg = tmp_path / "policy.json"
    reg.write_text(json.dumps(policy))
    return db, reg, policy


def values(db):
    with sqlite3.connect(db) as con:
        return dict(con.execute("select epoch_id,payload from units"))


def test_relational_retention_protects_actual_heavy_new_rows(tmp_path):
    db, reg, _ = setup(tmp_path)
    before = values(db)
    preview = slim(db, reg, tmp_path/"state")
    assert values(db) == before
    assert preview["rows_stripped"] == 1
    report = slim(db, reg, tmp_path/"state", yes=True)
    after = values(db)
    assert "heavy" not in json.loads(after["old"])
    assert after["new"] == before["new"]
    assert report["rows_kept_recent"] == 1
    assert json.loads(after["old"])["evidence"] == [3,4]


@pytest.mark.parametrize("kind", ["missing_row", "orphan", "null_key", "legacy_missing_json", "zero", "partial"])
def test_unresolved_protection_never_partially_writes(tmp_path, kind):
    db, reg, policy = setup(tmp_path, legacy=kind=="legacy_missing_json")
    keep = policy["entries"][0]["db_slim"]["keep_recent"]
    if kind == "missing_row": keep["row_column"] = "absent"
    if kind == "zero": keep["n"] = 0
    if kind == "partial": keep.pop("key_column")
    if kind in {"orphan", "null_key"}:
        with sqlite3.connect(db) as con:
            con.execute("update units set epoch_id=? where epoch_id='new'", ("unknown" if kind=="orphan" else None,))
    reg.write_text(json.dumps(policy))
    before = values(db)
    with pytest.raises(SystemExit): slim(db, reg, tmp_path/"state", yes=True)
    assert values(db) == before


def test_cli_cannot_strip_policy_protected_evidence(tmp_path):
    db, reg, _ = setup(tmp_path)
    before = values(db)
    with pytest.raises(SystemExit, match="protected"):
        slim(db, reg, tmp_path/"state", strip_keys=("evidence",), yes=True)
    assert values(db) == before


def test_planning_transaction_blocks_a_competing_writer(tmp_path, monkeypatch):
    db, reg, _ = setup(tmp_path)
    original = json.loads
    attempts = []
    def observe(blob, *args, **kwargs):
        if isinstance(blob, str) and blob.startswith('{"heavy":') and not attempts:
            with sqlite3.connect(db, timeout=0) as other:
                try:
                    other.execute("update units set payload='{}' where epoch_id='new'")
                except sqlite3.OperationalError as exc:
                    attempts.append("locked" in str(exc))
                else:
                    attempts.append(False)
        return original(blob, *args, **kwargs)
    monkeypatch.setattr(json, "loads", observe)
    slim(db, reg, tmp_path/"state", yes=True)
    assert attempts == [True]
    assert "heavy" in original(values(db)["new"])


def test_legacy_json_references_still_work_when_explicit(tmp_path):
    db, reg, _ = setup(tmp_path, legacy=True)
    with sqlite3.connect(db) as con:
        for key,date in [("old","2025-01-01"),("new","2025-02-01")]:
            con.execute("update units set payload=? where epoch_id=?",(json.dumps({"created_at":date,"heavy":[1]}),key))
    result = slim(db,reg,tmp_path/"state",yes=True)
    assert result["rows_stripped"] == 1
    assert result["rows_kept_recent"] == 1
