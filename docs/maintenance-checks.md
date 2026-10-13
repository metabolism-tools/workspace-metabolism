# Maintenance executors and actual SQLite consumer checks

`wm doctor` can read explicitly registered maintenance evidence. Separately, an
explicit consumer command can read a registered SQLite relation and compare its
real export with an export frozen before maintenance. Both features use the
standard library. Neither feature installs or starts a scheduler.

## Register an existing maintenance task

Add a task to the existing policy. Receipt locations and object paths are relative
to the workspace; escaping paths are refused. An executor description or `ok=true`
in the policy does not prove that an executor ran.

```json
{
  "maintenance_tasks": [{
    "id": "research-retain",
    "scope": ["data/app.db"],
    "policy_version": "research-retention-1",
    "executor": {
      "id": "scheduled-wm-retain",
      "version": "1",
      "description": "The existing application maintenance-window executor",
      "operation_action": "retain"
    },
    "required_actions": ["execute"],
    "required_capabilities": ["sqlite_read", "sqlite_write"],
    "capability_receipt": "evidence/capability.json",
    "execution_receipt": "evidence/execution.json",
    "max_age_seconds": 86400
  }]
}
```

The existing executor adapter produces two bounded JSON documents after actual
permission checks, probes and execution. Doctor reads them; it never creates them,
touches the database, runs commands, grants permission, or refreshes timestamps.

The common `binding` contains `task_id`, `scope_sha256`, `policy_version`,
`policy_sha256`, `executor_id` and `executor_version`. Use
`scope_digest(["data/app.db"])` for the scope digest; it hashes the sorted path set,
**not object contents**. Use the SHA-256 of the exact policy file for
`policy_sha256`. Policy edits therefore invalidate old bindings.

- `wm.executor_capability.v1` contains that binding, timezone-aware `checked_at`
  and `valid_until`, `permissions`, and `probes`. Each permission is a complete
  actual `wm govern` journal record (including its hash), for an allowed required
  action and the exact scope. Each required probe has a capability name,
  `status="passed"`, the actual probe method and an `observation_sha256` of its
  observation. A writer probe must use an application-approved maintenance window
  or a temporary copy; the example rolls back its temporary-database write probe.
- `wm.maintenance_execution.v1` contains the common binding plus `cycle_id` and
  `object_manifest_sha256`, `started_at`, `finished_at`, and a complete actual
  `operation_receipt` from the wm journal. The operation must carry its own exact
  `db`/`database` or `paths` scope. A wrapper's scope alone cannot substitute for
  missing operation scope. Old records without it remain `scope_evidence_missing`.
  The adapter computes the object-manifest digest from actual consumed content,
  not names/counts alone. Preview records never establish actual execution.

Doctor verifies the record hashes, declared bindings, time windows, capabilities,
permission decisions and actual operation outcomes. It reports fixed states such
as `executor_missing`, `capability_evidence_missing`, `permission_denied`,
`execution_missing`, `execution_stale`, `execution_failed`, `scope_mismatch`,
`policy_mismatch`, `not_executed`, or `recent_execution_reported`.
`no_change_reported` is a recent actual run with no due changes; it is not a count
of completed substantive maintenance. `all_recent` accepts either recent state.
An old policy without `maintenance_tasks` remains compatible and reports
`not_declared`.

The Python integration is:

```python
from workspace_metabolism.maintenance_checks import assess_maintenance_tasks
result = assess_maintenance_tasks(root, registry, policy_sha256=policy_hash)
```

Each receipt is limited to 256 KiB, the declaration to 128 tasks. Output contains
task IDs, fixed states, binding/evidence hashes and times, not raw permission or
business records. Hash consistency does not authenticate a producer, prove OS
permissions, or make self-reported probes independently trustworthy. The output
states `trust="local_reported_not_authenticated"` and
`authorizes_execution=false`. A production adapter must collect the real records
through its existing trusted entry point and retain the original observations.

## Explicitly consume a registered SQLite export

Register a named command in the policy. The only supported adapter is the fixed
`sqlite_json_export_v1` implementation, version `1`; arbitrary commands and SQL
are not accepted. Identifiers are validated. A relation may be an existing table
or view; the SQLite authorizer restricts reads, rejects writes/ATTACH and blocks
extension loading. The exact configured file is opened read-only without creation.

```json
{
  "consumer_checks": [{
    "id": "latest-export",
    "version": "domain-export-1",
    "adapter": "sqlite_json_export_v1",
    "adapter_version": "1",
    "database": "data/app.db",
    "relation": "latest",
    "id_column": "object_id",
    "json_column": "body",
    "fields": ["value"]
  }]
}
```

The relation must provide nonduplicate string/integer IDs and JSON objects with
all registered fields. The command exports the registered fields for **every row
in that relation** in ID order, computes an input manifest from the actual row
contents and computes the actual export digest. A frozen comparison checks exact
export equality; caller-supplied success booleans are ignored. This proves the
registered export remained equal in that snapshot. It does not prove broader
business correctness or the freshness/completeness of a domain-specific view.
Review the consumer relation and required fields before freezing a baseline.

Capture the actual pre-maintenance export, then explicitly call the check after
the actual operation. Files in these examples are outputs saved by the caller;
doctor never runs these commands.

```powershell
python -m workspace_metabolism.maintenance_checks capture --root . --policy metabolism.json --consumer latest-export | Out-File -Encoding utf8 baseline.json
python -m workspace_metabolism.maintenance_checks check --root . --policy metabolism.json --consumer latest-export --baseline baseline.json --operation-receipt operation.json
python -m workspace_metabolism.maintenance_checks check --root . --policy metabolism.json --consumer latest-export --baseline baseline.json --operation-receipt operation.json --recovery-receipt restore.json
```

`operation.json` and `restore.json` are the complete corresponding actual wm
journal entries, not an `ok` object. Recovery must match the original operation's
run, object scope, exact policy and time window. The consumer executes an actual
read even if the supplied receipt reports success. Output changes return code 1;
missing/mismatched inputs, failed operations and budgets return code 2; a matched
export returns code 0. Default record times use the wm journal's second precision;
equal timestamps cannot establish finer ordering.

The baseline includes its real export data. Keep it with the application's
protected evidence and retention rules; do not publish private baselines. Reader
budgets are 100,000 rows, 32 MiB JSON input, and 30 seconds of SQLite execution.
The progress handler also bounds an expensive registered view before its first
row is returned. The consumer itself leaves database bytes unchanged.

The generated receipt binds the operation hash, policy-content version/hash,
object-content manifest, registered consumer version, actual command version,
times and computed comparison result. `receipt_sha256` identifies its complete
content (excluding that digest field). `checked_at` and `valid_until` initially
refer to the same observed instant; the caller must not extend evidence validity
without a domain-approved freshness rule.

Its `binding`, `passed`, `receipt_sha256`, and `consumption` can be used by
`tools/evaluate_maintenance_cycle.py`. Freeze the expected post-maintenance input
manifest and acceptance contract at the actual consumer boundary; do not copy an
expected digest into a claimed actual-consumption field. The evaluator still
requires a separate integrity check and an explicit boundary/execution binding;
this consumer receipt alone does not close a whole maintenance cycle.

## Try the complete temporary example

```powershell
python examples/maintenance_consumer_demo.py
```

The example creates only synthetic data in a temporary directory. An actual
SQLite latest-view consumer exports a value before retention, after deleting two
old unreferenced versions with `wm retain`, and after `retain --restore`. Both
output comparisons pass. The tests also deliberately corrupt the latest value:
the next export and post-restore export both fail, even though the row-restore
operation itself completed. This records the limitation rather than hiding it.

The example makes no cloud calls or production changes. A real application's
domain reader needs its own approved adapter and acceptance rule; that work
cannot be replaced with a heartbeat or a supplied `ok=true`.
