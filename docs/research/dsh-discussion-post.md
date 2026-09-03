# DSH GitHub Discussion post — final text (posted)

> Posted: 2026-09-03 to https://github.com/deepseek-ai/deepseek-harness/discussions
> Category: `Show Your Plugins!` · Account: tongflau-dongzhu
> Status: FINAL — this file is the posted text, kept as a record.
> Follows the outreach discipline from `docs/research/outreach-log-2026-08-18.md`.

---

**Title:** workspace-metabolism — a policy layer for the files your agents leave behind (works with `dsh-mcp-client`, one `cordis.yml` row)

**Body:**

Hi! I built [workspace-metabolism](https://github.com/metabolism-tools/workspace-metabolism), a zero-dependency Python tool (v0.5.0, on PyPI), and it integrates with DeepSeek Harness through the official `@deepseek-ai/dsh-mcp-client` bridge — no code on either side.

The idea: agents (DSH, Claude Code, Codex, …) share one thing — the workspace — and all leave byproducts behind: logs, caches, scratch plugins, archived notes, "promote me" experiments. `workspace-metabolism` is a policy layer for that: one `metabolism.json` grades every path (G1 never / G2 keep / G3 approve / G4 auto), and the tool only ever does what the policy allows. Cleanup moves things to a recycle area with per-file SHA-256 hashes and a hash-chained journal, so everything is undoable and verifiable.

In a DSH session the agent gets eight tools:

- `wm_audit` — read-only workspace checkup
- `wm_health` — 0-100 workspace health score
- `wm_explain` — why a path is graded the way it is
- `wm_verify` — journal hash-chain integrity
- `wm_govern` — ask the policy *before* acting: is this read/write/execute/delete/network action on these paths allowed? deny-by-default, optional named human approver, decisions journaled
- `wm_clean` — policy-driven cleanup, dry-run unless `execute=true`
- `wm_init` — scaffold the policy file
- `wm_rollback` — SHA-256-verified restore from the recycle area

The whole integration is one `cordis.yml` row:

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

Full walkthrough: [docs/dsh-integration.md](https://github.com/metabolism-tools/workspace-metabolism/blob/main/docs/dsh-integration.md)

You can try it read-only in 30 seconds without touching your workspace:

```bash
pip install workspace-metabolism
wm init        # scaffolds metabolism.json (like git init)
wm audit       # read-only checkup
wm health      # 0-100 score
```

Status, honestly: v0.5.0, published on PyPI; policy schema may shift before v1.0. The repo carries the `dsh-plugin` topic; MCP tool definitions currently rate 92/100 (grade A) on [Glama](https://glama.ai/mcp/servers/metabolism-tools/workspace-metabolism).

I'm sharing it because "everything is a plugin" makes DSH a natural home for a workspace governance layer — and I'd like to know whether other people find a *workspace health score* useful as a signal across long sessions, or whether the more interesting direction is a session-end hook that audits automatically (`wm_govern` already gives an agent the ask-before-acting half of that loop).

Thanks for reading!
