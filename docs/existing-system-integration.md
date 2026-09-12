# Integrate Into an Existing System

WM supplies checks and controlled operations, not a replacement scheduler or AI
runtime. Keep existing task dispatch, resource locations, ownership storage,
deployment controls and business acceptance checks.

## Existing Database Readers

Use the application's authoritative path function, then call
`workspace_metabolism.sqlite_guard.open_existing_sqlite(path,
required_tables=("expected_table",))`. The returned connection is caller-owned;
close it with `contextlib.closing` or `finally`.

Replace a reader's create-capable connection, not the intentional initialization
or migration entry. Preserve existing fallback behavior when the optional index
is missing, invalid, empty, or incompatible. Do not silently initialize a file to
make a query return an empty success. Do not replace a fallback with made-up data.

For a host with no Python package installation workflow, pin the small helper as
a reviewed vendored file with the MIT license and source version/hash, as for
other existing integrations. Do not silently fetch the latest source at runtime.

Verify the actual consumer: it reads a valid fixture without changing its main
database, rejects a missing path without creating it, and keeps its established
fallback. The [resource guide](sqlite-resources.md) covers named CLI/MCP checks.

## Existing Task Ownership

`ClaimGuard` accepts a host backend with `transaction()`, `load()` and
`save(registry)`. Reuse the registry and lock already honored by all writers.
The host supplies its write-policy callback and clean-baseline check. The runner
keeps session values private; humans need not copy session credentials.

The stock `wm claim` CLI uses the standalone backend. **It cannot adopt a foreign
coordination registry.** Stock `clean`/`rollback` now refuse an unrecognized
registry instead of treating it as empty. Do not point these commands at an
existing host registry and remove it to get past the refusal. Integrating cleanup
with a different host backend remains explicit application work, not automatic
support supplied by this version.

Use the [claim guide](claim-before-write.md) for lifecycle and evidence limits.
An expired lease or interrupted write is not permission for another task to take
over. Claims coordinate participating operations, not arbitrary shell/editor I/O.

## Deliver the Integration

1. Select an existing consumer or writer, not a new demonstration-only pipeline.
2. Adopt the applicable helper while keeping that application's behavior and locks.
3. Run focused consumer tests and its existing release gates.
4. Publish the exact source/package, deploy through the host's established process,
   and verify the running entry, not just package installation.

Keep public synthetic examples separate from private operation records. A
published package, deployed code, and successful real consumer are three distinct
delivery facts. No orchestration framework, phone approval system, trading
execution, or unattended recovery is introduced here.
