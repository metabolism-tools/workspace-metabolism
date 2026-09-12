# Claim Before Write (Experimental)

The first implementation reserves exact files before a cooperative AI runner
creates or replaces them. It is not an operating-system sandbox and does not
automatically intercept editor tools, shell commands, or other AI applications.

## Run the Rehearsal

From a source checkout with Python 3.11+ and Git:

```console
python examples/claim_before_write_demo.py
```

The script creates a new temporary Git workspace. Four separate processes attempt
to claim one synthetic file; exactly one succeeds. It then checks session and scope
rejection, policy checks, controlled writing, duplicate requests, delivery checks,
and preservation of an external change. It never opens trading data or modifies
an existing project. The printed directory retains a report and recovery evidence.
The negative-control task deliberately remains open; do not use that directory
as a real workspace or publish its registry (which contains cooperative session
credentials and original file contents).

## Commands and Ownership

`wm claim begin --task TASK --file EXACT_PATH` returns a claim and session.
Repeat `--file` to reserve up to 32 files. The runner supplies that session in
`WM_CLAIM_SESSION` to subsequent commands, not through a user approval message.

| Command | Effect |
|---|---|
| `wm claim expand CLAIM --file EXACT_PATH` | Reserve additional files; reject the entire expansion on conflict. |
| `wm claim renew CLAIM` | Extend an unexpired claim by 30 minutes. |
| `wm claim recover CLAIM` | Reconcile a pending write from observed contents, without rewriting the file or renewing the lease. |
| `wm claim resume CLAIM` | Verify all claimed contents, rotate the owning session, and begin a new 30-minute lease. |
| `wm claim write CLAIM --file EXACT_PATH --content-file TEXT_FILE --operation-id ID --preview` | Check policy, reserve recovery evidence, and create or replace one UTF-8 file. |
| `wm claim finish CLAIM` | Release after the current claimed files match their recorded contents and Git baseline. |

The existing `metabolism.json` must be present. Claiming is not permission to
ignore that policy. `--preview` and `--approver` are caller declarations, not
proof of a performed review or authenticated human approval. The source text file
is explicitly read by the caller's account; this is not a restricted filesystem
read interface. `finish` does not commit, run tests, or verify a deployment.

The standalone backend stores claims in `.coordination/registry.json`, using a
stable operating-system-held lock. It refuses an existing foreign registry
without writing to it. **Do not mix it with another claim manager.** An existing
project must provide an adapter using the same registry and locking protocol as
all its other writers. Creating a second lock does not serialize legacy writers.

## Cleanup Interlock

The local 2026-09-12 implementation connects `clean` and `rollback` to the
standalone claim registry. Executing either operation acquires the same stable
registry lock as claim writes, before the lifecycle state lock, and holds it
through file moves. Preview reads retention scopes without creating claim storage;
an executing operation creates `.coordination/.wm-registry.lock` if necessary.

- Active, paused, unknown non-terminal and expired claims retain their exact
  files and ancestor directories. A pending intent retains ownership even if
  another tool has marked the claim terminal. New claims use this same rule.
- A finished claim without a pending intent does not itself prevent cleanup.
  Existing Git, sensitivity, retention and approval protections still apply.
- Foreign or malformed registries stop cleanup rather than being reset or
  treated as empty. Other host backends still require an explicit adapter.
- `.coordination`, its contents, and existing parent directories containing
  nested claim storage are not cleaned. Historical recycled control directories
  are not silently restored over the current authority.
- Rollback refuses an overlapping claimed destination, including absent files
  and parents. A fresh executing call rechecks ownership; a preview is not a
  reusable authorization.

This coordinates cooperative operations using the same workspace root and
registry. It does not lock independent nested-workspace authorities against new
creation, intercept external shell/editor writes, authenticate registry changes,
or cover `slim`, arbitrary `purge` inputs, or an external orchestrator's deletion.
Deleting or replacing the registry out of band remains outside this guarantee;
absence of a registry is treated as a workspace with no recorded claims.
Missing/unreadable or unrecognized existing evidence must not be manually reset
to bypass a refusal. Large-object recovery integrity limits are unchanged.

Blocked cleanup candidates retain the existing CLI convention: the command may
complete successfully while printing blocked items. Exit code zero is NOT proof
that a requested directory was removed, and must not authorize subsequent raw
deletion by another system. Run `python examples/claim_cleanup_rehearsal.py`
for a disposable cross-process rehearsal.

## Implemented Limits

- Exact paths only, no fuzzy matching, globs, links, or linked aliases. Existing
  files must have a clean tracked Git baseline; prior unexplained changes are
  not adopted by a new claim. New-file parent directories must already exist.
- UTF-8 create/replace only, up to 1 MiB per file, 64 writes and 8 MiB of encoded
  recovery originals per claim. No delete, rename, takeover, or automatic restore.
- A repeated operation ID returns its prior receipt, not a second write. Different
  content with the same ID is refused. An outside edit blocks subsequent writing.
- Pending writes and expired claims retain ownership. The owning session may
  explicitly `recover`, then `resume`. If the pending target still matches its
  original state, the pending intent and original-state observation remain in recovery history. If it
  matches the intended result, an observation-only receipt is recorded. Matching
  contents do not prove who wrote them. Any third state, changed sibling file, or
  invalid evidence blocks recovery; the target is never automatically restored.
- `resume` works only with the current owning credential and recorded contents;
  it rotates that credential and increments the generation. Old credentials can
  no longer write through this entry. The runner must retain the returned session
  privately; lost credentials or an uncertain rotation result require host review.
  This is not a general transfer to a new owner. Each claim permits up to 64
  recovery records and 64 continuations, with originals counted in its 8 MiB budget.
- Successful writes retain original bytes and before/after fingerprints in the
  registry. It is mutable local evidence, not authenticated or tamper-proof audit.
  Process-error tests do not establish filesystem durability after power loss.
- Session values are cooperative credentials, not independently authenticated
  identities. Same-account tools can read the registry or bypass this interface.
- No automatic AI-runner integration, renewal scheduler, final commit-tree
  attribution, or production deployment is included in this first slice.

For an existing host, pass its existing registry transaction, load and save
operations to `ClaimGuard`; do not use the standalone backend against a foreign
registry or create a second coordination authority. See the
[integration guide](existing-system-integration.md).

## Opt-In MCP Editing Pilot

`wm --root WORKSPACE --state-dir STATE mcp --claim-file maintenance.md` starts a
restricted stdio tool profile. The host chooses the exact relative path before
starting it; the filename must be `maintenance.md`, optionally in an existing
subdirectory. Use an independent development workspace and an existing policy.
The normal `wm mcp` catalog is unchanged when this option is absent.

This profile exposes only five tools:

| Tool | Effect |
|---|---|
| `wm_edit_read` | Read the assigned document, not a caller-selected path. |
| `wm_edit_begin` | Register the task; keep its credential in the serving process. |
| `wm_edit_preview` | Store an exact proposed replacement and return its diff and preview ID. |
| `wm_edit_apply` | Apply that preview under the claim lock, checking the current policy and file fingerprint. |
| `wm_edit_finish` | Close after the host has committed the document and the delivery check passes. |

The client cannot supply credentials, choose another path, replace the text at
apply time, expand scope, run commands, initialize policies, or call cleanup tools
through this profile. A stale preview fails; repeating an already successful
operation returns its receipt without another write. Preview generation is not
human approval: policies requiring an approver still deny these writes.

Limits: one connection-owned claim, 16 previews, nonempty UTF-8 replacements up
to 16 KiB, and the existing 30-minute claim lease. The host, not the model-facing
tool, performs any Git commit. Disconnecting or shutting down retains unfinished
ownership and evidence. There is no automatic reconnect, credential recovery,
renewal, commit, release, or rollback. A host must review an unfinished claim; do
not reset the registry to reconnect.

Run `python examples/claim_mcp_workspace.py` to prepare a fresh temporary Git
workspace with a maintenance document and policy. It prints the workspace and
state paths but does not generate or apply an AI edit. Connect a stdio client to
the command above using those paths, then read, begin, preview, inspect the diff,
and apply. After host delivery, finish and shut down the connection.

**This profile is not an OS sandbox.** The registry still stores credentials and
original bytes; the host must protect it from untrusted OS accounts. A client
with direct filesystem or shell access can bypass the interface. It has not
been automatically registered in every AI editor. Cloud supervision, other
orchestrators, and private integration records are outside this release.
