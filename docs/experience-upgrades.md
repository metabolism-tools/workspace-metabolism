# Experience-driven upgrades (0.8.0)

Install the exact 0.8.0 wheel from the [GitHub release](https://github.com/metabolism-tools/workspace-metabolism/releases/tag/v0.8.0), or install this checkout with `python -m pip install -e .`, then use
`wm doctor --json` to see the Python executable, module path and running version.
GitHub and PyPI are verified independently; a GitHub release alone does not
establish availability on PyPI. See the [release notes](publish/release-notes-v0.8.0.md).

## Cleanup and recovery

- A durable manifest is written before any file moves and after each completed
  move. A process interruption leaves a discoverable recovery batch.
- `wm verify` and `wm doctor` report interrupted batches, unreadable manifests
  and orphan recycle folders. `wm rollback <run_id>` reconciles an interrupted
  batch and can resume an interrupted restore. It checks the original workspace
  and refuses to overwrite a destination. `purge` skips unresolved batches.
- Every new file snapshot uses streaming SHA-256 hashes, including batches above
  the former 256 MiB / 5,000-file thresholds. Restoration compares the entire file
  inventory and contents. This costs additional read time for large directories.
- Old `size_only` snapshots cannot prove content integrity. Automatic restoration
  now refuses them and preserves their recycle data for manual inspection. Do not
  generate replacement hashes and treat them as proof of the original contents.
  Old manifests without a completion status are also protected from purge until
  reviewed; ones with complete hashes can be restored normally.
- Partial cleanup exits unsuccessfully, records the actual verified bytes moved,
  and claims zero disk space reclaimed. Restoration and verification also return
  a failure status when work remains unresolved.

A hard process exit can leave the existing `.wm.lock` file. Doctor and verify
can still report recovery evidence. Confirm the recorded process has stopped and
no other maintenance worker is active before manually removing that exact stale
state lock; then run rollback. The tool never breaks a live or uncertain lock.
Tests cover both an ordinary interruption and a subprocess hard exit followed
by this reviewed lock removal. They do not simulate storage hardware failure.
Symlinks and Windows junctions in clean/restore paths or recycle batches are refused.

Durability uses flushed files and atomic manifest replacement (plus directory
sync on POSIX). It cannot promise survival of faulty storage hardware. Manifests
and local journal hashes remain local consistency evidence, not authenticated
attestations. Cross-filesystem partial copies are retained for manual review
when both source and destination exist; they are never overwritten automatically.

## Maintenance and consumers

The [maintenance checks](maintenance-checks.md) document explicit executor,
capability, operation and consumer evidence. Doctor reads declared receipts and
does not schedule or execute maintenance. The SQLite consumer example uses an
isolated database and compares actual exports before maintenance, after maintenance
and after restoration. Each result is bound to the registered object, policy and
consumer contract; passing that example does not certify a production system.

## Distribution verification

`tools/verify_release.py` checks the requested version and published wheel digest
from GitHub or PyPI, installs that exact wheel in the current environment and
exercises the installed CLI in a temporary workspace. Use a disposable environment.
The release workflow runs this check on Windows and Linux after a GitHub release;
manual runs can select PyPI after an upload. It never publishes or guesses that
the two channels contain the same release.
