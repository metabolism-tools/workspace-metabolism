## workspace-metabolism v0.2.1

One policy file controls the whole lifecycle of files in your multi-agent
workspace: classify, audit, clean (recyclable), rollback, and purge — every
step leaves a hash-chained audit trail. Python 3.11+, zero dependencies,
Windows / Linux / macOS.

The one-liner: **loops keep the agent running; metabolism keeps the workspace
alive.**

### What's new in v0.2.1

- **Memory-backed awareness in `wm audit`**: on systems where a workspace
  location sits on tmpfs/ramfs (e.g. `/tmp` on modern Linux), the audit now
  says so — residue there costs **RAM, not just disk**. The report gains a
  `memory` section (workspace mount, memory-resident candidates and their
  size), the summary gains `memory_candidates` / `workspace_on_memory`, the
  journal records the count, and both the report and CLI print a hint when
  it matters. Degrades to a no-op where no memory-backed mounts are visible
  (Windows, macOS).
- **The demo now shows the difference**: `python examples/demo.py` contrasts
  the usual blind-delete fix (a file gone in place, no record, no undo) with
  the wm way — `clean` moves expired items to the recycle area, `rollback`
  restores them after a per-file SHA-256 check, `verify` confirms the journal
  chain. Deterministic 5-item comparison, all inside throwaway temp dirs.
- **Positioning page**: new `docs/positioning.md` — "What
  workspace-metabolism is not": not a fix for vendor bugs, not a heuristic
  classifier, not a rival to agent self-cleanup, not a blind-delete script.
  It exists because a public review on
  [anthropics/claude-code#8856](https://github.com/anthropics/claude-code/issues/8856)
  tested the project's first outreach comment; the four objections are
  answered in order there. The README gained a matching "What this is not"
  section.
- **One-liner refresh**: the project now introduces itself as the **policy
  layer for multi-agent workspaces** — Claude Code, Codex, Aider and OpenClaw
  all leave byproducts in the one thing they share: your workspace. Launch
  drafts and announcement copy were updated to match.

### What's unchanged

- Safety model: `clean` is dry-run by default; G3 needs `--approve` +
  `--approver`; `rollback` verifies per-file SHA-256 and refuses to overwrite;
  `purge` is the only real delete, retention-gated and recycle-area-only.
- Zero dependencies; CI on Ubuntu / Windows / macOS (Python 3.11 & 3.12).
- The policy schema is still versioned and may shift before v1.0.

Install: `pip install workspace-metabolism`

Docs: [README](https://github.com/metabolism-tools/workspace-metabolism#readme) ·
[positioning](https://github.com/metabolism-tools/workspace-metabolism/blob/main/docs/positioning.md) ·
[philosophy](https://github.com/metabolism-tools/workspace-metabolism/blob/main/docs/philosophy.md) ·
[narrative](https://github.com/metabolism-tools/workspace-metabolism/blob/main/docs/narrative.md)
