"""Disposable, synthetic end-to-end demonstration; never a production approval."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from datetime import datetime, timedelta, timezone

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))
from workspace_metabolism import changes
from workspace_metabolism.core import verify_journal

spec = importlib.util.spec_from_file_location('maintenance_cycle_demo', REPO / 'tools/evaluate_maintenance_cycle.py')
cycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cycle)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def consume(root):
    """Fixed consumer reads maintained data and persists its actual result."""
    rows = json.loads((root / 'records.json').read_bytes())
    result = {'count': len(rows), 'total': sum(row['amount'] for row in rows)}
    (root / 'result.json').write_bytes(encoded(result))


def run_scenario(scenario):
    if scenario not in ('equivalent', 'wrong_result', 'missing_consumer'):
        raise ValueError('unknown scenario')
    with tempfile.TemporaryDirectory(prefix='wm-public-demo-') as folder:
        base = Path(folder)
        root, state = base / 'workspace', base / 'state'
        root.mkdir()
        before = b'[\n {"amount": 7},\n {"amount": 11}\n]\n'
        after = encoded([{'amount': 7}, {'amount': 12 if scenario == 'wrong_result' else 11}])
        target = root / 'records.json'
        target.write_bytes(before)
        protected = root / 'schedule.txt'
        protected.write_bytes(b'disabled\n')
        policy = root / 'policy.json'
        policy.write_bytes(encoded({'version': 1, 'entries': [], 'ai_governance': {
            'default': 'deny', 'protected_paths': ['schedule.txt'],
            'actions': {'write': {'allow': True, 'requires_preview': True}}}}))
        # Freeze an independent expected result before proposing any modification.
        expected = encoded({'count': 2, 'total': 18})
        contract = {'expected_output_sha256': digest(expected), 'input_sha256': digest(after)}
        prepared = changes.run_change(root, state, policy, 'prepare', files=['records.json'],
            protected=['schedule.txt'], goal='Compact synthetic records without changing downstream totals',
            acceptance=json.dumps(contract, sort_keys=True))
        Path(prepared['draft'], 'records.json').write_bytes(after)

        def call(command, **kwargs):
            return changes.run_change(root, state, policy, command, change_id=prepared['id'], **kwargs)

        review = call('review')
        call('apply', approval=review['digest'], approver='Disposable demo only; not owner authorization',
             acceptance='Draft is valid JSON; semantic acceptance is still pending')
        finished = datetime.now(timezone.utc)
        binding = dict(cycle_id=prepared['id'], scope_sha256=review['digest'],
                       policy_version=digest(policy.read_bytes()),
                       executor_version=digest(Path(changes.__file__).read_bytes()),
                       consumer_version=digest(Path(__file__).read_bytes()))
        checks = []

        def record(name, passed, evidence, **extra):
            checks.append(dict(name=name, binding=binding.copy(), passed=passed,
                receipt_sha256=digest(encoded(evidence)), checked_at=datetime.now(timezone.utc).isoformat(),
                valid_until=(finished + timedelta(minutes=5)).isoformat(), **extra))

        record('integrity', target.read_bytes() == after and protected.read_bytes() == b'disabled\n',
               {'actual': digest(target.read_bytes()), 'protected': digest(protected.read_bytes())})
        consumer_receipt = None
        restored = False
        if scenario != 'missing_consumer':
            started = datetime.now(timezone.utc).isoformat()
            actual_input = digest(target.read_bytes())
            consume(root)
            actual_output = digest((root / 'result.json').read_bytes())
            accepted = actual_input == contract['input_sha256'] and actual_output == contract['expected_output_sha256']
            consumer_receipt = dict(mode='real_workflow', input_manifest_sha256=actual_input,
                output_sha256=actual_output, acceptance_version=digest(encoded(contract)),
                accepted=accepted, started_at=started)
            record('consumer', accepted, consumer_receipt, consumption=consumer_receipt)
            if not accepted:
                # Explicit, preselected response for this disposable data-only example.
                call('restore')
                consume(root)
                restored = target.read_bytes() == before and (root / 'result.json').read_bytes() == expected
                if not restored:
                    raise RuntimeError('recovery failed')
        packet = dict(boundary=dict(binding=binding, decision='allow', recovery_required=False,
            consumer_contract=dict(input_manifest_sha256=contract['input_sha256'],
                                   acceptance_version=digest(encoded(contract)))),
            execution=dict(binding=binding.copy(), status='completed', finished_at=finished.isoformat()),
            checks=checks)
        assessment = cycle.evaluate(packet, datetime.now(timezone.utc).isoformat())
        return dict(scenario=scenario, assessment=assessment, consumer_receipt=consumer_receipt,
                    recovered=restored, journal_chain_ok=verify_journal(state)['chain_ok'],
                    retained_bytes=sum(p.stat().st_size for p in base.rglob('*') if p.is_file()),
                    evidence=packet)


def run():
    return dict(schema='wm.synthetic_governed_change.v1', synthetic=True,
                production_validated=False, supervision_savings=None, token_savings=None,
                scenarios=[run_scenario(name) for name in
                           ('equivalent', 'wrong_result', 'missing_consumer')])


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
