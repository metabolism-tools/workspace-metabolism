# Show HN 发布草稿

> 用法：直接复制到 https://news.ycombinator.com/submit 提交。
> 建议标题选一个最抓眼球的，正文用下面的。

## 可选标题

1. **Show HN: workspace-metabolism – one policy file that governs what AI agents leave behind in your workspace**
2. **Show HN: I built a policy layer so Claude Code/Codex agents clean up after themselves (zero deps, reversible)**
3. **Show HN: workspace-metabolism – file lifecycle management for multi-agent workspaces (MCP + CLI)**

## 正文

Most "cleanup" tools either show you disk usage or delete things. Agents
(Claude Code, Codex, OpenClaw, Aider…) leave a trail of scratch files, caches
and staged directories in your workspace, and the next run has to work in the
garbage they left behind. I wanted a policy layer instead of another deleter.

`workspace-metabolism` = one JSON policy file (`metabolism.json`) that decides
what every path is worth (G1 never touch / G2 keep / G3 approve / G4 auto):

- **Nothing is ever deleted by pattern.** Items move to a recycle area with
  per-file SHA-256 hashes; `rollback` restores them exactly.
- **Every action lands in a hash-chained journal.** `wm verify` detects any
  manual edit — the audit trail is tamper-evident.
- **Agents can serve themselves**: `wm mcp` is a zero-dependency MCP stdio
  server, so an agent can audit, explain and dry-run a clean plan, then execute
  with a human approval gate for the sensitive grades.
- Ships with a reproducible 30-loop benchmark (2 active files vs 242 leftover),
  Windows / Linux / macOS, Python 3.11+, zero dependencies.

```bash
pip install workspace-metabolism
wm init        # generate the policy file
wm audit       # read-only health check
wm clean --grades G4 --yes   # recycle expired items (dry-run by default)
wm rollback <run_id>         # exact, verified undo
```

Repo: https://github.com/metabolism-tools/workspace-metabolism

Honest status: early (v0.2), no external users yet, policy schema may shift
before v1.0. It's a proposal plus reference implementation — I'd love feedback
on the policy model (G1–G4 + protected windows + approval gates) and on
failure modes I haven't thought of. What do you use to keep agent workspaces
tidy today?

## 提交建议

- 用 Hacker News 的 URL 提交时填 repo 链接（GitHub 会自动展开成帖子）
- 提交后 2 小时内回复所有评论（HN 的排名算法吃这个）
- 不要用 `Ask HN`，用 `Show HN` 前缀
