# Evaluate maintenance, not activity

Research question: Which retained evidence, isolation boundaries, and recovery conditions reduce necessary human takeovers while preserving downstream correctness?

## Choose a real opportunity

Use a naturally due maintenance event with an identifiable consumer. If investigating shared evidence specifically, establish another real use or cross-cycle dependency; do not impose that requirement on all maintenance. No eligible event means the trial has not started, not that a mechanism succeeded or failed.

State the mechanism being tested, such as preserving consumer-required provenance or blocking cleanup when a consumer contract has changed. Name an outcome that would refute its value.

## Make the comparison fair

Compare the mechanism against a competent ordinary script or existing workflow with the same permissions, backups, input, acceptance checks, and resource budget. Do not weaken the baseline to make WM look useful. Use isolated equivalent inputs or matched naturally occurring events; never destructively run two alternatives in sequence on the same production input.

Freeze input identity, acceptance conditions, versions, and the comparison procedure before examining results. Record differences that prevent a fair comparison. Use the actual consumer output, or a clearly labeled isolated replay with known limits. Fault injection belongs in isolated copies and is reported separately from natural incidents.

## Record separate outcomes

| Measure | Record | Interpretation |
| --- | --- | --- |
| Downstream correctness | Accepted outputs, failed checks, missing checks, and denominator | Missing acceptance is unknown, not success. |
| Recovery | Whether restored state passes the affected consumer; recovery duration | A rollback command succeeding is insufficient. |
| Human supervision | Measured checking/correction/rescue minutes, takeover events, and observation coverage | Keep intentional business decisions and creative work separate. |
| Supervision density | Supervision minutes per completed eligible cycle; takeovers per eligible cycle | Also report incomplete cycles and work complexity to avoid selection bias. |
| Time-based density | If useful, supervision minutes per 10 active agent-work hours | State concurrent-agent accounting; exclude idle waiting. Longer runtime can dilute this ratio without benefit. |
| Total cost | Compute/token usage, execution, retries, verification, recovery, and measured human effort | Missing usage or time remains unknown. Do not infer token savings from fewer messages. |
| Interruptions | Necessary and unnecessary alerts, missed escalations, unresolved incidents | Suppressed alerts alone are not reduced supervision. |

Record raw counts and time alongside ratios. Distinguish zero measured activity from unobserved activity. Keep failure and no-action cycles in the record; no-action is legitimate but not a completed maintenance benefit.

## State the conclusion conservatively

Supervision density falling while correctly measured downstream outcomes remain acceptable can be useful even if total human time or tokens do not fall. Check that work was not merely deferred, silently dropped, or transferred to someone else.

One successful event is a case, not evidence of general reliability. Report coverage, failure modes, uncertainty, and the safety limits of the tested scope. If the ordinary baseline is equally correct with comparable effort, say that the additional mechanism has not demonstrated value. Claim novelty, academic significance, or commercial advantage only with separate supporting evidence.
