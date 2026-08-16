# v0.2.0: give your agent workspace a metabolism

*Release announcement for workspace-metabolism v0.2.0. English, ~600 words.
Suitable for dev.to, a blog, or the Hacker News follow-up after Show HN.*

---

We released **workspace-metabolism v0.2.0** — a zero-dependency CLI that gives
an AI-driven workspace a digestion system instead of a funeral pyre.

The one-liner: **loops keep the agent running; metabolism keeps the workspace
alive.**

## Why this exists

Agent loops changed what a workspace looks like. Generate, error, fix, repeat
— every repetition leaves a trace: drafts, patches, lock files, test stubs,
half-finished refactors, abandoned approaches that were never deleted. AI
writes code like a fountain, and most workspaces have no drain.

The classic answers don't work. `rm -rf` burns intermediate matter a future
loop might need, along with its provenance. Git is too heavy for untracked,
high-churn byproducts. Cleaning every loop from a fresh sandbox throws away
the history that makes iteration possible.

## The proof: 2 vs 242

The repo ships a reproducible 30-loop experiment
(`examples/metabolism_benchmark.py`): two identical workspaces, each running
30 simulated agent loops that leave eight byproduct files behind.

After 30 loops, the governed workspace holds **2 active files and 0 expired
candidates**. The ungoverned one holds **242 files and 240 candidates**.

And every governed byproduct stays recoverable: rolling back the first loop's
draft restores it byte-for-byte in under a hundred milliseconds. Run it
yourself — the numbers are on the README, and the script ships in the repo.

## What's new in v0.2.0

- **`wm init`** — scaffold a `metabolism.json` policy file like `git init`.
  The tool scans your workspace and grades common directories: source and
  docs keep, logs/tmp/cache auto-recycle, archive/staging approve.
- **Policy auto-discovery** — `metabolism.json` / `.wm.json` in the workspace
  root are found automatically; `--registry` is optional. The format is
  versioned and covered by a JSON Schema.
- **`wm explain <path>`** — the nutrition label for any path: its grade,
  retention, whether it is a candidate right now, and why.
- **`wm health`** — a 0-100 workspace health score combining auditability,
  governance, rot burden and recycle readiness, with `--badge` output for a
  shields.io badge. A CI template (`examples/ci-audit.yml`) fails when the
  score drops below your threshold.
- **`wm mcp`** — a zero-dependency MCP stdio server so agents can run
  micro-metabolism themselves. Clean stays dry-run unless the caller
  explicitly passes `execute=true`.
- **The end-of-loop ritual** — `examples/micro_metabolism.py` asks the question
  every loop should answer: keep, archive, recycle, or leave for tomorrow's
  digestion.

The safety model is unchanged and remains the foundation: `clean` is dry-run
by default, G3 needs `--approve` + `--approver`, `rollback` verifies per-file
SHA-256 and refuses to overwrite, `purge` is the only real delete, and the
journal is a hash chain that detects tampering.

## The framing

We call this **Agentic Metabolic Engineering** — the fifth layer of the
agentic engineering stack, after Prompt, Context, Harness and Loop. Loop
engineering makes the agent keep running; metabolic engineering makes the
workspace survive the running. An honest disclaimer: the metaphor is not new
("information metabolism" dates to the 1960s; metabolic engineering belongs to
biology). We claim the framing, not the words.

## Get started

```bash
pip install workspace-metabolism
wm init
wm audit
wm health
```

- [README](https://github.com/metabolism-tools/workspace-metabolism#readme)
- [Narrative](https://github.com/metabolism-tools/workspace-metabolism/blob/main/docs/narrative.md)
- [Philosophy](https://github.com/metabolism-tools/workspace-metabolism/blob/main/docs/philosophy.md)
- [Roadmap](https://github.com/metabolism-tools/workspace-metabolism/blob/main/ROADMAP.md)
- [PyPI](https://pypi.org/project/workspace-metabolism/)
- [v0.2.0 release](https://github.com/metabolism-tools/workspace-metabolism/releases/tag/v0.2.0)

v0.2.0 is early days; the policy schema may shift before v1.0. Try it on a
throwaway workspace, then tell us what breaks. If your agent workspaces rot
faster than your code grows, that is not a cleaning problem — it is a missing
layer of the stack.
