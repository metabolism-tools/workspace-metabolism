# AI 智能体工作区卫生工具 —— 逐命令级竞品对比报告

**分析对象**：cozempic（Ruya-AI）、artifact-guard（ekta-chaudhry）、helm-agent-ops（Helm/JDeun）vs **workspace-metabolism（wm）**
**证据基础**：三份竞品的公开 README（GitHub raw / PyPI 描述）＋ wm 本地源码 `src/workspace_metabolism/cli.py`（命令表由 argparse 直接提取，可信度最高）。凡 README 声称但未能在源码层面核实的功能，均标注"未在公开资料中证实"。

**来源 URL**：
- cozempic：https://github.com/Ruya-AI/cozempic
- artifact-guard：https://github.com/ekta-chaudhry/artifact-guard
- helm-agent-ops：https://pypi.org/project/helm-agent-ops/ （描述即完整 README）、https://github.com/JDeun/Helm
- wm：本地源码 `src/workspace_metabolism/cli.py` + `README.md`

---

## 0. wm 基准命令面（来自本地 cli.py，作为对照锚点）

| wm 命令 | 参数/子命令 |
|---|---|
| `audit` | `--dupes` `--auto` `--json`（只读体检，写报告+日志条目） |
| `clean` | `--grades G3/G4`（必填）`--yes` `--approve` `--approver` `--auto` |
| `rollback <run_id>` | `--dry-run`（SHA-256 校验后从回收区恢复） |
| `purge` | `--older-than N`（默认 30）`--yes` `--auto`（唯一真删除） |
| `verify` | 无参数（校验日志哈希链+运行清单） |
| `status` / `init` | `init --force`（脚手架 metabolism.json） |
| `explain <path>` | `--json`（策略"营养标签"） |
| `health` | `--json` `--badge`（0-100 分） |
| `mcp` | 无参数（MCP stdio 服务） |

全局旗标：`--root` `--state-dir` `--registry` `--protected-window`。

---

## 1. 逐命令对比表

### 表 1：cozempic（v1.8.x，Claude Code 会话上下文减脂）↔ wm

来源：[GitHub - Ruya-AI/cozempic](https://github.com/Ruya-AI/cozempic)

| cozempic 命令/功能 | 行为描述（README 转述） | 对应 wm 命令 | 差异点 |
|---|---|---|---|
| `init` | 往项目里接线 hooks + slash command，guard 守护进程随 SessionStart 自动启动 | `wm init` | 同名词但语义不同：cozempic 挂钩到 Claude Code 会话生命周期；wm 只生成策略文件，不碰任何 agent 运行时 → **wm 更 agent-agnostic** |
| `list` / `current [-d]` | 列出会话及大小、token 估算；诊断当前会话 | `wm status` / `wm audit` | 面向"会话文件"而非"工作区文件"；cozempic 专精 Claude 格式 → 独有（会话视图），wm 无此视角 |
| `diagnose <session>` | 分析 bloat 来源、缓存命中率、上下文百分比 | `wm audit` | 功能对位但粒度相反：cozempic 分析单会话内部结构，wm 分析整盘文件策略 → 互补而非竞争 |
| `treat <session> [-rx PRESET] [--execute]` | 运行修剪处方（默认 dry-run，`--execute` 才改，改前自动备份 `.jsonl.bak`） | `wm clean --grades G4 --yes` | 行为模式高度相似（dry-run 默认、显式执行）；但 cozempic 处理的是会话 JSONL 内消息，wm 处理真实文件 → 各自领域独有 |
| `strategy <name> <session>` | 单条策略运行（18 条策略、3 个处方档：gentle 5 / standard 11 / aggressive 18） | （wm 无单条策略概念；最接近 `explain` 的"逐条解释"） | cozempic 独有：**策略组合器**。wm 的 G1-G4 是"文件价值分级"，cozempic 的 tier 是"修剪激进程度分级"——两者的"分级"是不同维度 |
| `reload [-rx]` | treat + 新终端自动 resume（tmux/screen 同窗恢复） | （wm 无；最接近 `rollback` 的恢复语义） | 独有：会话级"剪完再续跑"。wm 无会话概念 |
| `checkpoint [--show]` | 保存 Agent Teams 协调状态到磁盘（Task 钩子驱动） | （无直接对应；wm 的回收区是文件级快照） | 独有：团队状态检查点。wm 的回收区只保护文件，不保护 agent 协调状态 |
| `guard [--daemon]` | 守护进程每 30s 轮询，**4 档分级修剪**：Soft 25%→gentle 不重载；Hard 55%→standard+重载；Hard2 80%→aggressive+重载；User 90%→手动。safe-point 保护（有 Workflow/子代理/团队/工具调用在途时延后重载） | （wm 仅有 `--protected-window` 静态时段保护 + cron/任务计划模板，无守护进程） | cozempic **更强/独有**：主动式、阈值驱动、会话感知。用户所称"分级修剪保护"即此 4-tier guard |
| `doctor [--fix]` | 15 项检查（README 表列 8 项）：会话 JSON 损坏、孤立 tool_result、僵尸团队、超大会话、stale-backups、磁盘用量等，可自动修复 | `wm verify`（校验哈希链） | 部分重叠（都做"体检+修复"），但 cozempic 检查的是会话文件完整性，wm 检查的是审计链完整性 → 各自领域独有 |
| `digest [show\|update\|clear\|flush\|recover\|inject]` | 行为摘要：从对话提取"不要做 X"类纠正，2 次出现才激活，同步进 Claude 记忆系统 | （wm 无） | cozempic 独有；wm 完全不涉及会话记忆 |
| `dashboard` | 生成修剪节约量的静态 HTML 报告 | `wm audit`（写报告）+ `wm health --badge` | 部分对位：都是"给人看的报告"，cozempic 是会话级节约可视化，wm 是工作区健康分 |
| `formulary` | 列出全部策略与处方 | （无直接对应；wm 的 `explain` 是逐路径解释而非全局清单） | 独有：策略目录即文档 |
| `self-update` / 自动更新 | 每日检查 PyPI 就地升级；`COZEMPIC_PIN`/`COZEMPIC_NO_AUTO_UPDATE` 控制 | （wm 无） | 独有。对 wm 是反模式（策略工具应可复现） |
| `uninstall [--project\|--all\|--purge]` | 反向 init：拆除 hooks + slash 命令 | （wm 无对应；`purge` 语义完全不同） | 独有：安装痕迹清理 |

**未在公开资料中证实**：README 徽章自称"100k+ 用户"（自报数据，无法独立核实）；"18 条策略"清单与 changelog 一致，但每条策略的"Expected"节约百分比是声称值，未附基准数据。

---

### 表 2：artifact-guard（npm，AI 开发工作流隐私感知工件生命周期）↔ wm

来源：[GitHub - ekta-chaudhry/artifact-guard](https://github.com/ekta-chaudhry/artifact-guard)

| artifact-guard 命令/功能 | 行为描述（README 转述） | 对应 wm 命令 | 差异点 |
|---|---|---|---|
| `start` | 捕获工作区基线快照，存 `.artifact-guard/session.json` | （wm 无"会话基线"；最接近 `init` 的注册动作） | 独有：**会话内 diff 视角**。wm 是常驻策略视角，没有"这个 agent 会话新建了哪些文件"的概念 |
| `status` | 显示自基线以来 created/modified/deleted 的文件 | `wm status` / `wm audit` | 对位但更强于"增量"：artifact-guard 回答"这轮会话动了什么"，wm 回答"现在全盘状态如何" → 互补 |
| `finish` | 分类工件（source/temporary/sensitive/deliverable/unknown）并打印清理报告 | `wm audit`（候选分类） | 部分对位。artifact-guard 的分类是**推断**（模式匹配），wm 的分类是**策略声明**（policy 文件）→ wm 更可审计 |
| `finish --delete-safe` | 只删除"同时满足 temporary 且 created"的文件；改过的、source、sensitive、deliverable、unknown **一律不删** | `wm clean --grades G4 --yes` | 对位但更保守：wm 的 G4 由策略授权即可删；artifact-guard 硬编码双条件白名单，且**没有回收区**——删了就没了 → **wm 更安全（可回滚）** |
| `finish --interactive` | 逐条确认后删 safe 候选（与 `--delete-safe` 互斥） | `wm clean --grades G3 --approve --approver` | 对位：都是人工审批路径。wm 额外记录 approver 身份进审计链 → wm 更强（可追溯） |
| `finish --report` | 写 `.artifact-guard/report.md`：摘要计数、可删字节、分类原因、清理策略、已删/跳过清单 | `wm audit`（写报告）+ `wm health` | 对位。artifact-guard 报告**面向会话结束**（agent 退场仪式），wm 报告面向**持续运维** |
| `finish --clean-state` | 清理 `.artifact-guard/session.json`（保留 report） | （wm 无；wm 状态在系统缓存目录，天然不进 git） | 独有/更弱：wm 把状态放在工作区外，根本不需要"清理状态"这一步 → wm 设计上更优 |
| `.artifactguardrc.json` 配置 | ignore/sourceExtensions/temporaryPatterns/sensitivePatterns/deliverablePatterns，支持 glob 与正则 `/pattern/flags` | `metabolism.json` 策略 | 对位但 wm 更强：wm 策略带 grade/retention/scope/protected/owner/intent/review_after 等字段 + JSON Schema 校验 |
| Git-aware 分类 | 在 git 仓库内用 `git ls-files` 判定 tracked 文件为 source-impacting；sensitive 模式优先于 git 追踪 | （wm 无 git 集成） | 独有：**隐私优先 + git 感知**。wm 不读 git 状态 |
| integrations/（pi-skill、claude-code、codex、generic-agent） | 给 4 类 agent 提供会话开始/结束调用 AG 的集成说明 | `examples/micro_metabolism.py` + MCP | 对位：两者都提供"agent 循环里调用"的接线。wm 更进一步：MCP 让 agent 可编程调用而非仅 shell |

**未在公开资料中证实**：README 标"Planned Features: Multi-session history"，即目前**没有历史记录能力**（无回滚、无审计链）；敏感文件检测只按模式匹配（`*resume*` 等），未声称有熵/密钥检测。

---

### 表 3：helm-agent-ops（Helm v0.13.0，长生命周期 agent 工作区稳定性运维）↔ wm

来源：[PyPI - helm-agent-ops](https://pypi.org/project/helm-agent-ops/)（描述即完整 README）、[GitHub - JDeun/Helm](https://github.com/JDeun/Helm)

| helm 命令/功能 | 行为描述（README 转述） | 对应 wm 命令 | 差异点 |
|---|---|---|---|
| `init --path` | 建 Helm 工作区（`.helm/`，状态在专用目录） | `wm init` | 对位。helm 需要 `$HELM_WORKSPACE` 环境变量定位；wm 自动发现 `metabolism.json` → wm 更零配置 |
| `profile run <profile> --task-name -- <cmd>` | 在声明了 blast radius 的执行档案下跑命令（`inspect_local` / `workspace_edit` / `risky_edit` / `service_ops` / `remote_handoff`），档案决定可用工具组 | （wm 无执行档案；最接近 G1-G4 分级授权） | helm 独有：**命令级治理**。wm 治理的是文件，helm 治理的是 agent 将要执行的命令 → 互补领域 |
| Command guard | 破坏性或超出档案的命令在执行前被拦截 | `wm clean --grades`（策略门控） | 概念对位（都是"策略先行、执行后置"），对象不同（命令 vs 文件） |
| `checkpoint create/list/recommend` | 大改前建检查点作为回滚目标；推荐何时该建 | `wm clean`（回收区）+ `wm rollback` | 对位但机制不同：helm 检查点是**工作区快照**（可含 `$HELM_WORKSPACE`），wm 回收区是**逐文件带 SHA-256 的移动+校验** → wm 的恢复更精细（可按 run 精确回滚），helm 更粗粒度 |
| `task list / task doctor` | 任务台账与任务状态诊断（required/completed/blockers/approvals 结构化存储，"Control Flow Is Not Memory"） | `wm status` | 独有：**任务状态机**。wm 无任务概念 |
| `report --format markdown` | 生成本地任务台账/命令日志/检查点/面板的 markdown 报告 | `wm audit` 报告 | 对位，helm 覆盖面更广（含命令日志、任务） |
| `doctor` / `reconcile` / `verify-contract` | 结构体检；对照期望快照重放参考文件、报告漂移；断言运维不变量（guard fail-closed、审批 TTL、原子日志） | `wm verify` / `wm audit` | 部分对位：wm `verify` 校验**哈希链**（篡改检测），helm `verify-contract` 校验**行为不变量** → 互补；helm 独有 reconcile 漂移检测 |
| `context --mode decisions/timeline/entity/reflect-candidates --explain-ranking` | 文件化记忆 + 可解释排序检索（决策/时间线/实体/反思候选） | `wm explain <path>`（策略解释） | 部分对位：都叫"explain"，但 wm 解释"策略为什么这么分级"，helm 检索"历史决策" → 语义不同，wm 更聚焦 |
| `privacy scan / tokenize` | 隐私边界预检：扫描文本中的敏感信息（示例含邮箱）、按 scope 做 tokenize | （wm 无；artifact-guard 的 sensitivePatterns 是最弱版本） | helm 独有（且比 artifact-guard 更强：可 tokenize 而非仅标记） |
| `skill-lifecycle negative-claims / revalidation-due / revalidate-claim` | 技能规则的生命周期治理：负面声明、重验证到期、按 claim-id 处置 | （wm 无） | 独有：技能/知识衰退治理。wm 不管理知识 |
| `run-contract` / `capability-diff` / `skill-promotion digest` / `shadow-report` | 工作流契约校验、能力差异、技能晋升队列、影子模式报告（`ready_to_enforce / needs_more_data / caution / no_signal`） | （wm 无；最接近 `clean` 的 dry-run 影子） | 独有：**影子模式**——先记录不执行，凑够证据再启用。wm 的 dry-run 是一次性的，无跨期累积 |
| `health state / select --json` | **模型健康探针**（选择档案/上下文 token 数评估模型），另有 `scripts/model_health_probe.py` | `wm health` | 同名但**语义完全不同**：helm 测 LLM 模型，wm 测工作区健康分（0-100，4 维加权）→ wm 独有"工作区健康分"这个指标本身 |
| `loops validate/inspect`、`skill-intake classify/validate`、`memory capture-chat`、`survey/onboard` | 循环契约校验、外部技能准入、聊天记忆捕获、采纳现有系统为只读上下文源 | （wm 无） | 独有：面向 agent 运行时生态 |
| `dashboard` | 一页展示工作区状态 | `wm health --badge` + `wm status` | 对位，helm 是 Web/终端面板，wm 是 CLI + shields.io 徽章 |

**未在公开资料中证实**：README 声称的 arXiv 论文链接（2605.12129 / 2605.26731）与 2026 年发布节奏，我未逐条核对 arXiv 真伪；"1,596 tests"、"OpenClaw/Hermes 采纳"等仅 README 声称；大量子命令（skill-router、tool_adapter、grounding 脚本）只列名未附用法示例。报告以 README 描述为准。

---

## 2. 能力矩阵：三个竞品共同缺失、而 wm 独有的能力

| 能力 | cozempic | artifact-guard | helm-agent-ops | wm 的实现 |
|---|---|---|---|---|
| **策略分级（G1-G4 + cleanup 模式）** | 有"3 处方档/4 档修剪阈值"，但是**会话修剪激进度**，不是文件价值策略 | 有 5 类分类，但只是**报告分类**，不驱动执行边界 | 有执行档案（blast radius），是**命令级**授权 | `metabolism.json` 声明式分级，clean 严格按 grade 执行，G3 需 approve+approver |
| **回收区回滚（先移动后恢复）** | 有 `.jsonl.bak` 备份，但**无 rollback 命令**（README 未列） | **无任何撤销**（`--delete-safe` 是真删除） | 有 checkpoint，但恢复是**整区快照**级，无逐文件校验恢复 | 回收区 + 逐文件 SHA-256 + `rollback <run_id>` 拒绝覆盖已存在路径 |
| **哈希链审计（篡改检测）** | 无（README 未提及任何审计链） | 无 | 有"原子 ledger"，但**无哈希链校验**命令 | `verify` 校验 journal 哈希链 + 运行清单，检测任何编辑 |
| **健康分（0-100 可徽章/CI 门禁）** | 有 token 上下文百分比，**非综合分** | 无 | `health` 是**模型健康探针**，非工作区分 | `wm health --json/--badge`，4 维加权，CI 模板可设阈值失败 |
| **MCP 服务** | 有（plugin 提供 MCP tools），但**绑定 Claude Code** | 无 | 有 tool/MCP adapter 注册表，但**非独立 MCP server** | `wm mcp` 零依赖 stdio server，agent-agnostic |
| **agent-agnostic（不绑定运行时）** | ✗ 深度绑定 Claude Code（hooks、session 格式） | ✓ 通用（4 种 agent 集成） | ✓ 通用（"不替换你的 agent"） | ✓ 纯文件/策略驱动，任何 agent 都能调 |

**独有能力汇总**：
- **cozempic 独有**：18 条会话修剪策略组合器、guard 守护进程 4 档阈值 + safe-point 保护、行为摘要（digest）注入记忆、Agent Teams 检查点、会话级 doctor 修复、reload+resume、self-update。
- **artifact-guard 独有**：会话基线快照（start→status→finish 生命周期）、隐私敏感模式（sensitive 优先于 git 追踪）、markdown 会话结束报告、git ls-files 感知分类。
- **helm 独有**：执行档案+命令 guard、任务状态机、文件化记忆+可解释检索、技能生命周期、工作流契约、影子模式报告、隐私 tokenize、模型健康探针、循环/技能准入。

---

## 3. 可执行的借鉴点（7 条）

1. **借鉴 cozempic 的"阈值阶梯守护"**：wm 目前只有 cron 定时。可加 `wm guard --daemon`（或 `--watch`）：按磁盘压力/回收区占用分级——软档（如 <60% 可用）只跑 `audit` 并留报告、硬档（<40%）跑 `clean --grades G4 --dry-run`、临界档（<20%）才真正执行 G4。与现有 `--protected-window` 叠加即可复刻"分级修剪保护"。
2. **借鉴 cozempic 的 safe-point**：wm 的 clean/rollback 前做"占用检查"——检测工作区内是否有运行中的 agent 进程（pid 文件/锁）或文件被占用（Windows 上尝试打开失败即跳过），把 `--protected-window` 从"静态时段"升级为"动态在途保护"。
3. **借鉴 artifact-guard 的隐私感知分类**：在 `audit`/`init` 内置 `sensitive` 类别（`.env*`、`*credential*`、`*secret*`、`*.pem`、`*token*`），策略校验时**拒绝**把 sensitive 路径注册为 G4，audit 报告单列"敏感文件发现"区块——wm 现在完全无此视角，而这正是"工作区卫生"的隐私短板。
4. **借鉴 artifact-guard 的 git-aware 分类**：`audit` 增加 git 检测：tracked 文件默认视为受控（相当于 G2），只有 untracked 文件才按 policy 分级；非 git 仓库回退到纯模式匹配。这让 `wm init` 的自动注册更不容易误伤源码。
5. **借鉴 artifact-guard 的会话基线生命周期**：增加 `wm session start` / `wm session finish`：记录一次 agent 会话内新建/修改/删除的文件清单，finish 时产出"本会话可回收工件"报告（复用现有回收区做 dry-run 移动）。wm 目前只有"基于 retention 的常驻策略"，缺少"本次会话产生了什么"的即时视角——正好补上 `micro_metabolism.py` 的端循环仪式。
6. **借鉴 helm 的执行档案门控**：给 `clean` 加 profile 参数：`wm clean --grades G4 --profile safe|full`，profile 白名单限制单次可触达的 grade×cleanup 组合（如 safe 只允许 G4+auto），防止策略误配置时一次清扫过界；并在 journal 记录所用 profile。
7. **借鉴 helm 的 shadow-report 累积模式**：`clean` 增加 `--shadow` 累积账：持续记录"本可回收但未执行"的字节/条目（dry-run 结果入 journal），`wm health` 可纳入"策略过松"维度（如连续 N 天 shadow 存量超过阈值 → 健康分扣分并提示收紧 retention）。这把 wm 的一次性 dry-run 变成闭环度量。
8. **借鉴 helm 的 reconcile 漂移检测**：增加 `wm reconcile`：对照 `metabolism.json` 与实际目录布局，报告三类漂移——规则指向的路径已不存在、目录存在但无规则覆盖（未注册泄漏）、默认保留清单与注册条目冲突。与 `verify`（链完整性）互补，形成"规则健康"与"数据健康"双体检。

---

## 4. 总结

三个竞品与 workspace-metabolism 并非同一物种：**cozempic 是"会话内"减脂**（修剪 Claude Code 的 JSONL 消息，分级维度是修剪激进度，深度绑定单一运行时），**artifact-guard 是"会话间"的一次性生命周期**（基线→分类→报告，有隐私意识但无历史、无撤销、无策略文件），**helm 是"运行时外"的运维层**（治理 agent 要执行的命令、任务与知识，覆盖最广但与文件卫生只有 checkpoint 一个交叉点）。wm 的独特身位在于它独占"**可回滚的声明式文件策略**"这条轴线：G1-G4 策略分级、SHA-256 校验的回收区回滚、哈希链审计、0-100 健康分、agent-agnostic 的 MCP——这五项中没有任何一个竞品完整具备。三个竞品各自最强的可借鉴点分别是：cozempic 的阈值守护+在途保护（主动化）、artifact-guard 的隐私与 git 感知分类（补齐 wm 的隐私短板）、helm 的执行档案与影子累积模式（把 dry-run 变成治理闭环）。若 wm 吸收这三点，就同时获得了"主动、隐私、可治理"三个当前缺失的维度，且不牺牲其独有的安全回滚与审计根基。

**证据可信度说明**：wm 命令面直接来自本地 `cli.py` 源码（最高可信）；三个竞品命令面全部来自其 README 原文（cozempic/artifact-guard 抓自 GitHub raw main 分支，helm 抓自 PyPI JSON 描述），命令名未做任何杜撰；凡"未在公开资料中证实"处已逐条标注（如 cozempic 用户量徽章、helm 的 arXiv 链接与测试数、artifact-guard 的多会话历史为规划项）。
