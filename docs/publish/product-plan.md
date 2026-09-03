# workspace-metabolism × Holdout — 副业产品计划（PRD v0.1）

> 状态：内部计划草案。定位来自 2026-09 的实际生态观察（Glama 92 分双旗舰、
> DSH 插件生态爆发、MCP 目录竞争白热化）。所有数字是假设，不是承诺。

## 1. 一句话定位

**给 AI 工作区装一个"代谢系统"：策略治理文件生命周期（免费、开源），
给 AI 团队卖治理与审计（付费、SaaS/服务）。**

## 2. 目标用户（按优先级）

| 圈层 | 痛点 | 入口 |
|---|---|---|
| 独立开发者/研究员（用 Claude Code/Codex/DSH） | 工作区被代理残留塞满；不知道删什么安全 | `wm doctor --residue`（引导式首次运行，v0.5 发布即主打） |
| 小型 AI 团队（2–20 人共享工作区/仓库） | 多 agent 写同一工作区，没有策略与问责 | MCP + govern/gate（执行点拦截） |
| 量化/AI 金融团队 | 研究结论可信度、AI 使用声明、合规留痕 | Holdout 家族（artifact + gov + 防篡改账本） |

**钩子（第一眼价值）**：`pip install workspace-metabolism && wm doctor --residue --apply-policy`
——10 秒看到"你工作区里有 2.8 GB 代理残留 + 自动生成治理策略"，零概念门槛。

## 3. 产品漏斗

```
获客        激活                    留存                付费
PyPI + Glama 92分   wm doctor 首扫惊喜    policy + journal 成习惯  团队策略管理
GitHub + MCP 目录    wm audit/health 分数  每周清理仪式              多工作区看板/告警
DSH 生态 + HN/Reddit  MCP 进入 agent 循环   rollback 建立信任         audit 服务
```

**关键设计原则（这次实现的硬约束）**：
- 引导 ≠ 第二系统：`doctor --apply-policy` 把内置知识转化为**用户自己的 policy 条目**，
  journal/rollback/verify 全程不变 —— 免费层零维护成本，用户数据自持
- MCP 是 agent 的入口，CLI 是人的入口，同一引擎
- 诚实边界写进 README：gate 不是沙箱、approver 是声明不是认证

## 4. 产品形态

### 免费层（永远开源，MIT）
- CLI + MCP（8 工具）+ gate 治理代理：现状已齐
- `doctor --residue` 引导式首次运行：**v0.5.0 主打（已实现，待发布）**
- 0.5.0 发布包：PyPI + release + README 演示 gif + Show HN/Reddit 文案（docs/publish 已有草稿，需更新到 v0.5 特性）

### 付费层（假设，验证后才做）
| 候选 | 形态 | 证据门槛 |
|---|---|---|
| 团队策略云：多工作区 policy 同步/审批流 | SaaS | ≥50 个活跃安装 + 3 个团队询问 |
| 治理看板：跨工作区 health/审计报表 | SaaS | 同上 |
| 工作区治理/合规审计服务（人工+工具） | 服务 | holdout 企业故事被验证（见 §6） |
| 托管 gate（远程策略下发） | SaaS | MCP remote 生态成熟后 |

**定价假设**：免费；团队版 $19–49/月起步（先验证需求再定价）。

## 5. 渠道与节奏

| 渠道 | 动作 | 状态 |
|---|---|---|
| Glama | 双 92 分 A 档背书（README 徽章已挂） | ✅ |
| awesome-mcp-servers PR #12939 | 等合并（要求已满足） | ⏳ |
| DSH | 讨论帖 5248 + cordis 集成 + 试跑验证 | ✅ |
| PyPI | wm 0.4.0 / gov 0.4.0 | ✅ |
| Show HN / Reddit | 草稿就绪，等 v0.5.0 发布后发（内容含 doctor 引导体验） | ⏳ 计划 |
| holdout 家族 | org 钉选 + profile README 流程叙事 | ✅ |

**发布节奏**：功能 → v0.5.0（doctor 引导）→ Show HN/Reddit 同步推 → 观察 4 周。

## 6. Holdout 的角色（企业故事线）

- workspace-metabolism = **获客漏斗**（免费、病毒式、开发者为王）
- holdout-governance = **企业故事**（"AI 用了什么、谁批准的、可防篡改审计"——
  金融/合规场景的付费理由）
- 一条产品线，两个开源旗舰，一个商业漏斗。**不要做成两个独立生意。**

## 7. 验证指标（4 周观察窗）

| 指标 | 目标（假设） | 达标动作 |
|---|---|---|
| pip 周安装 | >200 | Show HN/Reddit 发布后 1 周内 |
| GitHub stars | >50 | 同上 + Glama/DSH 引流 |
| `doctor --residue` 使用（无法直接统计 → 用安装后 7 日活跃近似） | 无法直接统计 | 在 audit report 里加匿名计数？→ **不做**（隐私优先），改看 GitHub 讨论/issue 反馈 |
| MCP 使用（Glama "Try in Browser" 次数） | >20/月 | 评分页 usage 指标 |
| 付费询问（GitHub issue/邮件/Discord） | ≥3 条 | 触发 §4 付费层 MVP 设计 |
| PR #12939 合并 | 尽快 | 若 1 个月无动静：撤掉重提或 🤖 通道 |

## 8. 诚实风险（写给自己）

1. **副业时间预算**：每周可投入 ≤10h → 发布、回复、迭代必须只做高杠杆项
2. **0 用户阶段别做六件套 MCP**：holdout 家族单工具 MCP 只按真实需求做（ROADMAP 已写明）
3. **doctor 是获客钩子不是核心**：别让它膨胀成第二个清理工具（提案的教训：
   硬编码规则 + 私有回收站 = 架构倒退；本次实现以"建议→policy"方式落地）
4. **分数是借来的**：Glama 92 分依赖描述与 CI 常绿——每次大改后检查重评
5. **合规不是万能钥匙**：金融用户需要真正的合规背书，工具只是故事的一部分

## 9. 下一步执行清单（按顺序）

1. [x] doctor --residue 实现（50b04a8，120 测试）
2. [ ] 发 v0.5.0（版本号、PyPI、release notes、README gif 更新）
3. [ ] Show HN + Reddit 发布（草稿更新到 v0.5：doctor 引导体验为核心 demo）
4. [ ] PR #12939 收尾（合并或撤重提）
5. [ ] 4 周观察窗 → 决定付费层 MVP 做不做
