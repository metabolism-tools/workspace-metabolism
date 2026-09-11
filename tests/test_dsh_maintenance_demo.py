import importlib.util
from pathlib import Path

import pytest


EXAMPLE = Path(__file__).resolve().parents[1] / "plugins/dsh-metabolic-maintenance/examples/maintenance_cycle.py"
spec = importlib.util.spec_from_file_location("dsh_maintenance_example", EXAMPLE)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


@pytest.mark.parametrize("scenario", ["normal", "fault_injection", "missing_consumer"])
def test_demo_checks_actual_consumer_and_recovers_only_the_failed_fixture(tmp_path, scenario):
    base = tmp_path / scenario
    result = demo.run_scenario(base, scenario)
    assert result["candidate_count"] == 1
    assert result["llm_executed"] is False
    assert result["supervision_minutes"] is None
    assert (base / "evidence.json").is_file()
    assert (base / "workspace/inputs/values.json").is_file()
    calls = [entry["request"]["params"] for entry in result["wm_calls"]]
    if scenario == "missing_consumer":
        assert result["outcome"] == "held_missing_consumer"
        assert result["after"] is None
        assert not any(call["arguments"].get("execute") for call in calls)
        assert (base / "workspace/scratch/old-report.json").is_file()
    elif scenario == "fault_injection":
        assert result["outcome"] == "fault_recovered_consumer_verified"
        assert result["after"]["accepted"] is False
        assert result["recovery"]["total"] == 18
        assert (base / "workspace/scratch/old-report.json").is_file()
    else:
        assert result["outcome"] == "maintained_consumer_verified"
        assert result["after"]["total"] == result["before"]["total"] == 18
        assert not (base / "workspace/scratch").exists()


def test_demo_refuses_an_existing_workspace(tmp_path):
    marker = tmp_path / "keep.txt"
    marker.write_text("untouched", encoding="utf-8")
    with pytest.raises(FileExistsError):
        demo.run_scenario(tmp_path, "normal")
    assert marker.read_text(encoding="utf-8") == "untouched"
