# 发布文案终稿 v0.2.1（2026-08-24 定稿）

> 使用说明：Show HN 周二至周四美东 09:00–12:00 发（= 北京 21:00–24:00）。
> r/Python 同窗口；X 主帖+跟帖发布后立即自查链接。
> 文案原则：先具体痛点、再 30 秒试用、最后才讲机制。标题不用抽象词。

---

## 一、Show HN（Hacker News）

**推荐标题 A**

Show HN: One JSON file governs what Claude Code, Codex, Aider and OpenClaw leave in your workspace

**备选标题 B**

Show HN: My /tmp fills with claude-*-cwd files, so I built a recyclable cleaner with exact rollback (Python, zero deps)

**正文（贴在首个评论）**

Claude Code leaves ~174 files/day in /tmp on some systems. OpenClaw leaves empty staged dirs. Codex and Aider cache things in odd places. All of them work in the same workspace, and none of them clean up after themselves.

So I built the layer that governs what they leave behind: [workspace-metabolism](https://github.com/metabolism-tools/workspace-metabolism) — one JSON policy file decides what every path is worth (G1 never / G2 keep / G3 approve / G4 auto), and the tool only does what the policy allows.

The part people don't believe until they see it: **nothing is ever deleted by pattern**. Expired items move to a recycle area with per-file SHA-256 hashes; `wm rollback` restores them integrity-checked; `purge` is the only real delete, inside the recycle area only, after retention. Every action lands in a hash-chained journal and `wm verify` detects any edit.

Try it in 30 seconds (throwaway temp dirs, nothing touches your machine):

```bash
pip install workspace-metabolism
git clone https://github.com/metabolism-tools/workspace-metabolism
cd workspace-metabolism
python examples/demo.py   # blind delete vs recycle+rollback, side by side
```

The demo literally shows the difference: a blind `rm` removes a file with no record and no undo; `wm clean` moves the same kind of item to a recycle area, and `rollback` puts it back byte-for-byte.

The proof that governed workspaces stay flat: a reproducible 30-loop benchmark ships in the repo — one workspace ends every loop with `wm clean`, the other never cleans. Result: **2 active files vs 242**, and every governed byproduct stays recoverable.

New in v0.2.1: `wm audit` now detects residue on memory-backed mounts (on systems where /tmp is tmpfs, leftover files cost RAM, not just disk) — the insight came from a review on the Claude Code issue tracker, and the [positioning page](https://github.com/metabolism-tools/workspace-metabolism/blob/main/docs/positioning.md) answers the four objections raised there.

Python 3.11+, zero dependencies, Windows / Linux / macOS. It's early days (v0.2.1): I'm looking for people to break it on weird directory structures. What would you need before trusting it with real files?

Links: [repo](https://github.com/metabolism-tools/workspace-metabolism) · [README](https://github.com/metabolism-tools/workspace-metabolism#readme) · [PyPI](https://pypi.org/project/workspace-metabolism/) · [v0.2.1 release](https://github.com/metabolism-tools/workspace-metabolism/releases/tag/v0.2.1)

---

## 二、r/Python

**标题**

Show /r/Python: a "safe delete" CLI for AI workspaces — policy file, recycle area, exact rollback, hash-chained audit (zero deps)

**正文**

TL;DR: agent workspaces (Claude Code, Codex, Aider, OpenClaw) accumulate byproducts with no policy and no undo. I built a zero-dependency Python CLI where one JSON file decides what each path is worth, and cleanup is never a direct delete:

- 📋 **Policy as code**: `metabolism.json` grades paths G1–G4; unregistered paths are never touched
- ♻️ **Recyclable clean**: expired items move to a recycle area, dry-run by default
- ⏪ **Exact rollback**: per-file SHA-256, refuses to overwrite anything that reappeared
- 🔗 **Hash-chained journal**: `wm verify` detects any tampering
- 🧠 **`wm explain <path>`**: shows the exact rule and why (no "AI judgment" anywhere)
- ⏰ **Schedulable + agent-runnable**: cron/Task Scheduler templates; `wm mcp` lets agents audit and dry-run themselves

The demo contrasts a blind `rm` with the wm way in 30 seconds: `python examples/demo.py`. The repo ships a reproducible 30-loop benchmark — **2 active files vs 242**.

New in v0.2.1: audit reports residue on memory-backed mounts (tmpfs = RAM, not just disk).

Pure stdlib, tests on Ubuntu/Windows/macOS (3.11/3.12). Early days, schema may shift before v1.0 — what would you add before trusting it with real files?

Repo: https://github.com/metabolism-tools/workspace-metabolism

---

## 三、X（Twitter）线程

**主帖**

> Claude Code leaves ~174 files a day in /tmp. OpenClaw leaves empty staged dirs. Agents don't clean up after themselves — so I built the layer that governs what they leave behind.
>
> workspace-metabolism: one JSON policy file, recyclable clean, exact rollback, hash-chained audit. Zero deps.
>
> https://github.com/metabolism-tools/workspace-metabolism

**跟帖 1（机制）**

> The part people don't believe: nothing is ever deleted by pattern. Items move to a recycle area (per-file SHA-256); `wm rollback` restores them; `purge` is the only real delete, retention-gated, recycle-area-only.
>
> 30-second demo: python examples/demo.py — blind rm vs recycle+rollback, side by side.

**跟帖 2（证明）**

> Reproducible benchmark ships in the repo: 30 agent loops, one workspace governed, one not → 2 active files vs 242. Every governed byproduct stays recoverable.
>
> New in v0.2.1: audit now flags residue on memory-backed mounts (on tmpfs systems it's RAM, not just disk).

**跟帖 3（定位）**

> Not a fix for Claude Code's /tmp leak (that's Anthropic's to fix) — it's the policy layer for whatever your agents leave in the one thing they share: your workspace.
>
> pip install workspace-metabolism · https://pypi.org/project/workspace-metabolism

---

## 发布检查清单

- [ ] Show HN 发布时间窗口：周二至周四美东 09:00–12:00
- [ ] 主帖评论区贴正文（标题就是链接）
- [ ] HN 发完 1 小时内答复所有评论，主动问"你遇到的最怪的工作区残留是什么"
- [ ] r/Python 同窗口发
- [ ] X 主帖+3 跟帖，发布后自查链接可点
- [ ] 有人在评论里试用后，把反馈记入 docs/research/outreach-log（本地）
