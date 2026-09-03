# Reddit 发布草稿（v0.5 版，2026-09-02 更新）

> 发布到 r/MCP（最对口）、r/ClaudeAI、r/LocalLLaMA（先看版规，部分板块要求 10:1 参与比例）。
> 叙事顺序：具体痛点 → 30 秒上手 → 可回滚/审计卖点 → 证据 → 开放问题。

## r/MCP 版本（标题 + 正文）

**标题：** Agents keep trashing my workspace, so I built a policy layer that lets them clean up after themselves — reversible, audited, zero-dependency

**正文：**

Every agent I run (Claude Code, Codex, DSH…) shares my workspace and leaves a
trail: scratch files, caches, staged dirs, logs. Nobody owns the cleanup —
deleting by hand is irreversible, cron scripts have no audit trail, and the
next agent run works in the garbage the last one left.

So I built a **policy layer** instead of another deleter:

- One JSON policy file (`metabolism.json`) decides what every path is worth
  (G1 never touch → G4 auto). The tool only ever does what the policy allows.
- Nothing is deleted by pattern — items move to a recycle area with per-file
  SHA-256 hashes, `rollback` restores them exactly.
- Every action lands in a **hash-chained journal**; `wm verify` catches any
  tampering with the trail.
- Agents can govern themselves via MCP (`wm mcp`, 8 tools incl. policy
  pre-checks) — audited, dry-run-first, human approval for sensitive grades.

**First run is guided — no policy knowledge needed:**

```bash
pip install workspace-metabolism
wm doctor --residue                # what agent byproducts are not yet governed
wm doctor --residue --apply-policy # adopt them into the policy (auto-creates the file)
wm audit                           # read-only checkup + 0-100 health score
```

`doctor` only *suggests* — nothing is governed until you adopt it. The policy
stays the single source of truth.

Repo: https://github.com/metabolism-tools/workspace-metabolism
(MIT · Python 3.11+ · zero dependencies · Win/macOS/Linux · **Glama quality A,
92/100** — for reference, GitHub's own MCP server sits at C)

Honest bits: it's not a sandbox (documented), there are no big production
deployments yet, and the schema may shift before v1.0. The policy model
(G1–G4 + approval gates + protected windows + hash-chained journal) is what I
most want feedback on. Do agent workspaces rot for you too — and is an
audited, reversible policy layer the right shape for the fix?

## 备选板块

- **r/ClaudeAI** — 面向 Claude Code 用户（留痕问题对口；先看自推规则）
- **r/opensource** — 通用开源推广
- **r/LocalLLaMA** — 需要 10:1 参与比例，先满足再发

## 通用建议

- 评论区积极回复，比帖子本身更重要
- 附 README 里的 demo GIF 链接
- 标题用第一人称 + 具体痛点，别用 "Introducing..."
- 被问分数/证据时给 Glama 评分页链接
