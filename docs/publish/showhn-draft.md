# Show HN 发布草稿（v0.5 版，2026-09-02 更新）

> 用法：直接复制到 https://news.ycombinator.com/submit 提交（标题选一个，正文用下面的）。
> 叙事顺序：痛苦 → 30 秒上手 → 证据 → 诚实边界 → 开放式问题。

## 可选标题

1. **Show HN: workspace-metabolism – a policy file that governs what AI agents leave in your workspace (guided first run, reversible, 92/100 on Glama)**
2. **Show HN: I built a zero-dependency policy layer so Claude Code/Codex agents clean up after themselves – nothing is ever deleted by pattern**
3. **Show HN: workspace-metabolism – 30 seconds to your first audited agent-workspace cleanup (MCP + CLI)**

## 正文

Every AI coding agent shares one thing with you: the workspace. And they all
leave a trail behind – scratch files, caches, staged directories, logs. The
next run works in the garbage the last one left. Deleting by hand is
irreversible; scheduled scripts have no audit trail; nobody owns the cleanup.

`workspace-metabolism` is the **policy layer** for that: one JSON policy file
(`metabolism.json`) decides what every path is worth (G1 never touch →
G4 auto), and the tool only ever does what the policy allows:

- **Nothing is deleted by pattern.** Items move to a recycle area with
  per-file SHA-256 hashes; `rollback` restores them exactly.
- **Every action lands in a hash-chained journal.** `wm verify` detects any
  manual edit to the trail.
- **Agents can serve themselves**: `wm mcp` is a zero-dependency MCP stdio
  server (8 tools incl. policy pre-checks via `wm_govern`).

**First run is guided – no policy knowledge needed:**

```bash
pip install workspace-metabolism
wm doctor --residue                # what agent byproducts are NOT yet governed
wm doctor --residue --apply-policy # adopt them as policy entries (auto-creates the file)
wm audit                           # read-only checkup with a 0-100 health score
```

`doctor` only ever *suggests*; nothing is governed until you adopt it into the
policy. The policy stays the single source of truth.

**Evidence, since "early days" claims are cheap:** rated **Glama quality A
(92/100)** — above most *official* MCP servers (GitHub's own is C) — License A,
Maintenance A, Server Coherence A; published on PyPI; 120 tests green on
Windows/Linux/macOS; Python 3.11+, zero dependencies, MIT.

Repo: https://github.com/metabolism-tools/workspace-metabolism

**Honest boundaries:** this is governance, not a sandbox (a malicious agent
can bypass the MCP proxy – documented up front); it does not classify garbage
on its own; and there are no large production deployments yet — the schema may
shift before v1.0. I'd love feedback on the policy model (G1–G4 + approval
gates + protected windows) and on failure modes I haven't hit.

**Question for you:** do agent workspaces actually rot in practice for you —
and if so, is an audited, reversible policy layer the right shape for the fix?

## 提交建议

- 提交后 2 小时内回复所有评论（HN 排名吃互动）
- 如果评论区问"和 tmpreaper/trash-cli 区别"，答案要点：策略即代码 + 可回滚 + 哈希链审计 + MCP（观测层），不是又一个 deleter
- 被问 Glama 分数时给 https://glama.ai/mcp/servers/metabolism-tools/workspace-metabolism/score
