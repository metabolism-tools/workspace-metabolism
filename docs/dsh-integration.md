# DeepSeek Harness integration

[DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (DSH) is an
agent harness where *everything is a plugin*, built on the
[Cordis](https://github.com/cordiverse/cordis) plugin framework. Its official
channel for third-party tools is MCP, and `wm mcp` already speaks it — so
workspace-metabolism integrates with DSH **with zero code on either side**: one
`cordis.yml` row is the whole integration.

What the DSH agent gets: `wm_audit`, `wm_health`, `wm_explain`, `wm_verify`,
`wm_clean` (dry-run by default), `wm_init`, and `wm_rollback` — the same
policy-driven lifecycle as the CLI, now callable mid-session by the agent
itself.

## Prerequisites

```bash
pip install workspace-metabolism   # puts `wm` on PATH
```

## Option A — permanent project config

Add this row to your DSH project's `cordis.yml`
(a copy lives in [examples/dsh/wm.cordis.yml](../examples/dsh/wm.cordis.yml)):

```yaml
- insert:
    - id: workspace-metabolism
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: wm
        transport: stdio
        command: wm
        args: [mcp]
        cwd: !!js process.cwd()
```

## Option B — try it without touching config

```bash
pnpm dsh web --patch ./examples/dsh/wm.cordis.yml
```

The `--patch` overlay keeps your existing composition untouched; remove the
flag and the integration is gone.

## Pinning the workspace and state

`wm` governs the directory the DSH process is launched from by default
(`process.cwd()`), which is right for most projects. To govern a different
workspace, or to keep the journal/recycle area somewhere specific, remember
that `wm` global flags come **before** the subcommand:

```yaml
        command: wm
        args: [--root, /absolute/path/to/workspace, --state-dir, /absolute/path/to/state, mcp]
```

The default state directory lives outside the workspace on purpose, so
`git add .` can never sweep the audit journal into version control.

## Tool reference

| MCP tool | Model-facing name | What it does |
| --- | --- | --- |
| `wm_audit` | `mcp__wm__wm_audit` | Read-only checkup: candidates, unregistered paths, disk alerts, duplicates, sensitive files |
| `wm_health` | `mcp__wm__wm_health` | Workspace health score 0–100 with component breakdown |
| `wm_explain` | `mcp__wm__wm_explain` | Why a path is graded the way it is (the nutrition label) |
| `wm_verify` | `mcp__wm__wm_verify` | Journal hash-chain and run-manifest integrity check |
| `wm_clean` | `mcp__wm__wm_clean` | Policy-driven cleanup plan; **dry-run unless `execute=true`** |
| `wm_init` | `mcp__wm__wm_init` | Scaffold `metabolism.json` for a workspace with safe defaults (like `git init`) |
| `wm_rollback` | `mcp__wm__wm_rollback` | Restore a previous `wm_clean` run from the recycle area, SHA-256 verified; **dry-run unless `execute=true`** |

## Safety model (inherited unchanged)

- `wm_clean` plans by default; execution requires `execute=true`.
- G4 needs `--yes`-equivalent (`execute=true`); G3 additionally needs
  `approve=true` **and** an `approver` (audit trail).
- Sensitive files (`.env*`, `*.pem`, `*.key`, `*token*`, …) are never
  auto-cleaned; git-tracked files count as controlled by git and are skipped.
- Nothing is deleted directly: items move to a recycle area with per-file
  SHA-256 hashes, and `wm rollback` restores them. `purge` is the only real
  delete, and only inside the recycle area.
- Every action lands in a hash-chained journal; `wm_verify` detects edits.

## A policy tuned for DSH workspaces

Self-evolving agents leave specific byproducts: decision notes
(`.agents/notes/`), local plugin experiments (`scratch-plugin/`), generated
catalogs and build output. [examples/registry.dsh.example.json](../examples/registry.dsh.example.json)
is a ready-made policy for that shape — copy it to your workspace as
`metabolism.json` and adjust.

## What this is not

- This is the **MCP path**: the wm engine stays a Python subprocess; DSH only
  talks to it over stdio. A native Cordis plugin (in-process tools, session-end
  hooks, `tools/pre-execute` policy interception) is a possible next step, but
  the MCP bridge covers the capability today with nothing to maintain.
- It is not a fix for DSH bugs — it governs the workspace, which is the one
  thing every agent shares.
