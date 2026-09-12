# v0.6.0: Claim-Aware Maintenance and Non-Creating SQLite Reads

This release moves the reusable workspace protections into the installable WM
package. It does not add a scheduler, an AI runtime, or a Symphony integration.

## Included

- Experimental `wm claim`: exact-file reservation, policy-checked UTF-8 writes,
  before/after fingerprints, durable write intents, duplicate-operation receipts,
  explicit same-owner recovery/continuation, and delivery checks.
- `clean` and `rollback` coordinate with the standalone claim registry through
  the actual move. Active/expired claims and pending writes retain their scopes;
  control storage is protected and malformed/foreign registries fail closed.
- Opt-in `wm mcp --claim-file maintenance.md`: a five-tool document editing
  profile. Credentials stay in the serving process. The default catalog gains
  `wm_db_check` and otherwise retains its existing operations.
- `wm db-check --resource NAME`: check an exact SQLite binding in the existing
  policy, without path guessing, arbitrary SQL, database creation or repair.
- `open_existing_sqlite`: reusable existing-only, read-only-by-default connection
  helper. Read connections reject initialization, temp writes and ATTACH;
  `slim` uses the helper while preserving v0.5.2 consumer-evidence protections.
- Public integration guides and disposable claim/SQLite examples.

## Installation

GitHub release assets include a wheel and source archive:

```console
python -m pip install https://github.com/metabolism-tools/workspace-metabolism/releases/download/v0.6.0/workspace_metabolism-0.6.0-py3-none-any.whl
wm --version
wm claim --help
wm db-check --help
```

PyPI remains a separate publishing channel; the last verified available version
was 0.5.1. Do not expect an ordinary `pip install --upgrade workspace-metabolism`
to install 0.6.0 until its PyPI publication is confirmed.

## Compatibility and Limits

Python 3.11+, no runtime dependencies. Existing policies need no new fields
unless opting into named SQLite resources. Executed file cleanup can now create
`.coordination/.wm-registry.lock`; previews do not initialize claim storage.
Foreign coordination registries now block stock cleanup and need a host adapter.
Do not reset existing registries or mix different lock protocols.

Claims/MCP editing remain cooperative and experimental, not authenticated
permissions or a sandbox. Expiry does not release unfinished ownership. Local
evidence is mutable. `db-check` establishes path/schema compatibility, not data
identity, freshness or business correctness. No global AI interception, automatic
takeover, deployment of private systems, or unattended recovery is claimed.

## Verification

The release checkout is based on current upstream main, not the older development
checkout. Local full package regression: 369 passed, 1 skipped (Windows symlink
fixture unavailable). Existing CI runs Python 3.11/3.12 on Windows, Linux and
macOS. Package build/install and CI results are checked before the release tag.
Private system deployment is recorded separately, without uploading private data.
