## workspace-metabolism v0.2.0

One policy file controls the whole lifecycle of files in an AI-driven
workspace: classify, audit, clean (recyclable), rollback, and purge — every
step leaves a hash-chained audit trail. Python 3.11+, zero dependencies,
Windows / Linux / macOS.

The one-liner: **loops keep the agent running; metabolism keeps the workspace
alive.**

### What's new in v0.2.0

- **`wm init`**: scaffold a `metabolism.json` policy file like `git init`.
  The tool scans your workspace and grades common directories (source/docs
  keep, logs/tmp/cache auto, archive/staging approve).
- **Auto-discovery**: `metabolism.json` / `.wm.json` in the workspace root are
  found automatically, so `--registry` is optional.
- **Policy JSON Schema** in `schema/metabolism.schema.json`; new optional
  governance fields: `owner`, `intent`, `review_after`.
- **`wm explain <path>`**: the nutrition label for any path — what grade,
  what retention, whether it is a candidate right now, and why.
- **`wm health`**: a 0-100 workspace health score (auditability 25,
  governance 25, rot burden 35, recycle readiness 15) with `--json` and
  `--badge` (shields.io) output.
- **`wm mcp`**: a zero-dependency MCP stdio server so agents can run
  micro-metabolism themselves. Clean stays dry-run unless the caller
  explicitly passes `execute=true`.
- **Ritual and CI**: `examples/micro_metabolism.py` (the end-of-loop
  question) and `examples/ci-audit.yml` (a weekly health gate that fails
  below a configurable score).
- **Community**: ROADMAP, CONTRIBUTING, issue templates, an English essay
  (`docs/publish/agentic-metabolic-engineering-essay.md`) and a stack diagram
  in the narrative.

### What's unchanged

- Safety model: `clean` is dry-run by default; G3 needs `--approve` +
  `--approver`; `rollback` verifies per-file SHA-256 and refuses to overwrite;
  `purge` is the only real delete, retention-gated and recycle-area-only.
- Zero dependencies; CI on Ubuntu / Windows / macOS (Python 3.11 & 3.12).

Install: `pip install workspace-metabolism`

Docs: [README](https://github.com/metabolism-tools/workspace-metabolism#readme) ·
[philosophy](https://github.com/metabolism-tools/workspace-metabolism/blob/main/docs/philosophy.md) ·
[narrative](https://github.com/metabolism-tools/workspace-metabolism/blob/main/docs/narrative.md)
