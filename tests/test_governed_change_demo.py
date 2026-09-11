import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('demo', Path(__file__).parents[1] / 'examples/governed_change_demo.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


@pytest.mark.parametrize('scenario,state,recovered', [
    ('equivalent', 'declared_checks_passed', False),
    ('wrong_result', 'checks_failed', True),
    ('missing_consumer', 'verification_pending', False),
])
def test_actual_consumer_distinguishes_outcomes(scenario, state, recovered):
    result = demo.run_scenario(scenario)
    assert result['assessment']['state'] == state
    assert result['recovered'] is recovered
    assert result['journal_chain_ok']
    assert result['assessment']['authorizes_execution'] is False
    assert result['assessment']['supervision_minutes'] is None
    assert result['retained_bytes'] < 1024 * 1024
    if scenario == 'missing_consumer':
        assert result['consumer_receipt'] is None
        assert 'consumer:missing' in result['assessment']['gaps']


def test_bad_consumer_cannot_pass_by_claiming_success(monkeypatch):
    def wrong(root):
        (root / 'result.json').write_bytes(demo.encoded({'count': 2, 'total': 999}))
    monkeypatch.setattr(demo, 'consume', wrong)
    # Both acceptance and recovery re-read persisted output; no forged successful recovery.
    with pytest.raises(RuntimeError, match='recovery failed'):
        demo.run_scenario('equivalent')
