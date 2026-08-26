Following up on your review earlier today — it was acted on, and the changes shipped as [v0.2.1](https://github.com/metabolism-tools/workspace-metabolism/releases/tag/v0.2.1):

1. **Your tmpfs point is now a first-class audit dimension.** `wm audit` detects memory-backed mounts and reports residue there as a RAM cost, not just disk — the 22-byte-cwd-files-are-memory point, made visible instead of argued.
2. **The "guesswork" objection has a public answer.** A new page, ["What workspace-metabolism is not"](https://github.com/metabolism-tools/workspace-metabolism/blob/main/docs/positioning.md), takes your four objections in order — including the SessionEnd blind-delete accident class and why recycle + rollback avoids it by construction.
3. **The demo now shows the difference instead of claiming it.** `python examples/demo.py` contrasts a blind `rm` (gone, no record, no undo) with the wm way (clean → recycle → rollback → verify) in about 30 seconds.

To be clear, nothing about my position changed: this is still not a fix for Claude Code — the scratchpad/system-prompt/close-hook work remains Anthropic's to do, and I'd still rather see that land than see anyone depend on this tool. If you have a minute, the positioning page is the part I'd value your read on most; it exists because of your comment.
