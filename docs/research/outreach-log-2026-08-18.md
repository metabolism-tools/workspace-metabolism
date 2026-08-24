# 触达日志：2026-08-18 第一轮

> 记录保存在本地（`docs/research/` 未被 git 跟踪），不提交公开仓库。

## 本轮动作

| 线索 | Issue | 作者 | 触达方式 | 评论链接 | 状态 |
| --- | --- | --- | --- | --- | --- |
| Claude Code 临时文件泄漏 | [anthropics/claude-code#8856](https://github.com/anthropics/claude-code/issues/8856) | `Sundeepg98` | Issue 公开评论 | [issuecomment-5327516999](https://github.com/anthropics/claude-code/issues/8856#issuecomment-5327516999) | 已发布，待回复 |
| OpenClaw 残留目录 | [openclaw/openclaw#104358](https://github.com/openclaw/openclaw/issues/104358) | `danilovmy` | Issue 公开评论 | [issuecomment-5327518256](https://github.com/openclaw/openclaw/issues/104358#issuecomment-5327518256) | 已发布，待回复 |

发布账号：`tongflau-dongzhu`（2026-08-18 11:29 UTC）。草稿见
`outreach-comment-cc-8856.md`、`outreach-comment-oc-104358.md`，发布后已回读核验，内容完整无乱码。

## 评论策略执行情况

- **#8856**：明确声明"这不是对 Claude Code 的修复"；承认线程内已有插件式缓解 PR；
  只提供 30 秒一次性 demo 与只读 `audit` 路径；结尾问开放式问题（audit→recycle→rollback
  是否比纯清理脚本更有用），不索取任何东西。
- **#104358**：开头先承认 open PR #117184 与 bot 审查是在途的正确方向；把自己的工具定位为
  "外部治理视角"而非替代品；同样只提供只读试用路径；结尾询问保留规则/来源/回滚是否值得
  外部治理层。该 Issue 今天有 clawsweeper bot 正在重审（lease 至 10:15 UTC），评论未干扰其流程。

## 遵守的约束

- 只触达前两个高匹配候选，未私信、未批量联系。
- 次级候选（openai/codex#25319、Aider PR #2911）本轮不接触。
- 评论中无宣传话术，未宣称项目解决任何上游缺陷；如实说明 v0.2、零外部用户、策略 schema 可能变化。

## 观察指标（后续轮次核对）

1. 作者或其他用户是否回复、是否询问细节。
2. 是否有人实际运行 `python examples/demo.py` 或只读 `audit`（无法直接观测，看是否反馈报错/截图）。
3. 反馈中出现的真实需求：一次性清理、定时治理，还是集成 Agent 工作流。
4. #8856 上游是否出现官方修复、#104358 的 PR #117184 是否合入——影响后续跟进话术。

## 下一步（待回复后）

- 回复出现时：一对一跟进，给临时目录试用指引（demo 已覆盖），不转向推销。
- 若 7 天无回复：不催促；记录后转入次级候选评估或停止该线索。
