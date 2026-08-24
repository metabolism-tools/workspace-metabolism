# X（Twitter）英文发布文案（v0.2.0 最终版）

> 发布前：发帖时间建议北京时间周二 21:00–24:00（= 美东上午 9:00–12:00）。
> 每条帖子控制在 280 字以内（链接按 23 字计算）；发布后立刻在主页确认链接可点。

## 配图（英文版，供 X 使用）

- `images/four-phases-en.png`：四阶段主图
- `images/stack-l5-en.png`：Agentic 工程栈 L5
- `images/experiment-30-en.png`：30 轮对照实验数据卡
- `images/scheduled-vs-metabolism-en.png`：定时清理与代谢系统对比（可选）

## 方式 A：主帖 + 3 条跟帖（推荐）

**主帖：**

> AI writes code like a fountain. Most workspaces have no drain.
>
> Loops keep the agent running; metabolism keeps the workspace alive.
>
> I built workspace-metabolism v0.2.0: one policy file (G1–G4), recyclable clean, exact rollback, hash-chained audit.
>
> https://github.com/metabolism-tools/workspace-metabolism

**跟帖 1：**

> The classic answer to a messy workspace is a cron script that calls `rm -rf`. That's autophagy — it burns intermediate matter the next agent loop might need.
>
> So `clean` never deletes. It moves expired files to a recycle area, records a SHA-256 per file, and `rollback` is an exact, verified undo.

**跟帖 2：**

> Every action lands in a hash-chained journal; `wm verify` detects tampering. `purge` is the only real delete — after retention, inside the recycle area only.
>
> Policy as code: G1 never / G2 keep / G3 approve + reference check / G4 auto. Nothing happens the policy doesn't allow.

**跟帖 3：**

> The framing: Agentic Metabolic Engineering — L5 of the agentic stack. Third act: can the workspace survive the writing?
>
> Proof: 30 loops → governed: 2 files, ungoverned: 242. Every byproduct recoverable.
>
> pip install workspace-metabolism · https://pypi.org/project/workspace-metabolism

**跟帖 4：**

> "Isn't this just a scheduled cleanup?" A scheduler answers when. The policy file answers what, how, and how to undo it.
>
> They compose: cron / Task Scheduler / CI templates run `wm` on a schedule. Alarm clock + digestive system.

## 方式 B：合并成 1 条

> AI writes code like a fountain. Loops keep the agent running; metabolism keeps the workspace alive. I built workspace-metabolism: one policy file, recyclable clean, exact rollback, hash-chained audit. Agentic Metabolic Engineering, L5.
>
> https://github.com/metabolism-tools/workspace-metabolism

## 小提示

- 如果某条超了字数，先删「v0.2.0」「G1–G4」这类修饰。
- 可以加话题：#Python #OpenSource #DevTools #AI
- 主帖也可以直接指向 Release：https://github.com/metabolism-tools/workspace-metabolism/releases/tag/v0.2.0
