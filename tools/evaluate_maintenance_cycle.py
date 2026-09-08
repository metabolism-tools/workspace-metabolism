"""Read-only association of declared maintenance evidence, never an execution gate.

Adapters remain responsible for authenticating receipts and checking real data.
This evaluator neither runs checks nor grants permissions.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re

MAX_BYTES = 1024 * 1024
BINDING = ('cycle_id', 'scope_sha256', 'policy_version', 'executor_version', 'consumer_version')


def stamp(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError('timezone_required')
    return parsed


def consumer_gap(boundary, check, finished):
    """Require a declared real workflow and content-bound acceptance contract."""
    contract = boundary.get('consumer_contract', {})
    usage = check.get('consumption', {})
    if not isinstance(contract, dict) or not isinstance(usage, dict):
        return 'consumer_contract_missing'
    digest = contract.get('input_manifest_sha256', '')
    acceptance = contract.get('acceptance_version')
    if (not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest)
            or not isinstance(acceptance, str) or not acceptance.strip()):
        return 'consumer_contract_missing'
    if usage.get('mode') != 'real_workflow':
        return 'real_workflow_missing'
    if usage.get('input_manifest_sha256') != digest:
        return 'input_manifest_mismatch'
    if usage.get('acceptance_version') != acceptance:
        return 'acceptance_mismatch'
    if not re.fullmatch('[0-9a-f]{64}', str(usage.get('output_sha256', ''))):
        return 'output_digest_missing'
    if usage.get('accepted') is not True:
        return 'output_rejected' if usage.get('accepted') is False else 'output_acceptance_missing'
    try:
        if not (finished <= stamp(usage['started_at']) <= stamp(check['checked_at'])):
            return 'consumption_outside_window'
    except (ValueError, KeyError, TypeError, AttributeError):
        return 'consumption_outside_window'
    return None


def evaluate(packet, as_of):
    """Evaluate at an explicit time; only fixed reason codes leave this function."""
    now = stamp(as_of)
    boundary = packet['boundary']
    binding = boundary['binding']
    if any(not isinstance(binding.get(k), str) or not binding[k].strip() for k in BINDING):
        raise ValueError('invalid_binding')
    if not re.fullmatch('[0-9a-f]{64}', binding['scope_sha256']):
        raise ValueError('invalid_scope_digest')
    if type(boundary['recovery_required']) is not bool:
        raise ValueError('invalid_recovery_requirement')
    result = dict(schema='wm.maintenance_cycle.v2', mode='read_only_assessment',
                  assessed_at=now.isoformat(), evidence_trust='reported_not_authenticated',
                  supervision_minutes=None, supervision_sessions=None,
                  supervision_benefit='not_established', token_benefit='not_established',
                  authorizes_execution=False, checks_passed=[], gaps=[])
    decision = boundary['decision']
    execution = packet['execution']
    outcome = execution['status']
    if execution.get('binding') != binding:
        result['state'] = 'execution_binding_mismatch'
        return result
    if decision not in ('allow', 'hold', 'human_decision') or outcome not in (
            'not_run', 'preview', 'no_change', 'completed', 'failed'):
        raise ValueError('invalid_state')
    if decision != 'allow':
        result['state'] = ('boundary_violation' if outcome in ('completed', 'failed', 'no_change')
                           else 'held' if decision == 'hold' else 'human_decision_required')
        return result
    if outcome != 'completed':
        result['state'] = {'not_run': 'not_executed', 'preview': 'preview_only',
                           'no_change': 'no_change', 'failed': 'execution_failed'}[outcome]
        return result
    finished = stamp(execution['finished_at'])
    if finished > now:
        raise ValueError('execution_in_future')
    required = ['integrity', 'consumer'] + (['recovery'] if boundary['recovery_required'] else [])
    checks = packet.get('checks', [])
    if not isinstance(checks, list):
        raise ValueError('invalid_checks')
    failed = False
    for name in required:
        matches = [check for check in checks if check['name'] == name]
        reason = None
        if len(matches) != 1:
            reason = 'missing' if not matches else 'ambiguous'
        else:
            check = matches[0]
            if check.get('binding') != binding:
                reason = 'binding_mismatch'
            elif not re.fullmatch('[0-9a-f]{64}', str(check.get('receipt_sha256', ''))):
                reason = 'receipt_digest_missing'
            elif not (finished <= stamp(check['checked_at']) <= now <= stamp(check['valid_until'])):
                reason = 'outside_evidence_window'
            elif check.get('passed') is False:
                reason, failed = 'failed', True
            elif check.get('passed') is not True:
                reason = 'unknown'
            elif name == 'consumer':
                reason = consumer_gap(boundary, check, finished)
                failed = failed or reason == 'output_rejected'
        if reason:
            result['gaps'].append(f'{name}:{reason}')
        else:
            result['checks_passed'].append(name)
    result['state'] = ('checks_failed' if failed else 'verification_pending'
                       if result['gaps'] else 'declared_checks_passed')
    human = packet.get('human', {})
    if human.get('coverage_complete') is True and human.get('source') == 'measured':
        sessions, minutes = human.get('sessions'), human.get('minutes')
        if (type(sessions) is not int or sessions < 0 or type(minutes) not in (int, float)
                or not math.isfinite(minutes) or minutes < 0):
            raise ValueError('invalid_human_measurement')
        result.update(supervision_minutes=minutes, supervision_sessions=sessions)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--as-of', help='Explicit historical assessment time; defaults to now')
    args = parser.parse_args()
    try:
        with args.input.open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('input_over_budget')
        result = evaluate(json.loads(raw), args.as_of or datetime.now(timezone.utc).isoformat())
        result['input_sha256'] = hashlib.sha256(raw).hexdigest()
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError, OverflowError):
        print(json.dumps({'state': 'invalid_input', 'authorizes_execution': False}))
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['state'] == 'declared_checks_passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
