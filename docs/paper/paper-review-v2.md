# 论文审稿记录：Agentic Metabolic Engineering（v2, 2026-08-18）

> 审查对象：`agentic-metabolic-engineering-paper-v2.md`（英文版 + 中文版）。
> 审查方法：全部学术引用与行业数据经 web_search + 原文抓取逐条核实；GitHub/npm 仓库经 registry API 验证。
> 配套文档：修正版参考文献见 [references-corrected.md](references-corrected.md)；范式对比与优化见 [paradigm-comparison.md](paradigm-comparison.md)。
> **应用状态（2026-08-18）**：本文件"剩余问题"一节所列修正已全部应用到论文存档（编号映射、参考文献替换、vanish 删除、V.B 过度声称、摘要 orphaned processes、SABER 引文、zclean 细节、finishkit [17]）。范式对比与优化建议尚未应用，见 paradigm-comparison.md。

## 结论

**v2 核心内容可以投稿**：16 条引用中 11 条完全准确、引文逐字属实；剩余问题集中在参考文献条目的准确性（3 条内容错误、1 条需删、1 条存疑）与格式细节。**投稿前必须修复的 5 处：**
1. [12] zclean GitHub 链接 404 → `github.com/TheStack-ai/zclean`
2. [13] agent-gc GitHub 链接 404 → `github.com/williamjeong2/agent-gc`
3. [14] AI Harness Engineering 标题虚构 → "A Runtime Substrate for Foundation-Model Software Agents"
4. [16] SABER 标题虚构 → "Small Actions, Big Errors — Safeguarding Mutating Steps in LLM Agents"
5. vanish 描述不可靠（npm `vanish` 是 2015 年无关包；本项目 competitive-analysis.md 亦注明未能核实）→ 整句删除

## v1 → v2 已修正 ✅

| 项目 | 状态 |
|---|---|
| 摘要混入量化系统术语（look-ahead freedom） | ✅ 已删除 |
| 94% → 93.5%（New Relic 官方数字） | ✅ |
| 92% 补美国限定（76% 全球）+ JetBrains 来源 | ✅ |
| 41% "pushed to production" 无出处 → 改为 "produced globally" | ✅ |
| 86% 查无出处 → 换 63%（finishkit） | ✅ |
| Forbes 虚构引文 → 删引号改转述 + 真实文章入参考文献 | ✅ |
| ACM-SE 2026 描述 → NIST AI RMF 视角（DOI 10.1145/3746467.3801530） | ✅ |
| SABER "file creation" → "file deletion" | ✅ |
| 代谢债务 vs agent debt 定义区分 | ✅ |
| 回滚声明 → 补充字节级验证描述 | ⚠️ 见下方剩余项 |

## v2 剩余问题（详见 references-corrected.md）

### 🔴 硬伤（投稿前必须修）
1. 参考文献 [12][13][14][16] 条目内容错误（见上表）。
2. 参考文献 [2]（New Relic）、[9]（Forbes）、[11]（JetBrains）在正文中从未以 [n] 标注；编号未按首次出现顺序。
3. vanish 描述不可靠，建议删除。

### 🟠 建议修
4. Kingbird [10] 标题未能核实 → 改为"Kingbird Solutions（Q1 2026），经 SoftwareSeni（Wondrasek, 2026-05-21）报道"。
5. V.B "all 240 recycled files are SHA-256 recoverable… verifies this at the byte level" 过度声称——基准脚本只对 run00_draft.py 一个文件做字节级回滚验证。

### 🟡 可选
6. 摘要 "and orphaned processes"——工具不管理进程，建议删除。
7. SABER 引文 "concentrate around a small number of mutating actions" 非原文（原文："failures cluster at a small slice of mutating steps"），去引号或改原文。
8. 63% 数据引 finishkit（行业聚合博客）——加参考文献条目 [17] 并注明 "industry aggregation"，或挖一手来源。
9. 正文引用 "four-condition filter"（zclean）在 zclean README 中查无出处，建议删除该细节。

## 已核实无误（无需改动）

Waseem et al.（第一作者确认）、综述引文（逐字）、Position 引文（逐字）、LemonHarness 引文（逐字，Ren et al. 属实）、Workspace-Bench（Tang et al. + 全部数据）、AgentFold（Tongyi Lab, Alibaba + 引文逐字）、New Relic 报告存在性与 "agent debt" 定义、93.5%/78%/88%、91.5%（Kingbird Solutions Q1 2026）、JetBrains 2026 调查、ACM-SE 2026 论文存在性。
