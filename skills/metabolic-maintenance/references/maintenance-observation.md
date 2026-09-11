# Observe maintenance itself

Use this procedure when recurring maintenance is missing, its report may be stale, or its deployed entrypoint or notifications need verification. For a one-off disposable cache, use the ordinary maintenance cycle instead.

## Establish an obligation before looking for success

Use the existing scheduler or workflow contract to identify the action, eligible window, completion deadline including grace, and expected executor/version. Record when observation began. Keep this expectation outside the worker: a worker that cannot import its dependencies cannot report its own failure.

An obligation is an expectation to check or maintain, not permission to delete. A due audit can correctly find no eligible changes. Record explicit cancellations or authorized holds with reasons; do not silently remove them from the denominator.

If a required receipt is absent after the deadline, report **missing completion evidence**, not a proven non-execution or a guessed root cause. Missing historical receipts before observation was installed are **uninstrumented history**. Neither is success. Preserve independent historical failure evidence if it exists.

## Read separate dimensions

These are reporting terms, not new WM CLI commands or a replacement for existing evaluator states.

| Dimension | What to record | What it establishes |
| --- | --- | --- |
| Obligation | Not due, within window, completed, completed late, failed, missing evidence, or unknown | Coverage of a particular expected slot; late repair retains the missed deadline |
| Execution | Not observed, preview, no change, changed, failed; attempt and executor identity | What the entrypoint reports doing; no change is not reclaimed space |
| Evidence | Missing, mismatched, expired, or checked for a named scope/time | Which inputs, versions and outputs the observation can support |
| Consumer | Not checked, accepted, or rejected, with the acceptance condition and actual output | Whether the affected downstream work meets its contract |
| Recovery | Not assessed, not needed, attempted, files restored, or consumer reverified | Files restored is not the same as downstream recovery |
| Trigger | Manual, scheduler-observed, or unknown, plus source evidence | An `auto` argument alone cannot distinguish a manual scheduler start from a natural trigger |
| Notification | Not observed, not required, pending, failed, sent, or acknowledged | Sender-reported sent is not delivery/read confirmation or incident resolution |

Bind receipts to the expected action/slot, execution identity, policy/tool/consumer versions and applicable time window. Check the actual artifact against its receipt before presenting it as current. Hashes alone neither authenticate a source nor establish business correctness. Keep an old report available as history with its age visible; do not show it as current health.

If a consumer is genuinely inapplicable, name the narrower acceptance condition (for example, safe cache regeneration) and its evidence. Do not fabricate a business consumer to obtain a green result.

## Verify the deployed route

1. Inspect the actual task action, executable, arguments, working directory, environment assumptions and persistent data location. Compare with the tested release; copied scripts can outlive a deployment.
2. Reproduce import/startup faults from that route in an isolated fixture or through a safe read-only command. Record exit results and artifact checks independently.
3. Keep manual acceptance separate from the next natural scheduled trigger. Observe without moving retention deadlines or running cleanup merely to fill evidence gaps.
4. Reuse an existing observer with its own entrypoint. State its cadence, offline behavior, failure domain and how its own failure is detected. If observer coverage is unknown, expose that gap rather than promising continuous detection.

## Preserve unresolved incidents across notifications

Reuse the existing incident identity across retries. A useful deduplication key includes the obligation slot and meaningful failure state; an unchanged weekly incident should not become a new incident each day. A changed failure or a new due slot must remain visible.

Suppress only according to the existing successful-send policy. Failed sends remain pending for bounded retry/escalation under that policy. Record attempt failures and the eventual send separately. Honor existing authorization for external messages. Recovery requires fresh relevant checks, not notification success. Never send a synthetic production alert to prove a test.

Reuse existing protected evidence storage. Keep bounded latest status for display and preserve incident history according to policy; overwriting the latest receipt does not preserve attempt history. Define size/retention limits and protect recovery evidence from its own cleanup rule.

## Finish with a checkable result

Record the expected slot, observation coverage, separate outcomes, evidence locations, unresolved gaps and next naturally due verification. Use the [observation record](observation-record.md) for a case or comparison; routine runs can reuse existing receipts. Adapter code owns scheduling, data checks and authorized alert delivery. This skill supplies instructions, not those runtime services.
