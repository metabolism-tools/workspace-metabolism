---
name: metabolic-maintenance
description: "Evidence-aware maintenance for agent workflows: cleanup, retention, compaction, archival, and recovery of shared artifacts. Use when planning or carrying out workflow maintenance, investigating maintenance-related breakage, or evaluating whether maintenance reduces human supervision without damaging downstream work. Do not apply to unrelated coding tasks or use it to authorize business decisions. Works with ordinary scripts; WM integration is optional."
---

# Metabolic Maintenance

Maintain a workflow's ability to produce trustworthy results. Freed bytes, uninterrupted agent runtime, and fewer alerts are secondary observations; none proves that downstream work still works.

## Four working rules

1. **Maintain for a reason.** Identify a due retention rule, capacity constraint, broken dependency, or explicit user objective. If nothing qualifies, report no action. Do not manufacture an experiment by shortening retention, restarting paused work, or inventing consumers.
2. **Match autonomy to consequences.** Choose checks and isolation from what a wrong change could damage and how recovery works. Routine authorized, reversible maintenance can proceed with proportionate checks. Shared evidence, ambiguous consumers, or irreversible loss need stronger evidence or a narrower action. Confidence alone does not expand authority.
3. **Preserve the ability to check the result.** Before changing shared artifacts, identify their real consumers and acceptance conditions. Keep sufficient provenance and recovery material for those consumers. A file existing, a command exiting successfully, or a report saying `OK` is not business acceptance.
4. **Close the loop with evidence.** Verify relevant downstream outputs after maintenance. If recovery is needed, verify outputs again after restoring. Missing or failed checks leave the cycle unresolved. Fewer notifications do not establish fewer necessary human interventions.

## Carry out a maintenance cycle

Use existing project policies, permissions, and tooling. Keep the process proportional; a disposable cache and a shared research dataset do not need identical paperwork.

### Establish the boundary

- Inspect the actual target, why it qualifies, active writers/readers, and applicable retention rules. Distinguish observations from assumptions.
- Identify the smallest useful scope and who consumes it. For regenerable caches, establish the regeneration path; for shared evidence, identify the actual downstream workflow and its acceptance condition.
- When assessing recurring maintenance, establish what was due even if the worker left no record. Read [maintenance-observation.md](references/maintenance-observation.md) for missing runs, stale reports, deployment verification, or alert handling; finish with a bounded observation or an explicit coverage gap.
- Reuse authorization already given. This skill grants no permission, requires no extra blanket approval, and does not override project restrictions. If a consequential choice remains outside authorized scope, prepare a concrete preview and recovery proposal before requesting that specific decision.

### Prepare and execute

- Preview exact affected objects. Account for concurrent writes using existing locks, snapshots, or isolation; do not replay a stale preview against changed inputs.
- For recoverable changes, establish where recovery material lives, whether it covers the proposed scope, and when it expires. Avoid putting the only recovery copy inside the cleanup target.
- For shared or consequential changes, bind the evidence to the input/object identity, policy and tool version, consumer version, and observation time. Use hashes or immutable identifiers where available. Receipts and hashes establish traceability, not authenticity by themselves.
- Execute the smallest authorized action using available tools. Avoid building a new scheduler or control platform for a single maintenance task.

### Verify and retain the outcome

- Check storage integrity and the relevant consumer acceptance separately. Run the actual consumer safely when authorized; use an isolated replay if production execution would cause side effects. Label replay evidence as replay evidence.
- If a check fails, contain further dependent changes. Use the established recovery path within scope, then recheck the affected consumer. File restoration alone does not close the incident.
- Record the action, evidence locations, checks performed, unresolved gaps, and any human decision or rescue needed. Reuse the project's incident/task record across retries; silence or a new report must not erase an unresolved failure.
- Report a precise outcome: no action due, preview only, held for a named reason, changed and verified for the stated scope, recovered and verified, or unresolved. A successful local check cannot establish whole-system correctness.
- Keep execution, evidence freshness, consumer acceptance, and notification status separate. A manual run does not establish natural scheduling; a sent alert does not close the underlying failure.

## Optional WM integration

Inspect the installed `wm --help` and the relevant command help before choosing commands. Use its available previews, policy checks, receipts, and recovery support where they fit. Do not assume draft commands such as `wm change` exist in a released installation. WM decisions are not authenticated approval, and WM does not define a domain consumer's correctness.

In a WM source checkout that contains `tools/evaluate_maintenance_cycle.py`, that evaluator can associate supplied cycle evidence. It does not execute or authenticate checks and its reported-checks result is not permission to mutate data. Without WM, use the same rules with existing scripts and records.

## When evaluating the approach

Read [evaluation.md](references/evaluation.md) only when the task asks to measure supervision, compare approaches, or develop a research case. A controlled comparison is not a prerequisite for ordinary authorized maintenance.
