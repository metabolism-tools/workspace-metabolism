# 论文与路演稿：Agentic Metabolic Engineering

> 状态：草稿 v1，2026-08。本文按 [academic-anchors.md](../academic-anchors.md) 文末的"三支柱 / 三段故事"结构组织，引用锚点见该文档（含 DOI 与验证说明）。
> 对应市场侧论证：[competitive-analysis.md](../competitive-analysis.md)。
> 本文是叙事稿，不是最终论文；实验数据需按 §5 计划重跑后填充。

---

## 第一部分：学术论文大纲

### 0. 投稿策略建议

- **首选**：arXiv 预印本（cs.SE / cs.AI）+ 同期投稿到 agentic systems 方向的 workshop（NeurIPS/ICML/ICLR 的 agents 或 LLM systems workshop）；"系统 + 可复现实验 + 清晰术语"是 workshop 友好形态。
- **次选**：工具论文（tool paper）方向——短论文讲模型与安全不变量，实验作为在线附录（repo 自带可复现 benchmark 是加分项）。
- 不建议一开始投全文期刊：贡献是"工程 + 度量框架"，全文评审周期不值得。

### 1. 标题候选

1. *Workspace Metabolism: Policy-Driven Lifecycle Governance for Agent-Driven Workspaces*
2. *Agentic Metabolic Engineering: Governing the Byproducts of Agentic Loops*
3. *From Compost Pile to Digestion System: Policy-Graded File Lifecycle for AI Workspaces*

推荐 1（中性、可检索）或 2（有辨识度）。副标题统一强调"policy-driven, reversible, auditable"。

### 2. 摘要草稿（英文，约 180 词）

> Agentic coding tools have made the workspace the byproduct accumulator of every loop: abandoned drafts, duplicated caches, half-finished refactors grow faster than the code itself. Existing tooling either diagnoses (disk analyzers), deduplicates, deletes by age (tmpreaper), or cleans a single vendor's state directory — none governs the lifecycle of what agents leave behind.
>
> We propose **Agentic Metabolic Engineering**, a governance model for agent-driven workspaces, and **workspace-metabolism** (`wm`), a zero-dependency reference implementation. A versioned policy file grades every path G1–G4 (never / keep / approve + reference check / auto). `clean` never deletes: items move to a recycle area with per-file SHA-256, `rollback` restores them exactly, and every action lands in a hash-chained journal whose integrity `verify` checks. A 0–100 health score and a MCP server make the model usable by humans, CI, and agents alike.
>
> In a reproducible 30-loop benchmark, the governed workspace keeps 2 active files and 240 fully recoverable byproducts in the recycle area; the ungoverned twin accumulates all 242 in place. We position the model against file-system aging, software decay, and context-rot literature, and discuss the limits of the biological metaphor honestly.

### 3. 章节大纲

#### 1 Introduction（约 2 页）

- **问题**：agent 循环改变工作区形态——"AI 写代码 → 报错 → 修复 → 新依赖出现 → 旧方案被放弃但没删除 → 循环加速"。结果：副产品比代码长得快（引用 Claude Code issues 的 350GB/537GB 报告作为动机数据）。
- **为什么"直接删"不够**：删除烧掉可能被下一个循环需要的中间产物与出处（autophagy 类比，引 Mizushima 2018）。
- **为什么 git 不够**：副产品大多 untracked、高 churn、非代码；强制提交纪律成本过高。
- **三幕叙事**：Prompt 让 AI 会写；Harness/Loop 让 AI 能持续写；代谢让工作区扛得住写（引 Anthropic Building Effective Agents 作为"loop 时代"证据）。
- **贡献列表**（工程贡献，不宣称新理论）：
  1. 治理模型：策略即代码的 G1–G4 分级 + 安全不变量（clean 永不直接删除、回滚需哈希校验、日志哈希链）。
  2. 参考实现：零依赖 CLI（audit/clean/rollback/purge/verify/status/init/explain/health/mcp）+ MCP stdio 服务。
  3. 度量仪式：30 循环可复现基准 + 0–100 健康分。
  4. 术语与定位：Metabolic Debt / Workspace Rot，作为生态共享的开放概念（明确不声称造词）。

#### 2 Background & Related Work（三支柱，约 2.5 页）

- **支柱 A：生物学隐喻的学术谱系**（1 段 + 表格）
  - Bailey 1991（代谢工程：改造代谢网络优化产物 → 我们把文件读写/保留/清理当作可分级治理的代谢途径）
  - Endy 2005（标准化/解耦/模块化 → 策略文件的部件化设计）
  - Wu 2016（代谢负担 → 冗余文件的成本模型）
  - Mizushima 2018（自噬：选择性包裹→降解→回收 → 回收区）
  - Cannon 1932 / Schrödinger 1944（稳态 / 负熵 → 健康分与"开放系统维持局部有序"）
  - 主动引用批评：Leff 2021、Haglund（"熵=无序"是教学隐喻）——放在本节末尾或 Limitations，明确"隐喻用于沟通、指标用于治理"。
- **支柱 B：软件工程**（1 段 + 表格）
  - Lehman 1980 演化定律 I/II（持续变化、复杂度增长 = 问题陈述）
  - Brooks 1987（本质复杂度只能管理不能消灭）
  - Eick 2001 Does Code Decay?（用变更数据度量衰减的方法论 → audit 历史 + 健康分）
  - Foote & Yoder 1999 Big Ball of Mud（无人干预的熵增轨迹）
  - Smith & Seltzer 1997 File System Aging（工作区老化有实证传统）
  - 维护标准 ISO/IEC 14764、IEEE 1219（四类维护映射 G1–G4 处置）
  - Cunningham 1992 技术债 + Kruchten 2012（G3 付息 / G4 破产重组 / 健康分=债务指标）+ 技术债隐喻局限（IEEE 6608681）
- **支柱 C：LLM 上下文与 agent 循环**（1 段 + 表格）
  - MAST（Cemri 2025）：多智能体失败分类，我们的 audit/verify 对应捕获规范漂移与信息缺失
  - Context rot（2026）与 LOCA-bench（2026）：问题命名 + 可控评估基准
  - MemGPT / A-MEM / Generative Agents：工作区 = agent 的外部虚拟上下文/长期记忆 → 治理文件 = 治理上下文
  - Context Engineering survey（2025）与 Everything is Context（2025）：文件系统抽象是 context engineering 的载体
  - Anthropic Building Effective Agents：简单可组合部件哲学
  - **与竞品工具的区分**（半页）：磁盘分析/去重/年龄清理/官方状态目录/社区清理工具的"切片"性质 + 能力点阵图（competitive-gap-en.png）；GC 对照（Jones & Lins 1996；Wilson 1992）：自动回收 vs 策略驱动可审计回收。
- **与相邻论文的区别**：LemonHarness（L3 运行时边界）、Workspace-Bench（评估脏工作区中的 agent 表现，是未来评测场地而非竞争框架）、AgentFold（上下文雕刻，L2/L4）——引 narrative.md §8 的定位表。

#### 3 The Model（约 3 页）

- 3.1 策略文件（metabolism.json）：G1–G4 语义、字段（retention_days/scope/protected/owner/intent/review_after）、JSON Schema 校验、auto-discovery（metabolism.json/.wm.json）、作为"标准工件"与 .gitignore 类比。
- 3.2 四阶段模型：catabolism（audit）→ sequestration（clean）→ verification（verify）→ anabolism（rollback）；每阶段的形式化描述（输入、输出、不变量）。
- 3.3 安全不变量（每个都给可测试的陈述）：
  - I1：clean 永不删除——只移动，且目标（回收区）位于受管状态目录。
  - I2：rollback 前置校验——恢复前逐文件 SHA-256 比对，拒绝覆盖已存在路径。
  - I3：日志链完整性——每个条目链接前一条目哈希；verify 检出任何历史篡改（Haber & Stornetta 1991；Schneier & Kelsey 1999 前向安全作为强化方向）。
  - I4：G3 双要素——approve + approver 落审计。
  - I5：purge 是唯一真删除，且只在回收区内、在 retention 之后。
- 3.4 度量：健康分 0–100（审计 25 / 治理 25 / 腐烂负担 35 / 回收就绪 15）与 Wang & Strong 1996 多维框架的关系（当前是单标量加权，论文中说明这是 v1 简化，多维度拆分是未来工作）。
- 3.5 与 ILM/档案学的映射（半页）：ISO 15489 留存分级表、OAIS SIP/AIP/DIP 与 fixity 校验、DCC 策展循环（Higgins 2008）——"治理必须是循环而非一次性整理"。

#### 4 Implementation（约 1.5 页）

- 零依赖 Python 3.11+ stdlib-only（论证：可审计性、供应链安全、任何环境可跑）。
- 命令面：audit/clean/rollback/purge/verify/status/init/explain/health/mcp。
- MCP stdio 服务器：agent 自服务设计（clean 默认 dry-run，execute=true 显式传入；策略文件仍是一切裁决者）。
- 调度与 CI：Task Scheduler/cron 模板、CI 健康门禁（失败阈值）。
- 状态目录默认在工作区外（防 `git add .` 扫入审计日志）。
- 性能备注：30 循环基准里 audit ~80ms（机器相关），增量扫描是未来优化。

#### 5 Evaluation（约 3 页，实验需按此计划重跑）

- **E1 可复现基准（已有）**：30 循环双工作区对照（2 vs 242，全部可回滚，哈希链完整）。报告结构数字 + 机器相关数字的区分；发布 benchmark-run JSON 与日志（已发布）。
- **E2 长时任务对照（计划，LOCA-bench 风格）**：用 LOCA-bench（ICML 2026）或自建 100 循环多档案工作区（agent-heavy repo / 数据科学工作区 / web 项目，ROADMAP 的 benchmark v2），测量：完成率、步骤数、重试次数、audit 时间随文件数的增长曲线（对比"有治理 vs 无治理"）。预期叙事：治理组任务成功率不衰减或衰减更慢；代价是 audit 开销。
- **E3 回滚正确性**：随机破坏回收区文件 → rollback 拒绝恢复（SHA-256 不匹配）；正常路径逐字节恢复（已有 benchmark 数据）。
- **E4 审计防篡改**：手工篡改历史日志条目 → verify 报链断裂；展示攻击场景（删除中间条目、改写时间戳、替换文件）。
- **E5 健康分合理性**：人工构造"健康/腐烂"工作区集合，健康分排序与人工排序的一致性（简单相关系数即可，先定性后定量）。
- **E6 策略可移植性**：同一策略文件在不同 OS 的表现（CI 三 OS 矩阵已覆盖基本正确性）。
- 诚实边界：所有基准都是模拟循环而非真实 agent；E2 用真实 agent（Claude Code / Codex）跑受限任务作为 v2 验证，报告其方差。

#### 6 Limitations（约 1 页）

- 隐喻边界：熵≠无序（Leff 2021 / Haglund）、技术债隐喻局限（IEEE 6608681）→ 明确"类比用于沟通，指标用于治理"；健康分是简化加权，不是信息论意义上的熵。
- 引用检查的语义深度：G3 目前是"审批 + 保留期"，引用失效检测（reference rot）尚未实现（计划中）。
- 基准的模拟性质；真实 agent 行为方差大。
- 回收区占用与保留期的平衡（双倍磁盘占用窗口）。
- 单机假设：多机/共享工作区与权限模型未覆盖。
- 未验证文献提醒：正式投稿前复核预印本作者信息与 DOI（见 academic-anchors.md 的诚实标注）。

#### 7 Future Work

- 策略 Schema v2：owner/intent/review_after 的评审工作流、策略 diff 与审批历史入日志。
- 引用失效检测与"最后访问时间"默认特征（agedu 维度）。
- 健康分多维化（对齐 Wang & Strong 框架）与跨仓库可比标准。
- 真实 agent session-end hooks（Claude Code / Codex）+ 托管徽章端点。
- Merkle 根批量校验（Merkle 1980）与日志归档（日志自身的生命周期管理）。

#### 8 参考文献组织

直接复用 academic-anchors.md 的 TOP 10 + 荣誉提名；在论文中按支柱分组，并对每个隐喻性表述加 footnote "used as an analogy"。

---

## 第二部分：路演稿

### 三段故事（30 秒 / 2 分钟 / 5 分钟版本共用骨架）

1. **命名故事**：细胞靠代谢维持低熵（Schrödinger 1944）；代谢工程让工程师能改造代谢（Bailey 1991）→ 我们要把 AI 工作区变成"可代谢"的系统。
2. **问题故事**：文件系统会老化（Smith & Seltzer 1997）、代码会腐烂（Eick 2001）、上下文会 rot（2026）→ 没人治理的工作区是默认的熵增轨迹；AI 循环把它加速了。
3. **方案故事**：哈希链日志让每次清理可审计、可回滚（Haber & Stornetta 1991）；健康分让治理可度量（Wang & Strong 1996）→ 这就是 Agentic Metabolic Engineering。

### 逐页 slide 大纲（10 页，含现成素材）

| # | Slide | 内容 | 素材 |
|---|---|---|---|
| 1 | 封面 | 一句话："循环让 Agent 一直跑，代谢让工作区一直活" | cover-zh.png |
| 2 | 问题 | AI 写代码像喷泉，工作区没有排水口；副产品比代码长得快（350GB/537GB 实例） | 文字 + 引用 |
| 3 | 三幕 | Prompt → Harness/Loop → Metabolism；第三幕：工作区能否扛得住写作 | stack-l5-en.png |
| 4 | 现有工具是切片 | 六类工具各自只做一块，没有闭环 | **competitive-gap-en.png（新）** |
| 5 | 方案：四阶段 | audit→clean→verify→rollback；绝不直接删除 | four-phases-en.png |
| 6 | 策略即代码 | metabolism.json 像 .gitignore 一样进仓库；G1–G4 分级 + JSON Schema | 代码截图 |
| 7 | 证据 | 30 循环对照：2 vs 242，全部可回滚，哈希链完整 | experiment-30-en.png |
| 8 | 定时 ≠ 代谢 | 调度器是闹钟，策略是消化系统；cron/任务计划/CI 可组合 | scheduled-vs-metabolism-en.png |
| 9 | agent 自服务 | wm mcp：agent 在循环末尾自己跑 micro-metabolism；clean 默认 dry-run | 终端截图 |
| 10 | 愿景 + 邀请 | 代谢策略成为标准工件（如 .gitignore）；Metabolic Debt / Workspace Rot 成为开放词汇；开源讨论 | 文字 |

### 口播要点（每页 1 句记忆点）

- P2："问题不是 AI 写得太多，而是没人管它留下什么。"
- P4："磁盘工具很多，闭环只有一个。"
- P5："我们不是第 N 个清理 ~/.claude 的工具——我们治理 agent 在你项目里写的所有文件。"
- P7："2 比 242 不是一个营销数字，是你自己能在仓库里重跑出来的实验。"
- P9："人类从清洁工变成政策作者。"
- P10："我们的野心不是让这个工具流行，是让'代谢'这个词成为工作区的常识。"

---

## 附：引用清单（完整版见 academic-anchors.md）

TOP 10：Bailey 1991；Haber & Stornetta 1991；Smith & Seltzer 1997；Wang & Strong 1996；Cemri 2025 (MAST)；Lehman 1980；Schneier & Kelsey 1999；Context Rot 2026；MemGPT 2023；Cunningham 1992。
荣誉提名：ISO 15489-1:2016；ISO 14721:2012；Endy 2005；Mizushima 2018；Klein 2014（引用腐烂）；LOCA-bench 2026。
