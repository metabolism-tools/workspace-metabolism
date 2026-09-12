# Registered SQLite Resource Checks

`wm db-check` checks an existing database by its policy-registered name. It never
searches for another file with a similar name, creates a database, initializes
tables, repairs a database, or deletes a file. It returns table names, not records.
Available in v0.6.0. Installing the package does not automatically replace an
application's readers; explicitly connect its existing canonical path helper.

## Register Once in the Existing Policy

Add the optional fields to the database's exact entry in `metabolism.json` (or the
existing policy selected with `--registry`). Do not create a parallel registry.
The following is a synthetic example, not a production database registration:

```json
{
  "version": 1,
  "entries": [
    {"path": "data/*", "grade": "G2", "cleanup": "never"},
    {
      "path": "data/index/app.sqlite",
      "grade": "G2",
      "cleanup": "never",
      "resource_id": "query-index",
      "sqlite": {"required_tables": ["snapshot_day", "snapshot_row"]}
    }
  ]
}
```

Use the application's existing canonical path and actual required tables.
Resource names must be unique lowercase identifiers. Both new fields are
required together. Resource paths must be literal workspace-relative file paths,
not glob patterns, absolute paths, traversal paths, symlinks, junctions or hard
link aliases. Existing policy entries without these fields continue to work.
Cleanup grades and retention rules keep their existing meaning.

## Use

```powershell
wm --root D:/example-workspace db-check --resource query-index
```

The MCP equivalent is `wm_db_check` with `{"resource_id":"query-index"}`.
Neither interface accepts a path override or arbitrary SQL. Unknown names and
invalid/ambiguous registration fail instead of choosing the first search result.

Success returns JSON with `status: "ok"`, the registered relative path,
`read_only: true`, required tables, and observed user tables. CLI failure returns
`status: "blocked"`, a reason, and exit code 2; MCP returns `isError: true`.
There is no automatic initialize/rebuild/retry fallback. Missing files, empty
files, corrupt databases and missing required tables remain distinguishable
errors. A valid initialized database with zero data rows may pass legitimately.

No extra human approval is required. Check results go to the caller only; this
command does not create a second evidence store or append a journal record.

## Embed in an Existing Reader

For a trusted application that already has a canonical path function:

```python
from contextlib import closing
from workspace_metabolism.sqlite_guard import open_existing_sqlite

# canonical_index_path comes from the application's existing configuration.
with closing(open_existing_sqlite(
    canonical_index_path, required_tables=("snapshot_day",)
)) as connection:
    rows = connection.execute(
        "SELECT day FROM snapshot_day WHERE day = ?", (requested_day,)
    ).fetchall()
```

Do not call an initializing writer first and then switch it to read-only: the
side effect has already happened. Preserve deliberate initialization as a
separate writer workflow. This helper is not a wrapper that can undo earlier
writes by another connection function.

Read-only connections use `mode=ro` plus SQLite's
[SQL authorization callback](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.set_authorizer).
The callback permits reads, ordinary SQL functions (not extension loading),
transactions, and a small metadata PRAGMA set. It rejects schema/data/temp writes,
ATTACH, and configuration changes outside that set. This also prevents a later
helper from accidentally running initialization SQL on the guarded connection.
Explicit `writable=True` uses existing-only `mode=rw` without that callback;
it is for trusted writers such as `wm slim --yes`, not a permission grant.

## Limits

- Resource binding validates the configured location, not that the policy itself
  chose the right database. A substituted same-schema copy can still pass.
- Passing does not prove freshness, completeness, correct data, consumer health,
  business acceptance, or identity/authentication. Required tables are not a
  full schema-version contract.
- The check and a later caller operation are separate. Pass/fail is not a write
  receipt or a guarantee against concurrent file replacement or stale overwrites.
- Trusted Python callers can replace the callback, register side-effecting SQL
  functions, or open other connections. This is accidental-misuse prevention,
  not an OS sandbox for hostile code or a global permissions system.
- SQLite can still use temporary storage or WAL/journal sidecars as needed;
  main-database SQL read-only is not a claim of zero filesystem activity.
- An empty file protected by `G2/never` stays protected. No consumer found does
  not grant permission to delete it or alter the policy.

Run `python examples/sqlite_wrong_path_demo.py` for a synthetic wrong-path and
initializing-reader case. See the [integration guide](existing-system-integration.md).
