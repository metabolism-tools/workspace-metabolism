# A maintenance cycle with an actual downstream check

This runnable example uses WM's real MCP request handler and real file operations in new temporary directories. The downstream consumer reads JSON and computes a total. A Python script follows the illustrated procedure; it does **not** call a DSH model or test whether a model follows the skill. It also does not exercise the DSH-to-MCP transport, which is a separate integration boundary.

## Run it

With Python 3.11 or newer, in an environment where you want to install WM:

```sh
python -m pip install workspace-metabolism==0.5.2
python /path/to/package/examples/maintenance_cycle.py
```

Or install WM from this repository and run the same file from `plugins/dsh-metabolic-maintenance/examples/maintenance_cycle.py`.

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

```text
normal: maintained_consumer_verified
fault_injection: fault_recovered_consumer_verified
missing_consumer: held_missing_consumer
```

**Normal:** the downstream workflow reads protected input, so removing an expired scratch copy leaves the result at 18.

**Fault injection:** the consumer is deliberately made dependent on the cleanup target. The script intentionally bypasses this known warning in an isolated fixture to show failure and recovery. A skill-following agent should instead stop or narrow the operation when it identifies that dependency. Successful rollback is accepted only after the real consumer works again; this recovery demonstration is not permission to test destructive changes in production.

**Missing consumer:** audit and preview can proceed, but the example has no supplied consumer acceptance contract. It holds before cleanup and records unknown results. This is not a maintenance success and not a universal rule that every disposable cache needs a bespoke consumer.

Each `evidence.json` contains the actual WM calls and responses and available consumer results. These files include temporary local paths; sanitize them before public sharing. `before.json` preserves pre-action acceptance evidence. Baseline evidence and recovery material are outside the cleanup target.

## What this proves—and what it does not

The example makes the difference between tool completion and downstream acceptance observable, and demonstrates WM cleanup and recovery with small synthetic data. It provides no natural maintenance opportunity, autonomous-model result, ordinary-script comparison, or measured reduction in human supervision or tokens. Human time and token savings remain unknown. Those claims require separate real-workflow trials under the [evaluation guide](https://github.com/metabolism-tools/workspace-metabolism/blob/main/skills/metabolic-maintenance/references/evaluation.md).
