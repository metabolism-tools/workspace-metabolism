# GitHub 发布（release 说明 + 讨论区公告）

GitHub 上的 v0.1.0 和 v0.1.1 已经发布，这里补两件事：把 release 说明写完整，再开一个置顶公告，作为英文内容的「长文主页」。

## 一、更新 v0.1.1 的 release 说明

网页操作：

1. 打开 https://github.com/metabolism-tools/workspace-metabolism/releases/tag/v0.1.1
2. 点右上角「Edit」（铅笔图标）
3. 把正文替换成下面的英文，点「Update release」

**正文（英文，直接粘贴）：**

> ## workspace-metabolism v0.1.1
>
> One policy file controls the whole lifecycle of files in an AI-driven workspace: classify, audit, clean (recyclable), rollback, and purge — every step leaves a hash-chained audit trail. Python 3.11+, zero dependencies, Windows / Linux / macOS.
>
> What's in v0.1.1:
>
> - `wm audit --json` summary block: growth, recycle ratio, journal chain, governance (the measurement ritual in docs/narrative.md)
> - Policy grades G1–G4; `clean` is dry-run by default; G3 needs `--approve` + `--approver`
> - Rollback with per-file SHA-256; `purge` is the only real delete, retention-gated, recycle area only
> - Scheduling templates for cron and Windows Task Scheduler
>
> Install: `pip install workspace-metabolism`
> Docs: [philosophy.md](https://github.com/metabolism-tools/workspace-metabolism/blob/main/docs/philosophy.md) (framing) · [narrative.md](https://github.com/metabolism-tools/workspace-metabolism/blob/main/docs/narrative.md) (story) · [README](https://github.com/metabolism-tools/workspace-metabolism#readme)
>
> It's early days (v0.1), so the policy schema might have minor tweaks before v1.0. Issues and PRs are welcome.

## 二、打开 Discussions（讨论区）

网页操作：

1. 打开 https://github.com/metabolism-tools/workspace-metabolism/settings/general
2. 往下找到 Features，勾选 **Discussions**，点 Save
3. 回到仓库主页，顶部会出现 **Discussions** 标签

（如果你不想自己点，我可以用命令行帮你开。）

## 三、发置顶公告

网页操作：

1. 打开仓库主页，点 **Discussions** 标签
2. 点 **New discussion**
3. Category 选 **Announcements**
4. Title 填：`Introducing workspace-metabolism — file lifecycle as a living system`
5. 正文粘贴下面的英文，点 **Start discussion**
6. 发布后点正文右下角 **…** → **Pin discussion**（置顶）

**正文（英文，直接粘贴）：**

> `workspace-metabolism` is a zero-dependency CLI (Python 3.11+) that manages the lifecycle of files in an AI-driven workspace from a single policy file.
>
> **The problem:** vibe coding and agentic loops leave behind drafts, caches, failed attempts, and half-finished refactors — faster than the code grows. The classic answer is a cron script that calls `rm -rf`, which can burn intermediate matter a future loop needs. Pure git is too heavy for untracked, high-churn byproducts.
>
> **The approach:** treat the workspace as a living system — audit (catabolism) → clean (sequestration, never delete) → verify (hash-chained journal) → rollback (anabolism). One JSON policy grades every path G1–G4, and nothing happens that the policy doesn't allow.
>
> We propose **Agentic Metabolic Engineering** as a framing — the L5 layer of the agentic stack, the last mile of every loop. This is a proposal, not a claim of coining the words: "information metabolism" dates to the 1960s, and "metabolic engineering" belongs to synthetic biology.
>
> - [README](https://github.com/metabolism-tools/workspace-metabolism#readme)
> - [Philosophy](https://github.com/metabolism-tools/workspace-metabolism/blob/main/docs/philosophy.md)
> - [Narrative](https://github.com/metabolism-tools/workspace-metabolism/blob/main/docs/narrative.md)
> - [PyPI](https://pypi.org/project/workspace-metabolism/)
>
> v0.1.1 is early days; the policy schema may shift before v1.0. We'd love early adopters to break it on weird directory structures.
