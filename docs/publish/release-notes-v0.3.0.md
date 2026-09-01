# workspace-metabolism v0.3.0

## What's new: `wm slim` — in-place SQLite trimming

Databases rot too. `wm slim` is the DB-internal analogue of `wm clean`:

- **Never deletes rows or files** — only rewrites one JSON blob column,
  dropping policy-listed heavy keys (e.g. `factor_observations` that nothing
  reads after they are stored).
- **keep_recent** — rows whose reference value is among the newest N distinct
  values (e.g. the newest N epochs) are left untouched.
- **VACUUM** — when the reclaim exceeds `vacuum_min_gb`, `--yes` also reclaims
  the freed pages.
- **Journaled** — every run lands in the hash-chained audit trail
  (action `slim`); dry-run by default, `--yes` to execute.
- **Policy-driven** — the policy entry for the database declares the recipe:

```json
{
  "path": "data/app.db", "grade": "G2", "cleanup": "never",
  "db_slim": {
    "table": "work_units",
    "blob_column": "payload_json",
    "strip_keys": ["factor_observations"],
    "keep_recent": {"table": "epochs", "column": "created_at", "n": 3},
    "vacuum_min_gb": 1.0
  }
}
```

Run it (maintenance window, when the DB is not in use):

```bash
wm slim --db data/app.db            # dry-run: how many rows, how much reclaimable
wm slim --db data/app.db --yes      # execute + journal; VACUUM if reclaim >= 1 GB
```

CLI overrides exist for every policy field (`--table`, `--blob-column`,
`--strip-keys`, `--keep-recent`, `--keep-table`, `--keep-column`,
`--vacuum-min-gb`). Identifiers are validated against the database schema —
no free-form SQL.

## Why this belongs in the metabolism tool

The audit trail answers "what happened to my workspace". Until v0.3.0 it was
file-only; databases were invisible and rotted silently (a 20.7 GB work
ledger caused minute-long queries in production). `slim` makes DB bloat a
first-class, policy-driven, audited lifecycle concern — the same
classify → audit → clean → rollback philosophy, applied inside the file.
