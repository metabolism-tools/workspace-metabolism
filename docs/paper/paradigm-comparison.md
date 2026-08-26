# 范式对比与优化建议：Agentic Metabolic Engineering vs Prompt / Context / Harness / Loop Engineering

> 2026-08-18。目的：把论文 `agentic-metabolic-engineering-paper-v2.md` 与相邻工程范式（及其代表论文）逐层对比，
> 找出论文目前缺失的定位、引用与论证，给出按优先级排列的优化清单。
> 对比用文献均经 web_search 核实存在（arXiv 号已确认）。
>
> **应用状态（2026-08-18）**：🔴 必做三项 + 🟠 建议第 4、5、6、8 项已应用到论文（v3）：
> 新增 III.B 范式关系（L1–L5 表）、III.C 形式化框架（M0–M3 梯子 + G1–G4 层级 + 代谢周期）、VII.B 设计原则、VII.C 反模式、
> VII.D Open Problems 与隐喻边界、引用 [18]–[26]（Cunningham、Kruchten、Haber & Stornetta、Schneier & Kelsey、Context Engineering 两篇、Prompt 两篇、Leff）。
> 未应用：🟠 第 7 项已部分应用（V.C context noise 已引 [23]）；🟡 真实 agent loop 实验、与 zclean/agent-gc 对照实验、健康分度量（需数据/实验，留给 Evaluation 阶段）。
> 注意：另一AI分析中"Context Engineering 综述=五角色+四阶段、200 次交互 72%→55%"与"Prompt Report=41 种技术"**经原文核实不成立**（实际：58 种技术；Context 综述中查无 200/72% 数据），已剔除，勿引用。

## 一、范式全景：五层工程栈

| 层 | 范式 | 核心问题 | 工程对象 | 代表文献（已核实） | 成熟度 |
|---|---|---|---|---|---|
| L1 | Prompt Engineering | 怎么对模型说，它才输出对？ | 提示词 | [The Prompt Report](https://arxiv.org/abs/2406.06608)（arXiv:2406.06608）；[A Systematic Survey of Prompt Engineering](https://arxiv.org/html/2402.07927v2)（arXiv:2402.07927） | 成熟（2023–2024 已系统化） |
| L2 | Context Engineering | 给模型读什么，它才知道？ | 上下文（检索/压缩/构造） | [A Survey of Context Engineering](https://ar5iv.labs.arxiv.org/html/2507.13334v2)（arXiv:2507.13334）；[Everything is Context: Agentic File System Abstraction](https://ar5iv.labs.arxiv.org/html/2512.05470)（arXiv:2512.05470） | 兴起（2025） |
| L3 | Harness Engineering | 怎么约束运行时，让 agent 可靠？ | 运行时/沙箱/工具接口 | [AI Harness Engineering: A Runtime Substrate](https://huggingface.co/papers/2605.13357)（arXiv:2605.13357）；LemonHarness（arXiv:2606.24311） | 涌现（2025–2026 预印本） |
| L4 | Loop Engineering | 怎么设计循环，让 agent 自主持续运行？ | 循环结构/状态机/调度 | [Engineering the Loops that Replace Step-by-Step Prompting](https://huggingface.co/buckets/huggingchat/papers-content/tree/2607/2607.00038.md)（arXiv:2607.00038） | 涌现（2026） |
| L5 | **Agentic Metabolic Engineering**（本论文） | 每轮循环之后，工作区副产物怎么办？ | 文件生命周期（文件系统层） | 本论文 + workspace-metabolism | 萌芽（本论文） |

## 二、逐范式对比

### 1. vs Prompt Engineering（L1）—— 正交，无需竞争，但论文需要亮明分层

Prompt Engineering 优化的是"输入前"（怎么把任务说清楚）；AME 治理的是"输出后"（执行留下的物理残留）。
两者在因果链上不相交。**论文现状**：完全没提 Prompt Engineering——这没问题，但论文 III.A 只与 Harness/Loop 对比，
建议在 III 加一个 L1–L5 分层定位表（philosophy.md 已有现成版本，可作 Figure 1），一句话说明 Prompt/Context 管"入"、
Harness/Loop 管"行"、Metabolic 管"留"。这会让"第五层"叙事立刻成立。

### 2. vs Context Engineering（L2）—— 最值得建立连接的一层，论文现在白白放过

- Everything is Context 直接把"agentic 文件系统抽象"当作 Context Engineering 的载体：**工作区文件就是 agent 的持久化上下文**。
- 论文 V.C 的"Increased context noise (agents must parse through more files)"正是在论证这件事，**但没有引任何 Context Engineering 文献**。
- **优化**：在 VI 新增一小节（或并入 VI.B），用 Context Engineering survey + Everything is Context 支撑"文件=上下文、文件治理=上下文卫生"的论证；
  并可在 V.C 的 context noise 论点处补引 arXiv:2512.05470。这是把论文从"清理工具论文"提升为"治理范式论文"的关键一步。

### 3. vs Harness Engineering（L3）—— 边界要写清楚，LemonHarness 是双刃剑

- AI Harness Engineering 定义"运行时底座"；LemonHarness 用显式工作区边界约束执行期状态变更。
- **关系**：Harness 管"执行期间"的状态变更约束；AME 管"执行之后"的残留治理。LemonHarness 的 "observation, execution, modification,
  and verification aligned" 主张与 AME 的 audit/verify 阶段同构——论文 VI.B 已引 LemonHarness，但只在 VI.D 用一句话划了边界。
- **优化**：在 VI.D（Our Position）把边界展开成三列对比：**执行期间治理（LemonHarness/AgentFold/SABER）→ 执行后测量（Workspace-Bench）→ 执行后清理无审计（zclean/agent-gc）→ 生命周期治理（AME）**。目前论文已有雏形，补上"无审计清理"与"有审计治理"的对比即可。

### 4. vs Loop Engineering（L4）—— 微代谢应该"长"进循环里，论文有概念没论证

- Engineering the Loops 把 agent 循环工程化（plan→execute→observe→reflect）。
- **关系**：micro-metabolism 本质上是**循环内的原生治理步骤**（观察阶段的扩展：除了"世界发生了什么"，还问"工作区变成了什么样"）。
- **优化**：III.D 的微代谢段落目前只是"wrapper script"的工程描述，建议升格为范式主张：
  "micro-metabolism 是把代谢阶段嵌入 loop 观察步骤的循环内治理（loop-native governance）"，与 Loop Engineering 的循环抽象对接，
  并引 arXiv:2607.00038。这句是论文"填补执行期间与执行后之间空白"叙事的最强版本。

### 5. vs 技术债基础文献（跨层）—— 论文最大的引用漏洞

论文通篇讨论 technical debt / agent debt / metabolic debt，但**参考文献里没有任何一条技术债源头文献**：
- Cunningham, W. (1992). The WyCash Portfolio Management System. OOPSLA '92 Addendum. DOI: [10.1145/157709.157715](https://dl.acm.org/doi/10.1145/157709.157715)（"技术债"概念的原始出处，审稿人必查）
- Kruchten, Nord, Ozkaya (2012). Managing Technical Debt. ACM Queue. DOI: [10.1145/2168796.2168798](https://dl.acm.org/doi/10.1145/2168796.2168798)
**优化**：VII.A 定义 metabolic debt 之前先引 Cunningham；"metabolic debt 是 technical debt 的文件系统层沉积"这句要在引了源头文献之后说才站得住。

### 6. 其他必须补的引用

- **哈希链审计声明（IV.B "Hash-chain audit: append-only and tamper-evident"）零引用**。补：
  - Haber & Stornetta (1991). How to Time-Stamp a Digital Document. J. Cryptology. DOI: [10.1007/BF00196791](https://link.springer.com/article/10.1007/BF00196791)
  - Schneier & Kelsey (1999). Secure Audit Logs to Support Computer Forensics. ACM TISSEC. DOI: [10.1145/317087.317089](https://dl.acm.org/doi/10.1145/317087.317089)
- **隐喻的学术诚实（Limitations）**：Leff (2021). Good Use of a 'Bad' Metaphor: Entropy as Disorder（"代谢/自噬/消化"是类比不是定律，度量必须落在可测指标上）。这在 philosophy.md FAQ 与 academic-anchors 方向 11 已有，论文 VII.B Limitations 应加一句。

## 三、优化清单（按优先级）

### 🔴 投稿前必做（引用完整性，审稿人一眼能抓）
1. 补技术债源头：Cunningham 1992（VII.A 定义 metabolic debt 前）+ Kruchten 2012。
2. 补哈希链审计文献：Haber & Stornetta 1991 + Schneier & Kelsey 1999（IV.B 安全模型处）。
3. VI 新增/扩展现有段落，连接 Context Engineering（2507.13334 + Everything is Context 2512.05470）——支撑"文件=上下文、治理=上下文卫生"。

### 🟠 强烈建议（论文档次：从工具论文 → 范式论文）
4. III 加 L1–L5 分层定位表（Figure 1，直接采用 philosophy.md 的栈表），亮明"第五层"位置。
5. III.D 微代谢升格为"循环内治理（loop-native governance）"主张，引 2607.00038。
6. VI.D 边界对比展开为四列（执行期治理/执行后测量/无审计清理/有审计生命周期治理）。
7. V.C 的 context noise 论点补引 Everything is Context（2512.05470）。
8. VII.B Limitations 补隐喻边界声明（Leff 2021）：术语是类比，指标才是证据。

### 🟡 可选（提升实验与度量说服力）
9. Evaluation 增加真实 agent loop 实验（真实 coding agent 跑 N 轮，测文件增长/回收/回滚恢复），并声明与模拟基准的差异——这是论文最大的证据缺口。
10. 与 zclean/agent-gc 做对照运行实验（各自跑同一污染工作区，对比"清理后可恢复性/审计性"），把 VI.C 的工具对比从文字变成数据。
11. 健康分（wm health）作为 metabolic debt 的度量方案，引 Wang & Strong (1996) 数据质量维度框架（academic-anchors 方向 8）。
12. 补 SABER 工作区版（arXiv:2606.01317）作为 VI.B 的并列引用（两篇 SABER 的区分已在 academic-anchors 12.2 注明）。

## 四、新增参考文献建议（均已核实存在）

| 建议编号 | 文献 | arXiv/DOI |
|---|---|---|
| [18] | S. Schulhoff et al., "The Prompt Report: A Systematic Survey of Prompting Techniques" | arXiv:2406.06608 |
| [19] | "A Systematic Survey of Prompt Engineering in Large Language Models" | arXiv:2402.07927 |
| [20] | "A Survey of Context Engineering for Large Language Models" | arXiv:2507.13334 |
| [21] | Xu & Mao, "Everything is Context: Agentic File System Abstraction for Context Engineering" | arXiv:2512.05470 |
| [22] | W. Cunningham, "The WyCash Portfolio Management System," OOPSLA '92 Addendum | DOI 10.1145/157709.157715 |
| [23] | P. Kruchten, R. Nord, I. Ozkaya, "Managing Technical Debt," ACM Queue, 2012 | DOI 10.1145/2168796.2168798 |
| [24] | S. Haber, W. Stornetta, "How to Time-Stamp a Digital Document," J. Cryptology, 1991 | DOI 10.1007/BF00196791 |
| [25] | B. Schneier, J. Kelsey, "Secure Audit Logs to Support Computer Forensics," ACM TISSEC, 1999 | DOI 10.1145/317087.317089 |
| [26] | H. Leff, "Good Use of a 'Bad' Metaphor: Entropy as Disorder," Foundations of Science, 2021 | scholarsportal（见 academic-anchors 11.2） |
