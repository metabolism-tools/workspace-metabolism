# WBS / 仓库组织 / 分支 CI / README 模板（2026-09-02 讨论存档 3/3）

> 来源：产品/策略外部提案原文存档。含仓库拓扑、MVP1-3 WBS、分支与CI门禁、README/PR/CONTRIBUTING 模板。

# workspace‑metabolism + holdout‑labs WBS任务拆解 + GitHub仓库组织方案 + CI/分支策略

> 约束：内核主仓库保持最小、稳定；所有样板、模板、基准、适配器全部独立子仓库；**内核API不随便膨胀；易用性全部放在外围仓库**。

## 一、workspace‑metabolism 仓库拓扑（多仓库分离，避免主仓库臃肿）

```
workspace-metabolism/
├─ workspace-metabolism        # 【主仓库｜内核】引擎、core逻辑、policy解析、journal审计、wm-gate
├─ wm-presets                  # 【子仓库】官方预制policy模板库
├─ wm-dashboard                # 【子仓库】静态HTML仪表盘（只读，无写权限）
└─ wm-docs                     # 【子仓库】文档：灾难案例、运维手册、教程
```

职责边界：主仓库 = 引擎/扫描/journal/gate/policy lint核心；禁止放入大量示例policy、静态html、教程文档。
wm-presets = 经CI lint校验的预设policy（`wm init --preset xxx`引用）；wm-dashboard = 只消费wm输出的json/metrics，无任何删除能力；wm-docs = 故事/教程/运维。

### 分支策略
- `main`：稳定发布分支，仅接受经过完整测试的合并；打tag发布。
- `develop`：集成分支；`feature/*`；`hotfix/*`。
> 规则：所有新功能先过develop再合main；禁止直接往main提交。

### CI门禁（主仓库）
1. 单元+集成测试；2. `wm policy lint`校验内置样例policy；3. 静态代码检查+安全扫描；4. 多平台构建（linux/amd64, arm64, macos）；5. 任何修改graveyard自动purge逻辑/默认删除行为的代码需人工评审。

### 发布规范
语义化版本；每个release附变更日志、二进制、风险提示（gate仅观测；默认不自动purge）。

## 二、holdout‑labs 仓库拓扑

```
holdout-labs/
├─ holdout-labs                #【主仓库｜内核】pit-adjuster、lookahead-free、factor-qc、falsification-ledger
├─ holdout-quickstart          #【子仓库】样板流水线、notebook、poetry模板、docker-compose
├─ pit-adjuster-benchmark      #【子仓库】PIT真值基准测试套件
├─ holdout-adapters            #【子仓库】数据源适配器（tushare/akshare/Wind等）
├─ holdout-report              #【子仓库】markdown/pdf报告生成器
└─ holdout-docs                #【子仓库】回测陷阱百科、教程、SOP
```

### CI门禁（holdout主仓库）
1. 单元测试；2. pit-adjuster-benchmark基准套件（PIT差异超阈值阻断合并）；3. 静态检查；4. L2预注册/PIT核心逻辑改动需人工评审。

## 三、两个项目共用治理规则
1. **内核层 vs 接入层铁律**：内核改动多人评审；接入层可快速试错。
2. **叙事顺序固定**：先痛苦案例 → 工具用法 → 底层范式哲学。
3. **禁止为star牺牲底层哲学**（wm绝不自动purge、gate只观测；holdout绝不降级L2、不做因子淘金、不承诺收益）。
4. **社区贡献策略**：优先鼓励模板/适配器/样例/benchmark用例/文档；谨慎接受内核API变更。
5. **Issue分类标签**：`kernel-bug` / `upper-layer` / `feature-request-kernel` / `feature-request-upper`。

---

# README 模板（workspace-metabolism 主仓库建议稿）

```
# workspace-metabolism
> Agent工作空间代谢治理引擎
> 🚨 **重要安全声明**
> 1. 默认不会物理删除任何文件，所有待清理文件先移入graveyard（墓地），支持回滚；**不会自动purge**，物理删除必须人工执行。
> 2. wm-gate 仅为**Agent文件行为观测探针**，不能拦截绕过MCP的进程操作，不充当安全网关。
> 3. 本工具是治理系统，不是一键清理工具；生产环境请先充分测试。

## 📌 项目定位
面向AI-Agent持续运行场景，解决：Agent大量生成零散临时文件/目录污染；文件生命周期无审计无法回溯；清理要么粗暴误删要么放任膨胀；缺少声明式策略、大量手写shell难以维护。
核心范式：**代谢治理，埋葬优先，审计可追溯，可逆优先**。

> ⚠️ 仓库边界说明
> - ✅ 本仓库：内核引擎、扫描、policy解析、journal审计账本、wm-gate观测探针
> - ❌ 不存放：预制策略模板、静态仪表盘、完整教程文档（外围：wm-presets / wm-dashboard / wm-docs）

## ✨ 核心能力
声明式policy（TTL生命周期）；bury/rollback不直接删除；哈希审计journal；wm-gate MCP观测；policy lint静态校验（冲突/性能风险）；增量扫描。

## 🚀 快速上手
### 新手模式（交互式向导，推荐）
wm init --guide ./my-agent-workspace
### 专家模式
wm init --expert ./my-agent-workspace
### 官方预制模板
wm init --preset ai-agent-sandbox ./agent-ws
### 审计与导出
wm audit / wm audit --html audit-report.html / wm policy lint metabolism.json

## 🤝 贡献指南
内核改动（本仓库）：扫描引擎/journal/policy解析/wm-gate核心——需完整测试；禁止修改默认安全行为；重大变更多人评审。
上层改动：模板/仪表盘/文档/示例 → 对应子仓库。
Issue标签：kernel-bug / upper-layer / feature-request-kernel / feature-request-upper

## ⚠️ 已知限制
1. wm-gate只能观测经由MCP调用产生的文件操作，无法拦截直接读写文件的进程。
2. 跨机器/跨文件系统的journal审计存在边界。
3. graveyard仅本地存储不自动备份；生产建议定期WORM归档。

## 📄 License
MIT
```

# README 模板（holdout-labs 主仓库建议稿）

```
# holdout-labs
> 开源量化研究质检基础设施：对抗前视泄露、过拟合、p-hacking，构建可审计的研究证据链

> 🚨 **重要免责声明**
> 1. 本工具**只校验研究流程严谨性，不预测收益，不构成任何投资建议**。流程合规 ≠ 未来实盘有效。
> 2. 不内置回测引擎，不提供因子淘金功能；仅做质检与证据记录。
> 3. L1为探索模式，L2为严格预注册验证模式；严禁将L1批量探索结果当作验证结论。

## 📌 项目定位
量化研究隐形陷阱：事后复权代替PIT；前视偏差；多重检验p-hacking；实验无记录不可复现。
模块：pit-adjuster（时点复权）；lookahead-free（前视扫描）；factor-qc（多重检验校正 PBO/FDR）；falsification-ledger（实验预注册账本 L1/L2）。

> ⚠️ 仓库边界说明
> - ✅ 本仓库：底层核心库（统计逻辑、PIT计算、账本核心API）
> - ❌ 不存放：完整流水线、适配器、报告生成、教程（外围：holdout-quickstart / pit-adjuster-benchmark / holdout-adapters / holdout-report / holdout-docs）

## 🚀 快速上手（普通用户建议直接使用 quickstart 样板仓库）
git clone https://github.com/holdout-labs/holdout-quickstart
cd holdout-quickstart && poetry install
poetry run python run_l1.py    # L1探索模式
poetry run python run_l2.py    # L2严格预注册模式
ledger-cli list / ledger-cli show <exp-id> / ledger-cli export-md <exp-id>

## ⚠️ 已知限制
1. 不能消除全部研究风险，只能识别可形式化缺陷；仍需研究员人工终审。
2. holdout-governance MCP仅用于沙箱Agent实验，不对外提供自动“因子盖章”。
3. 数据源质量影响质检结果；建议配合pit-adjuster-benchmark抽样校验。
```

# 通用 PR 模板（.github/PULL_REQUEST_TEMPLATE.md，两项目共用）

```
## 变更类型
- [ ] 🧠 **Kernel 内核改动**（主仓库核心逻辑：扫描引擎 / PIT计算 / 账本 / 统计模型）
- [ ] 🧩 **Upper-layer 上层接入层改动**（示例、模板、文档、适配器、仪表盘、样板流水线）
> 内核改动需要完整测试；上层改动请确认是否应提交到外围子仓库。

## 变更描述 / 关联Issue / 测试校验
### Kernel 内核改动
- [ ] 单元测试全部通过
- [ ]（workspace-metabolism）内置样例policy全部通过 wm policy lint
- [ ]（holdout-labs）pit-adjuster-benchmark基准套件通过，无超阈值差异
- [ ] 未修改底层安全/统计哲学（wm：无自动purge、gate仅观测；holdout：L2未降级、无因子淘金）
### Upper-layer
- [ ] 示例/模板可运行；文档更新完整，风险提示保留

## 风险说明 / 额外说明
```

# CONTRIBUTING.md 片段（仓库分离原则 + Issue标签 + 分支策略）

```
# 贡献指南
## 仓库分离原则
主仓库存放核心引擎/底层库，改动门槛高；外围子仓库存放模板/配置/示例流水线/UI仪表盘/数据适配器/文档教程。
> 提交模板、示例、文档优先提交到对应子仓库，不要往主仓库提交。

## Issue标签含义
- kernel-bug：内核核心逻辑bug，最高优先级
- upper-layer：问题属于外围子仓库，转对应仓库提issue
- feature-request-kernel：内核新增功能，需评审，不一定接受
- feature-request-upper：外围层功能，欢迎PR到子仓库

## 分支策略
- main：稳定发布，仅接受完整测试的合并，用于打tag
- develop：集成分支
- feature/*、hotfix/*
> 禁止直接提交代码到main分支。
```
