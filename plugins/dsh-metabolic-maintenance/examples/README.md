# A maintenance cycle with an actual downstream check

This runnable example uses WM's real MCP request handler and real file operations in new temporary directories. The downstream consumer reads JSON and computes a total. A Python script follows the illustrated procedure; it does **not** call a DSH model or test whether a model follows the skill. It also does not exercise the DSH-to-MCP transport, which is a separate integration boundary.

## Run it

With Python 3.11 or newer, in an environment where you want to install WM:

```sh
python -m pip install workspace-metabolism==0.5.1
python /path/to/package/examples/maintenance_cycle.py
```

Or install WM from this repository and run the same file from `plugins/dsh-metabolic-maintenance/examples/maintenance_cycle.py`.

Version check on 2026-09-11: PyPI provides WM **0.5.1**; **0.5.2** is a GitHub release, not an available PyPI version. This example was also run successfully using the actual PyPI 0.5.1 wheel in a fresh environment.

The script accepts no production workspace path. It creates a fresh temporary workspace, state directory, and evidence file for each scenario. It leaves them in place for inspection. No purge or permanent data deletion is invoked.

## Follow the roles through the cycle

| Step | What a skill-guided agent should establish | What runs in this example |
| --- | --- | --- |
| 1. Need | A real rule makes a scratch report due; being idle is not a reason | A synthetic 45-day-old report and a 30-day retention policy; `wm_audit` finds one candidate |
| 2. Boundary | Inputs and acceptance evidence are outside cleanup scope; recovery state is separate | Protected `inputs/values.json`, evidence beside the workspace, and a sibling WM state directory |
| 3. Preview | Inspect the exact proposed maintenance within existing authorization | `wm_clean({grades: "G4"})`; the example checks that the report still exists |
| 4. Acceptance | Know what the affected consumer must produce before acting | Read `[7, 11]`, compute 18, and preserve input/policy/consumer identity plus the baseline output |
| 5. Execution | Perform only the agreed operation | `wm_clean({grades: "G4", execute: true})` moves the scratch directory to WM's recycle area |
| 6. Verification | Check the actual downstream result independently of tool success | Run the file-reading consumer again and require total 18 |
| 7. Recovery | On failure, restore within scope and rerun acceptance | In the negative fixture, `wm_rollback` previews then restores; the consumer must again produce 18 and the input hash must match |

WM does not infer that “18” is the correct answer. That condition belongs to the example's downstream workflow. The skill describes how an agent should organize these checks; it does not enforce their execution.

## Expected results

[View the captured terminal session](terminal-session.txt). It records an actual scripted run on 2026-09-11 with PyPI WM 0.5.1; only the temporary evidence directory is replaced with a placeholder. It is a synthetic fixture run, not a recording of an autonomous DSH session.

```text
normal: maintained_consumer_verified
fault_injection: fault_recovered_consumer_verified
missing_consumer: held_missing_consumer
```

**Normal:** the downstream workflow reads protected input, so removing an expired scratch copy leaves the result at 18.

**Fault injection:** the consumer is deliberately made dependent on the cleanup target. The script intentionally bypasses this known warning in an isolated fixture to show failure and recovery. A skill-following agent should instead stop or narrow the operation when it identifies that dependency. Successful rollback is accepted only after the real consumer works again; this recovery demonstration is not permission to test destructive changes in production.

**Missing consumer:** audit and preview can proceed, but the example has no supplied consumer acceptance contract. It holds before cleanup and records unknown results. This is not a maintenance success and not a universal rule that every disposable cache needs a bespoke consumer.

Each `evidence.json` contains the actual WM calls and responses and available consumer results. These files include temporary local paths; sanitize them before public sharing. `before.json` preserves pre-action acceptance evidence. Baseline evidence and recovery material are outside the cleanup target.

## Observe maintenance that never completes

The source development version also includes a separate standard-library example:

```sh
python /path/to/package/examples/maintenance_observation.py
```

This example requires Python 3.11+ but no installed WM. It creates and removes only its own temporary fixture. JSON is printed to the terminal; [observation-session.json](observation-session.json) is an actual captured run with fixed synthetic January timestamps, not production history.

| Scenario | Actual fixture operation | Expected interpretation |
| --- | --- | --- |
| Startup failure | An isolated Python subprocess fails to import before producing any receipt | An independently supplied due slot still exposes missing completion evidence |
| Stale report | A real file remains unchanged and its hash matches, but the supplied evidence window has expired | Report exists; current health is unknown |
| Notification retry | An in-memory sender deliberately fails once, then succeeds; a third call is suppressed | Failed sends remain retryable; successful send does not resolve the incident |
| Incomplete recovery | Input bytes are restored, but a changed calculation rule remains; the real consumer returns 36 instead of 18 | File recovery passes; consumer acceptance fails |
| Normal no change | Current supplied receipt plus a real consumer returning 18 | No change can be legitimate; reclaimed bytes are zero |
| Not due / before enrollment | Explicit replay times with no receipt | Not yet due and uninstrumented history are separate from missing post-enrollment evidence |

The small `evaluate_obligation` function is an illustrative read-only association of supplied slot/receipt fields. It does not read scheduler registrations, verify hashes, authenticate receipts, inspect production artifacts, execute recovery or enforce permissions. Artifact and consumer checks in the scenarios are separate real fixture operations. All receipt timestamps and trigger labels are supplied replay data; natural scheduling remains unverified. The in-memory sender is not a delivery integration, persistent queue, restart-safe deduplicator or retry daemon.

Use [maintenance-observation.md](../skills/metabolic-maintenance/references/maintenance-observation.md) for adapter responsibilities and the [observation record](../skills/metabolic-maintenance/references/observation-record.md) for real cases. Those relative references are included by the plugin build. Existing `tools/evaluate_maintenance_cycle.py` states and WM CLI behavior are unchanged by this example.

## What this proves—and what it does not

The example makes the difference between tool completion and downstream acceptance observable, and demonstrates WM cleanup and recovery with small synthetic data. It provides no natural maintenance opportunity, autonomous-model result, ordinary-script comparison, or measured reduction in human supervision or tokens. Human time and token savings remain unknown. Those claims require separate real-workflow trials under the [evaluation guide](https://github.com/metabolism-tools/workspace-metabolism/blob/main/skills/metabolic-maintenance/references/evaluation.md).
