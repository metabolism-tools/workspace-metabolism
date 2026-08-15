## workspace-metabolism v0.1.2

One policy file controls the whole lifecycle of files in an AI-driven
workspace: classify, audit, clean (recyclable), rollback, and purge — every
step leaves a hash-chained audit trail. Python 3.11+, zero dependencies,
Windows / Linux / macOS.

The one-liner: **loops keep the agent running; metabolism keeps the workspace
alive.**

### What's new in v0.1.2

- **Complete narrative.** "Agentic Metabolic Engineering" is now framed as
  the fifth layer of the agentic engineering stack, with a one-liner, a
  three-act story (can write → keeps writing → writes without rotting), and a
  named human role (policy author). See
  [docs/narrative.md](https://github.com/metabolism-tools/workspace-metabolism/blob/main/docs/narrative.md).
- **Reproducible proof.** `examples/metabolism_benchmark.py` simulates 30
  agent loops in two identical workspaces (governed vs ungoverned) and prints
  the numbers quoted in the narrative: after 30 loops, the governed workspace
  holds 2 active files and 0 expired candidates; the ungoverned one holds 242
  files and 240 expired candidates, and every governed byproduct is
  recoverable via `wm rollback`.
- **Reliability fix.** `audit` and `clean` run IDs now include microseconds.
  Previously, two runs started in the same second produced the same run ID;
  the second run could overwrite the first run's manifest, silently orphaning
  the first recycle batch. This matters exactly for the narrative's
  micro-metabolism scenario: an agent running `clean` at the end of every
  loop. Regression tests added.
- **Copy in Chinese and English.** Updated launch draft, Zhihu article, X
  post, and GitHub announcement with the one-liner and the three-act story.

### What's unchanged

- Safety model: `clean` is dry-run by default; G3 needs `--approve` +
  `--approver`; `rollback` verifies per-file SHA-256 and refuses to overwrite;
  `purge` is the only real delete, retention-gated and recycle-area-only.
- Policy grades G1–G4 in one JSON file; nothing happens the policy doesn't
  allow.
- Zero dependencies; CI on Ubuntu / Windows / macOS (Python 3.11 & 3.12).

It's early days (v0.1.x), so the policy schema might have minor tweaks before
v1.0. Issues and PRs are welcome.
