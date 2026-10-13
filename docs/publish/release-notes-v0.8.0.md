# v0.8.0: Recoverable cleanup and maintenance evidence

## Changes

- Save durable recovery records before moving files and after each verified move.
  Report interrupted and orphan batches in `verify` and `doctor`; protect them
  from purge. Partial operations return an unsuccessful exit status.
- Hash every file in new cleanup batches, including large batches. Verify the
  complete file inventory and content before and after restoration.
- Refuse symbolic links and Windows junctions in cleanup and restoration paths.
- Report the actual Python executable, module path and version in `doctor`.
- Check declared maintenance executor receipts for scope, policy, permission,
  capability, version and freshness. Configuration alone does not prove execution.
- Add an explicitly registered SQLite export consumer with an isolated
  before/after/restore example. It compares actual exported output and binds the
  result to operation and policy evidence; it does not certify a production system.
- Build and check wheels in independent environments; verify GitHub and PyPI
  distributions separately after publication.

## Install

```console
python -m pip install https://github.com/metabolism-tools/workspace-metabolism/releases/download/v0.8.0/workspace_metabolism-0.8.0-py3-none-any.whl
wm --version
wm doctor --json
```

`SHA256SUMS` records the release artifact digests. PyPI is a separate channel:
use `python -m pip install workspace-metabolism==0.8.0` only after that exact
version is available there.

## Compatibility and recovery

Old `size_only` snapshots cannot verify original file contents. Automatic restore
refuses them and preserves their data for manual review. Old manifests without a
completion status are protected from purge; batches with complete hashes can
still be restored. Large batches take more read time and recovery-record space.

A hard process exit may leave `.wm.lock`. Confirm that its recorded process has
stopped and no other worker is active before removing that exact stale lock and
retrying rollback. No live or uncertain lock is broken automatically. Storage
hardware failure and downstream production recovery are not claimed.

See [upgrade details](../experience-upgrades.md) and
[maintenance checks](../maintenance-checks.md). Existing policies can continue
without declaring maintenance tasks or consumers. No schedule is enabled.
