# 统一行动方案（2026-09-02 收敛版）

> 合并全部线索：产品计划（product-plan.md）、批判/路线图档案（01-03）、求职提案（04）、
> 会话内已完成工作。原则：**不重复已做的工作；按"收尾→面试包→下一批→backlog"分层；**
> 副业节奏 ≤10h/周，双项目共用。

## 0. 防重复清单（这些已做完，别再做）
- ❌ 引导式首次运行（新手体验）→ **已实现**：`wm doctor --residue --apply-policy`（50b04a8，120 测试）
- ❌ 策略建议能力 → 同上（建议→用户确认→policy，哲学未破）
- ❌ gate 本身 / decision_id / tool_patterns / schema 支持 → v0.4.0 已发布
- ❌ gov 端到端家族链 → gov-demo 绿/红路径已实测跑通
- ❌ gov TDQS 描述重写（4 工具 A 档 4.7/5）→ 785bfc1
- ❌ gov Glama 三件套 + mcp<2 锁版 + PyPI 0.4.0 + GitHub release v0.4.0 + tag
- ❌ wm Glama 92 A / README 徽章 / holdout README 徽章
- ❌ DSH 集成 + 讨论帖 + 自进化评论 + ROADMAP 落档
- ❌ 组织改名 holdout-labs 全量同步 + profile README（含钉选指引）
- ❌ 乱码/BOM 全量清查
- ❌ 产品计划（docs/publish/product-plan.md）+ 策略档案 01-04

## A. 收尾层（多数只需一个动作/发布）
| # | 事项 | 负责人 | 备注 |
|---|---|---|---|
| A1 | **wm v0.5.0 发布**（doctor 引导主打；pyproject+__init__ 同步 0.5.0 → 构建 → PyPI → GitHub release） | 我 | 同步更新：ROADMAP 加 v0.5.0 shipped；product-plan 勾选 #2；release-notes-v0.5.0.md |
| A2 | **Show HN + Reddit 发布**（草稿更新为 v0.5 doctor 体验） | 我写/你发 | 可选：中文平台（知乎/小红书/X）文案同步 |
| A3 | **Glama Sync**：wm（8 工具重评）+ gov（TDQS 新分同步）；验证 gov "quality B" 缓存归位 + related servers 刷新（改名后） | ✅ 已完成 2026-09-02 | 双项目实测 AAA（Coherence/TDQS/Maintenance 全 A；wm 4.6、gov 4.7） |
| A4 | **holdout-labs 主页钉选 6 仓库**（按 flow 顺序） | 你（浏览器） | 指引已在 profile README |
| A5 | **PyPI token 轮换**：删聊天里出现过的账户级 token，重生成存文件 | 你 | 安全项 |
| A6 | **PR 跟进**：#12939（awesome-mcp-servers）/ #292（vibe-coding）/**awesome-quant #593 已合并（08-29）→ 补一个链接修正小 PR**（README 里 foolproof-labs → holdout-labs，顺带作为"外部落地证据"写进叙事） | 我查/你定 | #593 是已合并的外部收录，叙事可用 |
| A7 | gov "Try in Browser" 几次（usage 信号，91→92 级） | 你（浏览器） | 顺手 |
| A8 | **Glama Discord 加入**（领 server-author flair；申诉 quality B 缓存） | 你（可选） | 与 A3 联动 |

## B. 面试/叙事半小时包（wm，纯收尾）
| # | 事项 | 工作量 | 说明 |
|---|---|---|---|
| B1 | README 状态行**改写**（不删诚实，更新为事实：v0.4→v0.5、Glama A、已发布；去掉陈旧 "no external users yet" 措辞）+ **边界声明前置**（沙箱/分类器/不修 Agent bug） | 30min | 求职提案 2+9 的修正版 |
| B2 | `wm gate` 启动警告 + `--help` 首屏边界声明 | 30min | 求职提案 1 |
| B3 | 60 秒 demo 录屏：doctor --residue → apply-policy → audit 前后对比 | 1h | 面试最强资产 |
| B4 | **README 叙事重排（痛苦→工具→哲学）**：开篇痛点/灾难场景（Agent 工作区被塞满、误删、无审计）→ 30 秒上手（doctor）→ 能力 → 哲学下移到 Why/Philosophy 章节；**gate 措辞全仓统一为"观测探针/治理审计层"**（README、--help、启动横幅一致，不出现"安全网关"暗示）；中文快速上手区同步 | 1-2h | 冷启动七层拆解 + 路线图"叙事顺序固定"（01/02 档案一致结论） |
| B5 | **事实数字核对单**：简历/叙事用数字必须准确——wm **120** 测试 / gov **100+** 测试（不是 94）；双 Glama **92**（A 档）；工具数 wm 8 / gov 4；双 PyPI 0.4.x；awesome-quant 已收录 | 15min | 求职提案 4 的"94 个测试"数字不实，防错 |

## C. 下一批（holdout 产品化收尾 + wm 测试加固）
| # | 事项 | 工作量 | 说明 |
|---|---|---|---|
| C1 | gov `audit_pipeline()` 一行 API（内部复用 engine.run_check/report，输出 markdown 汇总） | 0.5-1 天 | 求职提案 3 |
| C2 | gov examples 端到端（模拟数据，5 分钟跑通；gov-demo 基础上做干净入口） | 0.5-1 天 | 求职提案 10 |
| C3 | gov test extra 依赖修复（numpy 等进 [test]）；**并核验 PyPI 0.4.0 是否含 785bfc1 的 TDQS 参数描述**（不含 → 补发 0.4.1） | 30min | 现状：装了 numpy 才能收集测试 |
| C4 | wm 可移植边缘测试（只读目录/超长名/编码怪名/空目录）；**符号链接测试只在 Linux job，Windows 不做** | 0.5-1 天 | 求职提案 4 的修正版；性能测试仅冒烟级 |
| C5 | **ADR×3**（从 backlog 提级）：gate=观测探针定位 / doctor 建议转 policy 而非硬编码 / journal 用 JSONL 哈希链的取舍 | 0.5-1 天 | 面试"为什么这么设计"弹药库 |
| C6 | **wm presets**：`wm init --preset python-dev / jupyter-lab / ai-agent-sandbox / node-npm / data-pipeline`（`examples/presets/` 目录，非新仓库；CI 跑 policy lint 校验） | 0.5-1 天 | "上手即用"窄面第 1 项（从 D 提级）；与 A1 的 doctor 引导互补 |
| C7 | **`wm audit --html`** 静态报告导出（单文件无依赖；unregistered 聚合/冲突告警/回收站占用/建议规则） | 0.5-1 天 | "上手即用"窄面第 2 项（从 D 提级）；同时是面试 demo 资产 |
| C8 | **doctor 首跑"下一步"引导增强**：apply-policy 后提示可用 preset 与 `audit --html`（存在时）；现状已提示 NEXT 行，属小收尾 | 30min | "上手即用"窄面第 3 项；解决"跑完不知道干嘛" |

## D. Backlog（有真实信号再动，防超前建设）
- wm `policy lint`（冲突/贪婪 glob/不可达）——批判 P1-1，等有用户策略样本再定优先级
- wm `health --metrics` / 增量扫描
- 其他 MCP 目录提交：Smithery / PulseMCP / mcp.so / MCPFind（等 v0.5 发布后一次做完，几分钟/个）
- holdout quickstart 独立仓库 / pit-adjuster-benchmark / 《回测陷阱百科》/ L1-L2 分级
- 复杂策略自动分类（不做——保持"非启发式分类器"定位）
- ❌ 明确不做（防超前建设）：桌面应用/常驻 GUI/安装器生态（brew/choco/apt/docker 全家桶）/大型交互式向导工程——"一键部署"只做 C6-C8 窄面

## "上手即用"五项映射（2026-09-02 决策）
presets=C6 ✅ / audit--html=C7 ✅ / gov quickstart=C2（已有规划）✅ / audit_pipeline=C1（已有规划）✅ / doctor 首跑引导=C8 ✅——与隔壁提案对齐且不重复造线

## 执行顺序建议
A1(+B1/B2/B4 同提交) → B3 → A2 → A3/A4/A5（你三个浏览器动作一次做完）→ C1-C4 → 观察 4 周 → D 按信号触发
