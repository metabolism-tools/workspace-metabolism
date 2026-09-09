# Reviewed local changes: experimental pilot

This is a cooperative local workflow, not a security sandbox or authenticated approval system. It does not run an AI, execute tests, or contact a service. No production or Dongzhu files are needed.

## Scope

- Select up to 100 existing UTF-8 files, each at most 1 MiB. Only selected files are copied, not a runnable copy of the entire repository.
- Extra files, deleted files, protected-file edits, binary files, mode changes, linked files, policy edits and Git metadata targets are rejected.
- A task contains a goal and acceptance criteria. These are recorded, not automatically proven.
- Review binds original bytes/modes, proposed bytes/modes, task, protected list, policy fingerprint, workspace and expiry into a digest.
- Apply requires that digest, an approver declaration and acceptance evidence. Reviews expire after one hour and cannot be applied twice.
- Original-file, draft or policy changes invalidate the reviewed proposal. Apply uses the stored reviewed bytes, not a fresh read of the draft during writes.
- Existing `govern` write policy is checked before application. Deletion is never performed by this pilot.
- Backups and status are persisted before writes. Successful apply and restore include byte/mode verification. Interrupted writes retain recovery state; `restore` can recover files already written.
- Restore refuses to overwrite newer edits. It is an explicit recovery of this task's original bytes, not a new policy-governed proposal. Missing files or unexpected contents require manual conflict resolution.

## Try it in PowerShell

Run from the repository root, using the current source:

```powershell
$env:PYTHONPATH = 'src'
python -m workspace_metabolism --root . change prepare --file src/workspace_metabolism/__init__.py --goal "Review a small documentation-only change" --acceptance "Only the intended docstring changes; no new execution path"
```

The JSON result contains an `id` and an absolute `draft` folder. Only edit files inside that draft. Do not apply an actual source modification until you have reviewed it. Use a disposable fixture for an initial roundtrip.

```powershell
python -m workspace_metabolism --root . change review CHANGE_ID
```

Read the returned diff and acceptance criteria. Independently inspect/test as appropriate; the pilot does not run tests for you. The digest identifies exact bytes, including whitespace and final newlines which a displayed diff may not make obvious. Review again after changing the draft; use the new digest.

```powershell
python -m workspace_metabolism --root . change apply CHANGE_ID --approve REVIEW_DIGEST --approver "local reviewer" --acceptance-evidence "Describe actual checks and their results here"
python -m workspace_metabolism --root . change restore CHANGE_ID
```

`CHANGE_ID` and `REVIEW_DIGEST` are placeholders for returned values. All steps return JSON on success; rejected input returns exit code 2. Global options must precede `change`. The default state folder is outside the workspace; an explicit `--state-dir` must also be separate. Backups and draft contents are retained locally and may contain sensitive data. No automatic retention/purge is added here.

## Reproducible initial checks

```powershell
$env:PYTHONPATH = 'src'
python -m pytest tests/test_changes.py -q
```

Tests use disposable temporary workspaces and no AI calls. Cases include normal review/apply/restore, protected deletion and editing, extra files, stale original/draft/policy, expiry, missing approval/evidence, policy denial, duplicate application, preservation of newer work, invalid paths and a simulated partial disk-write failure followed by recovery.

Passing these cases establishes bounded behavior, not lower supervision cost. Next compare this workflow with ordinary Git plus human review on the same frozen task. Record errors, false blocks, recovery correctness and total human minutes including configuration and review. Unnecessary second pipelines remain a manual/structural-test acceptance criterion.

## Limits and operating assumptions

Keep the original workspace idle during apply and restore. Locks serialize this pilot using the same state directory, not arbitrary editors, other state directories or processes. Check-then-write races remain possible; multi-file writes are not an atomic filesystem transaction. A hard crash can leave a stale lock and partial writes; inspect the process and manifest before manually clearing a stale lock, then restore. A journal-write error after file writes can also leave file state ahead of the journal; retain and inspect the manifest.

Anyone with write access to the state can alter manifests, approval declarations, backups and logs. Hashes are not signatures or identity authentication. The copy is not a sandbox: an AI with direct access to the original workspace can bypass this workflow. No external side effects, automatic semantic correctness, hostile-agent containment, durable transactional database or enterprise compliance guarantee is claimed.

This command is experimental and CLI-only. It intentionally does not expose approval/application as an MCP tool automatically available to the editing agent.
