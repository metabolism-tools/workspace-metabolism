# Reddit 发布草稿

> 发布到 r/MCP（最对口）和 r/LocalLLaMA（推广贴需要先看版规，有些板块要求
> 10:1 参与比例）。发布前看下各版 sidebar 规则。

## r/MCP 版本（标题 + 正文）

**标题：** I built an MCP server that lets agents clean up their own workspace — policy-driven, reversible, zero-dependency

**正文：**

I got tired of agent workspaces filling up with scratch files: Claude Code
leaves `/tmp` cwd tracking, OpenClaw stages directories, codex drops `Q*.tmp`
files, and nobody owns the cleanup. So I built a "policy layer" instead of
another deleter:

- One JSON policy file (`metabolism.json`) grades every path G1–G4
- `wm mcp` = zero-dependency Python MCP stdio server: agents can audit,
  explain, and dry-run clean plans themselves
- Nothing is ever deleted by pattern — files move to a recycle area with
  per-file SHA-256 hashes, `rollback` restores them exactly
- Every action lands in a hash-chained journal; `wm verify` catches tampering
- Sensitive grades need human approval (`approve` + `approver`), and a
  protected window option keeps trading/business hours untouched

```bash
pip install workspace-metabolism
wm init
wm mcp   # talk to it from Claude Code / Cursor / any MCP client
```

Repo: https://github.com/metabolism-tools/workspace-metabolism
(MIT, Python 3.11+, zero dependencies, Win/macOS/Linux)

It's early-stage (v0.2) — the policy model (G1–G4, approval gates, protected
windows, hash-chained journal) is the thing I most want feedback on. What do
you use to keep agent workspaces tidy? Does your agent framework already do
this and I reinvented it? 😅

## 备选板块

- **r/ClaudeAI** — 面向 Claude Code 用户（留痕问题对口）
- **r/opensource** — 通用开源推广
- **r/Python** — 需要先看版规（自推内容通常要满足参与要求）

## 通用建议

- 评论区积极回复，比帖子本身更重要
- 附上 demo GIF 链接（README 里有）
- 标题用第一人称 + 具体痛点，别用 "Introducing..."
