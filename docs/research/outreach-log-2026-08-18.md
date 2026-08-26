# 触达日志：2026-08-18 第一轮

> 记录保存在本地（`docs/research/` 未被 git 跟踪），不提交公开仓库。

## 本轮动作

| 线索 | Issue | 作者 | 触达方式 | 评论链接 | 状态 |
| --- | --- | --- | --- | --- | --- |
| Claude Code 临时文件泄漏 | [anthropics/claude-code#8856](https://github.com/anthropics/claude-code/issues/8856) | `Sundeepg98` | Issue 公开评论 | [issuecomment-5327516999](https://github.com/anthropics/claude-code/issues/8856#issuecomment-5327516999) | 已发布；收到第三方回复并已回应 |
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

## 追加：2026-08-18 互动记录（#8856）

**第三方回复**（非目标作者）：[@alexanderadam](https://github.com/alexanderadam) 在
[issuecomment-5327788815](https://github.com/anthropics/claude-code/issues/8856#issuecomment-5327788815)
（11:53 UTC）引用我评论的首句并反驳，核心论点：

1. 该问题本质上是 Anthropic/Claude Code 的 4 个上游问题组合（引用其
   [issuecomment-5007625792](https://github.com/anthropics/claude-code/issues/8856#issuecomment-5007625792)）：
   系统提示词指示 scratchpad 放 `/tmp/claude-<uid>/`（tmpfs = RAM）；提示词缺清理指令；
   缺关闭钩子；官方文档 SessionEnd 示例路径错误且有误删风险。
2. 批评我的工具："靠规则猜测什么可以删"，不解决根因；若 agent 能自清理则外部层无必要。

**我的回应**：[issuecomment-5329150957](https://github.com/anthropics/claude-code/issues/8856#issuecomment-5329150957)
（草稿 `outreach-reply-cc-8856-alexanderadam.md`）：
认账根因全在上游并接住 tmpfs/RAM 论点（22 字节文件在 tmpfs 上也是占内存）；
澄清"猜测"误解（显式策略文件 + 只读 audit + 默认 dry-run + 回收区 + 回滚，非启发式）；
承认其第 2、3 点是正确终局，工具只是到那时为止的补丁层；
指出盲删 `rm -rf /tmp/claude-*` 正是其 SessionEnd 警告的同类事故，回收区设计按构造避免；
结尾问 Anthropic 是否对系统提示词问题有回应。已回读核验。

**观察记录**：

- 目标作者 `Sundeepg98` 尚未回复；首个实质回应来自第三方深度技术评论者，属有效反馈。
- 该回复验证了两个判断：外部治理工具在此话题圈会被严格审视；定位必须诚实（补丁层而非修复）。
- 产品启示（暂不行动，记入候选）："策略驱动 vs 猜测"的区分需在 README/演示中更前置；
  `/tmp` = tmpfs 场景（占内存而非占磁盘）可作为 audit 报告的一个新信号维度。

## 追加：2026-08-18 产品启示已全部落地

四项启发全部实现（详见 docs/positioning.md 的 Provenance 一节）：

- **P0 定位文档**：新增 `docs/positioning.md`（"What workspace-metabolism is not"，
  四个"不是"+ 边界 + 一段话版本 + 本次交锋出处）；README 新增 "What this is not"
  小节并链接定位页。
- **P1 audit 的 tmpfs/RAM 感知**：`core.py` 新增 `parse_mounts` /
  `memory_backed_mounts` / `memory_backed_info`（Linux 读 /proc/self/mounts，
  Windows/macOS 无 tmpfs 时自动降级为空）；audit 报告新增 `memory` 段与
  summary 的 `memory_candidates` / `workspace_on_memory`，journal 记录
  memory_candidates，报告与 CLI 输出新增"RAM 而非磁盘"提示。测试 +5（含跨平台
  最长前缀匹配与 monkeypatch 集成测试），全量 **79 passed**（Windows 本机验证）。
- **P1 demo 对照演示**：`examples/demo.py` 重写——先演示盲删（文件永久消失、
  无记录），再演示 wm 方式（clean 回收 5 项 → rollback 全部还原 → verify 链完好），
  记分牌对比；已端到端运行验证。
- **P2 对外定位**：launch-draft（Show HN / r/Python 开场）、github-announcement、
  release-announcement-v0.2.0 均改为"多 agent 工作区的策略层"一句话；线上置顶公告
  （discussions/3）开头一句已通过 GraphQL 实际更新并回读验证。

**遗留说明**：沙箱环境下 pytest 的 tmp_path 需要完整文件权限才能运行（沙箱拦截
python 自建目录的枚举）；后续在 CI（Linux/macOS）不受影响。

**版本**：v0.2.0 已于 PyPI/GitHub 发布（tag v0.2.0 存在），上述新功能属于 v0.2.0
之后的工作，已升级为 **v0.2.1**（`__init__.py` + `pyproject.toml`），发布说明草稿
`docs/publish/release-notes-v0.2.1.md`，README 状态行同步。

## 追加：2026-08-18 收尾回复（#8856）

v0.2.1 发布后给 @alexanderadam 发了收尾回复
[issuecomment-5330063223](https://github.com/anthropics/claude-code/issues/8856#issuecomment-5330063223)
（草稿 `outreach-followup-cc-8856-alexanderadam.md`），内容：
1. 他的 tmpfs 论点已成为 audit 的一等维度（内存挂载检测，占 RAM 而非磁盘）；
2. "猜测"质疑有了公开回答页（docs/positioning.md，按他的四点逐条回应）；
3. demo 改为 30 秒内可见的"盲删 vs 回收+回滚"对照。
同时重申立场不变（仍不是对 Claude Code 的修复，上游该修什么还是什么），并请他
审阅定位页。已回读核验。截至 2026-08-18 15:03 UTC，该 Issue 上 @alexanderadam
尚未再次回复，`Sundeepg98` 与 #104358 的 `danilovmy` 均未回复。

## 追加：2026-08-19 第二轮搜索（openai/codex 方向）

按用户要求做了第二轮只读搜索（未发任何评论），重点核实次级候选与新增线索：

| 线索 | 状态 | 匹配度 | 结论 |
| --- | --- | --- | --- |
| [openai/codex#37225](https://github.com/openai/codex/issues/37225) Windows 下 Codex 在工作目录留下 Q*.tmp（100+ 在项目根、7000+ 在 %TEMP%） | open；作者做了对照实验；修复卡在 fork PR（LIghtJUNction/codex#1），上游未合并 | **高** | 工作目录残留 = 我们的核心场景；修复在途未落地，语境有效。草稿已写：`outreach-comment-codex-37225.md` |
| [openai/codex#36428](https://github.com/openai/codex/issues/36428) 退出时清理 /tmp 临时文件（feature request） | open（08-10 最后更新） | 中 | 生命周期修复请求，与 #37225 相关联；不作为触达目标 |
| [openai/codex#39332](https://github.com/openai/codex/issues/39332) marketplace 升级泄漏 ~/.codex/.tmp（26 GB / 234 目录） | open（08-19 创建） | 中 | 状态目录残留而非工作区；量级惊人，列入观察 |
| [anthropics/claude-code#87677](https://github.com/anthropics/claude-code/issues/87677) ~/.claude.json.tmp 原子写残留 | open（08-18 创建） | 中 | 同仓库已有 #8856 对话，短时间内再发一条有「连发」观感；建议等 #8856 收尾后再评估 |
| Aider / Cursor | 无匹配残留类 issue（Aider 的 cache issue 均为 token 计费） | 低 | 不触达 |

**决策点**：是否现在向 #37225 发布草稿评论（草稿口径与第一轮一致：承认 fork 修复是正确终局、定位为外部治理视角、只提供只读路径、结尾开放问题）。

**已发布**：2026-08-19 10:55 UTC，[issuecomment-5341119313](https://github.com/openai/codex/issues/37225#issuecomment-5341119313)，已回读核验（与草稿逐字一致）。观察指标：作者 freedally 是否回复、上游是否合入 fork 修复、是否有人跑 demo。

## 下一步（待回复后）

- 回复出现时：一对一跟进，给临时目录试用指引（demo 已覆盖），不转向推销。
- 若 7 天无回复：不催促；记录后转入次级候选评估或停止该线索。

## 追加：分发轮（2026-08-26）

诊断：产品改进 ≠ 关注；0 star / 0 反馈，HN 上 0 条记录（Show HN 从未发过）。已执行：

- **仓库描述改尖锐**（GitHub 搜索/列表页首印象）：改为 "Govern what Claude Code, Codex, Aider and OpenClaw leave in your workspace: one JSON policy file, audit, recyclable clean, rollback, hash-chained audit trail."
- **awesome-mcp-servers PR**：[punkpeye/awesome-mcp-servers#12939](https://github.com/punkpeye/awesome-mcp-servers/pull/12939)（Developer Tools 分类，`wm mcp` 条目，含 glama badge；待维护者合入/回复）
- **发布文案终稿**：docs/publish/launch-bundle-v0.2.1.md（Show HN 标题 A/B + 正文、r/Python、X 线程 3 条、发布检查清单；痛点先行，30 秒 demo 锚点）
- **demo 反馈 CTA**：examples/demo.py 结尾新增 "issues & stars welcome" 指向；80 passed
- **工作区恢复**：本地工作区被清空（仅剩 docs 两份草稿），已从 origin 克隆恢复至 5d79c33，未丢失任何远端内容

待用户操作：按 launch-bundle 在美东周二至周四上午发 Show HN / r/Python / X；PyPI 0.2.1 上传（本机无凭据）。
