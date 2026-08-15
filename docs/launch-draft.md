# Launch drafts (Show HN / r/Python)

Status: draft for the user to review before posting. Repo URL placeholder:
`https://github.com/tongflau-dongzhu/workspace-metabolism`

## Show HN (Hacker News)

**Title option A**

Show HN: workspace-metabolism – one policy file controls file cleanup, with recycle/rollback and a hash-chain audit

**Title option B**

Show HN: A zero-dependency CLI where a single JSON policy governs file lifecycle: audit, recyclable clean, rollback, purge

**Body (paste into the first comment)**

`workspace-metabolism` is a zero-dependency CLI (Python 3.11+) that manages the
lifecycle of files in a workspace from a single policy file.

Why: most tools either show you disk usage (ncdu) or delete files (rmlint).
This one never deletes directly. Expired items move to a recycle area,
`rollback` restores them after per-file SHA-256 checks, `purge` is the only
real delete, and every action lands in a hash-chained journal you can verify.

Highlights:

- Policy as code: every path is graded G1–G4 (never / keep / approve + reference check / auto)
- Safety first: dry-run by default; G3 needs `--approve` + `--approver`; protected windows, size caps, reference checks
- Auditability: hash-chained journal, `wm verify` detects any tampering
- Scheduling out of the box: Windows Task Scheduler + cron templates (placeholders only, no environment guessing)
- Zero dependencies; tests run on Ubuntu / Windows / macOS (Python 3.11 & 3.12)

Links: [repo](https://github.com/tongflau-dongzhu/workspace-metabolism) · [README](https://github.com/tongflau-dongzhu/workspace-metabolism#readme) · PyPI (coming)

**Launch-day notes**

- Post Tuesday–Thursday, 09:00–12:00 US Eastern
- Answer every comment quickly; ask for edge cases they hit
- Be honest about scope: v0.1, alpha; hardening is in progress

## r/Python

**Title**

[Meta] I built a zero-dependency CLI that manages file lifecycles from one policy file: audit, recyclable clean, rollback, hash-chain verify

**Body**

Long story short: my workspace kept filling up, and I wanted cleanup I could
trust. `workspace-metabolism` is a policy-driven file lifecycle tool:

- You write one JSON policy that grades paths G1–G4 (never / keep / approve / auto)
- `wm audit` is a read-only health check (candidates, disk alerts, growth, duplicates)
- `wm clean` moves expired items to a recycle area — never a direct delete
- `wm rollback <run_id>` restores them after a per-file SHA-256 check
- `wm purge` is the only real delete, and only inside the recycle area
- Every action is appended to a hash-chained journal; `wm verify` detects tampering
- Optional protected window (e.g. your business hours), size caps, reference checks before G3 cleanup
- Windows Task Scheduler and cron templates included

It is pure stdlib (Python 3.11+), no dependencies, and tests run on three OSes.
I would love feedback on the safety model and the policy file format in
particular — what would you add before trusting it with real files?

Repo: https://github.com/tongflau-dongzhu/workspace-metabolism
