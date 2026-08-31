# Draft: DSH GitHub Discussion post

> Status: draft — review before posting. Follows the outreach discipline from
> `docs/research/outreach-log-2026-08-18.md`: honest status, read-only demo
> path, no hype, no asking for anything, one open question at the end.
>
> Target: https://github.com/deepseek-ai/deepseek-harness/discussions
> Topic suggestion: `Show and tell` / `Ecosystem`.

---

## Title: workspace-metabolism — a policy layer for the files your agents leave behind (MCP, works with dsh-mcp-client)

Hi! I built a small zero-dependency Python tool called
[workspace-metabolism](https://github.com/metabolism-tools/workspace-metabolism)
and it turns out it integrates with DeepSeek Harness through the official
`@deepseek-ai/dsh-mcp-client` bridge — no code on either side.

The idea: agents (DSH, Claude Code, Codex, …) all share one thing — the
workspace — and they all leave byproducts behind: logs, caches, scratch
plugins, archived notes, "promote me" experiments. `workspace-metabolism` is a
policy layer for that: one `metabolism.json` file grades every path
(G1 never / G2 keep / G3 approve / G4 auto), and the tool only ever does what
the policy allows. Cleanup moves things to a recycle area with per-file
SHA-256 hashes and a hash-chained journal, so everything is undoable and
verifiable.

In a DSH session, the agent gets seven tools: `wm_audit` (read-only checkup),
`wm_health` (0-100 score), `wm_explain` (why a path is graded as it is),
`wm_verify` (journal integrity), `wm_init` (scaffold the policy file),
`wm_rollback` (SHA-256-verified restore from the recycle area), and
`wm_clean` (dry-run by default; execution still requires the policy's
approval gates).

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

You can try it read-only in 30 seconds without touching your workspace:

```bash
pip install workspace-metabolism
wm init        # scaffolds metabolism.json (like git init)
wm audit       # read-only checkup
wm health      # 0-100 score
```

Status, honestly: v0.2.3, no external users yet, policy schema may shift
before v1.0 — but the MCP server now scores 92/100 (grade A) on
[Glama's tool-definition-quality evaluation](https://glama.ai/mcp/servers/metabolism-tools/workspace-metabolism/score).
I'm sharing it because the "everything is a plugin" philosophy
makes DSH a natural home for a governance layer, and I'd like to know whether
other people find a *workspace health score* a useful signal across long
sessions — or whether the more interesting direction is a session-end hook
that audits automatically.

Thanks for reading!
