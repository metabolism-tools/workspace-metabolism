# X（Twitter）英文发布文案

发帖时间建议：周二 21:00–24:00（北京时间），即美东上午 9:00–12:00。

## 方式 A：主帖 + 3 条跟帖（推荐）

**主帖：**

> AI writes code faster than we can clean up after it.
>
> Loops keep the agent running; metabolism keeps the workspace alive.
>
> I built a zero-dep CLI that treats a workspace like a living system: audit → recycle → verify → rollback. One JSON policy file decides what every path is worth (G1–G4).
>
> Clean never deletes. Rollback is an exact undo.
>
> github.com/metabolism-tools/workspace-metabolism

**跟帖 1：**

> The classic answer to a messy workspace is a cron script that calls `rm -rf`. That's autophagy — it burns intermediate matter the next agent loop might need.
>
> So `clean` moves expired files to a recycle area and records a SHA-256 for each one. `rollback` is an exact, verified undo.

**跟帖 2：**

> Every action lands in a hash-chained journal, and `wm verify` detects any tampering. `purge` is the only real delete — after retention, inside the recycle area only.
>
> Policy as code: one JSON file grades every path G1 (never) / G2 (keep) / G3 (approve) / G4 (auto). Nothing happens that the policy doesn't allow.

**跟帖 3：**

> I call the framing Agentic Metabolic Engineering — the L5 layer of the agentic stack: what happens to byproducts after each loop. Proposing a framework, not coining a word.
>
> Philosophy + narrative docs live in the repo. Python 3.11+, zero deps, CI on Ubuntu/Windows/macOS.
>
> pip install workspace-metabolism

## 方式 B：合并成 1 条

> AI writes code faster than we can clean up after it. Loops keep the agent running; metabolism keeps the workspace alive. I built workspace-metabolism: a zero-dep CLI where one policy file grades every path (G1–G4); clean moves files to a recycle area (never rm -rf), rollback is exact, and every move lands in a hash-chained journal. I call the framing Agentic Metabolic Engineering — L5 of the agentic stack.
>
> github.com/metabolism-tools/workspace-metabolism

## 小提示

- 每条帖子建议控制在 280 字以内（链接按 23 字计算）；如果超了，先删「zero-dep」或「G1–G4」这类修饰。
- 可以加话题：#Python #OpenSource #DevTools #AI
- 发布后立刻在自己主页确认帖子完整、链接可点。
