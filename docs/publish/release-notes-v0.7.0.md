# v0.7.0: Reference-safe SQLite row retention

Adds `wm retain`: keep the newest N JSON versions per group and every declared
reference. Preview is the default. Execution requires an explicit G2 policy,
respects ownership and protected windows, and computes its plan in the same
SQLite write transaction that performs deletion.

Complete typed rows are exported and verified before deletion. Use
`wm retain --db <database> --restore <run_id> --yes` to restore them without
overwriting changed rows. Recovery batches live in `state/retention`, are outside
file purge, and have no automatic expiration. Interrupted prepared batches remain
blocked until inspected/reconciled. Reports do not claim freed disk space: no
VACUUM is performed, and recovery material uses space.

Policy must list the complete in-table reference paths. Missing referenced
objects, malformed payloads, content-hash mismatches and budget overruns stop
retention. External references are not inferred. The host adapter may narrow
candidates and supply its existing claim backend; it cannot widen WM's safe set.
Triggers, foreign keys, generated columns and composite primary keys are refused.

Install the GitHub wheel (PyPI is a separate channel):

```console
python -m pip install https://github.com/metabolism-tools/workspace-metabolism/releases/download/v0.7.0/workspace_metabolism-0.7.0-py3-none-any.whl
wm --version
wm retain --help
```

Existing policies remain unchanged. Opt in using the complete example under
“SQLite row retention” in README. The earlier unpublished local retention draft
is superseded; its partial-row exports and lack of restoration are not shipped.
This release does not enable an automatic deletion schedule or certify downstream
business correctness. See `tests/test_retain.py` for round-trip, failure-injection,
concurrency, reference and policy-boundary regressions.
