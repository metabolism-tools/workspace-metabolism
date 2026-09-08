import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

spec = importlib.util.spec_from_file_location('cycle', Path(__file__).parents[1] / 'tools/evaluate_maintenance_cycle.py')
cycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cycle)
NOW = '2026-09-08T14:00:00+00:00'


def packet():
    binding = dict(cycle_id='example', scope_sha256='a' * 64, policy_version='1',
                   executor_version='1', consumer_version='1')
    check = dict(binding=binding.copy(), receipt_sha256='b' * 64, passed=True,
                 checked_at='2026-09-08T13:30:00+00:00', valid_until=NOW)
    check['consumption'] = dict(mode='real_workflow', input_manifest_sha256='c' * 64,
                                acceptance_version='acceptance-1', output_sha256='d' * 64,
                                accepted=True, started_at='2026-09-08T13:10:00+00:00')
    return dict(boundary=dict(binding=binding, decision='allow', recovery_required=False,
                             consumer_contract=dict(input_manifest_sha256='c' * 64,
                                                    acceptance_version='acceptance-1')),
                execution=dict(binding=binding.copy(), status='completed', finished_at='2026-09-08T13:00:00+00:00'),
                checks=[dict(check, name='integrity'), dict(check, name='consumer')])


@pytest.mark.parametrize('change,reason', [
    ({'mode': 'replay'}, 'real_workflow_missing'),
    ({'mode': 'heartbeat'}, 'real_workflow_missing'),
    ({'input_manifest_sha256': 'e' * 64}, 'input_manifest_mismatch'),
    ({'acceptance_version': 'other'}, 'acceptance_mismatch'),
    ({'output_sha256': ''}, 'output_digest_missing'),
    ({'accepted': None}, 'output_acceptance_missing'),
    ({'accepted': False}, 'output_rejected'),
    ({'started_at': '2026-09-08T12:59:00+00:00'}, 'consumption_outside_window'),
    ({'started_at': NOW}, 'consumption_outside_window'),
])
def test_consumer_claim_requires_content_and_real_output(change, reason):
    p = packet()
    p['checks'][1]['consumption'].update(change)
    result = cycle.evaluate(p, NOW)
    assert 'consumer:' + reason in result['gaps']
    assert result['state'] == ('checks_failed' if reason == 'output_rejected' else 'verification_pending')


def test_old_boolean_only_consumer_cannot_pass():
    p = packet()
    del p['boundary']['consumer_contract']
    assert 'consumer:consumer_contract_missing' in cycle.evaluate(p, NOW)['gaps']


def test_bound_checks_do_not_invent_supervision_or_authority():
    p = packet()
    before = copy.deepcopy(p)
    r = cycle.evaluate(p, NOW)
    assert r['state'] == 'declared_checks_passed'
    assert r['supervision_minutes'] is None
    assert r['supervision_benefit'] == 'not_established'
    assert r['authorizes_execution'] is False
    assert p == before


@pytest.mark.parametrize('field', cycle.BINDING)
def test_wrong_task_scope_or_version_cannot_close(field):
    p = packet()
    p['checks'][1]['binding'] = dict(p['checks'][1]['binding'], **{field: 'different'})
    r = cycle.evaluate(p, NOW)
    assert r['state'] == 'verification_pending'
    assert 'consumer:binding_mismatch' in r['gaps']


def test_successful_storage_without_consumer_is_pending():
    p = packet()
    p['checks'].pop()
    assert cycle.evaluate(p, NOW)['gaps'] == ['consumer:missing']


def test_execution_itself_must_match_the_boundary():
    p = packet()
    p['execution']['binding']['scope_sha256'] = 'c' * 64
    assert cycle.evaluate(p, NOW)['state'] == 'execution_binding_mismatch'


@pytest.mark.parametrize('change,reason', [
    ({'passed': False}, 'failed'), ({'passed': None}, 'unknown'),
    ({'receipt_sha256': ''}, 'receipt_digest_missing'),
    ({'checked_at': '2026-09-08T12:00:00+00:00'}, 'outside_evidence_window'),
    ({'valid_until': '2026-09-08T13:40:00+00:00'}, 'outside_evidence_window'),
])
def test_bad_consumer_evidence_is_not_success(change, reason):
    p = packet()
    p['checks'][1].update(change)
    assert 'consumer:' + reason in cycle.evaluate(p, NOW)['gaps']


def test_duplicate_receipts_and_missing_recovery_do_not_pass():
    p = packet()
    p['checks'].append(copy.deepcopy(p['checks'][1]))
    p['boundary']['recovery_required'] = True
    assert cycle.evaluate(p, NOW)['gaps'] == ['consumer:ambiguous', 'recovery:missing']


@pytest.mark.parametrize('status,state', [('preview', 'preview_only'), ('no_change', 'no_change'),
                                        ('failed', 'execution_failed'), ('not_run', 'not_executed')])
def test_no_work_and_failure_never_count_as_closed(status, state):
    p = packet()
    p['execution']['status'] = status
    assert cycle.evaluate(p, NOW)['state'] == state


def test_hold_cannot_be_overridden_by_good_checks():
    p = packet()
    p['boundary']['decision'] = 'hold'
    assert cycle.evaluate(p, NOW)['state'] == 'boundary_violation'
    p['execution']['status'] = 'not_run'
    assert cycle.evaluate(p, NOW)['state'] == 'held'


def test_complete_measurement_is_required_even_for_zero():
    p = packet()
    p['human'] = dict(source='measured', sessions=0, minutes=0)
    assert cycle.evaluate(p, NOW)['supervision_minutes'] is None
    p['human']['coverage_complete'] = True
    r = cycle.evaluate(p, NOW)
    assert r['supervision_minutes'] == 0
    assert r['supervision_benefit'] == 'not_established'


@pytest.mark.parametrize('minutes', [True, -1, float('nan'), float('inf')])
def test_invalid_measurements_rejected(minutes):
    p = packet()
    p['human'] = dict(source='measured', coverage_complete=True, sessions=0, minutes=minutes)
    with pytest.raises(ValueError):
        cycle.evaluate(p, NOW)


def test_real_case_remains_pending_without_next_workflow():
    path = Path(__file__).parents[1] / 'docs/case-studies/evidence/matrix-maintenance-20260908.json'
    p = json.loads(path.read_text())
    r = cycle.evaluate(p, p['assessment_time'])
    assert r['checks_passed'] == ['integrity']
    assert r['gaps'] == ['consumer:missing']
    assert r['supervision_minutes'] is None


@pytest.mark.parametrize('content', ['private-secret', '[]', 'x' * (cycle.MAX_BYTES + 1)],
                         ids=['invalid-json', 'wrong-shape', 'over-budget'])
def test_cli_rejects_invalid_or_oversize_input_without_leaking(tmp_path, content):
    path = tmp_path / 'private-secret.json'
    path.write_text(content)
    before = path.read_bytes()
    run = subprocess.run([sys.executable, str(Path(cycle.__file__)), str(path)], capture_output=True, text=True)
    assert run.returncode == 2
    assert json.loads(run.stdout)['state'] == 'invalid_input'
    assert 'private-secret' not in run.stdout + run.stderr
    assert path.read_bytes() == before
