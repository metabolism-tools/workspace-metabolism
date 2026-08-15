# 草稿状态：待你审改后发布（首发知乎）

> 标题候选：
> A. 《Agentic Metabolic Engineering：Vibe Coding 的下半场》
> B. 《AI 写代码留下的烂摊子，需要一个「代谢系统」来收拾》
>
> 发布前要做的事：
> 1. 把文中的仓库/PyPI 链接确认一遍（已填好，复制即用）
> 2. 在知乎编辑器里把「代码块」「表格」「小标题」重新整理一下（知乎粘贴 Markdown 后需要手动微调）
> 3. 配图建议：在文末或开头放一张 `wm audit` 的真实终端截图（仓库 README 里有现成的 docs/terminal-preview.png）
> 4. 建议发布时间：和 Show HN 同一天（北京时间周二到周四晚 9–12 点），先发知乎再发 HN，或同晚一起发

---

# Agentic Metabolic Engineering：Vibe Coding 的下半场

最近一年，大家应该都感受到了：AI 写代码真的很爽，但写完代码之后的**工作区**越来越乱。

废弃的实现方案、临时补丁、重复的依赖锁文件、测试桩、半途而废的重构……AI 每跑一轮，就会留下一些「中间产物」。代码在增长，但工作区膨胀得更快。时间一长，整个项目就像一个没人打理的堆肥场——而下一轮 AI 还得在堆肥场里面干活。

这不是小事。上下文被污染、构建越来越慢、旧方案和新代码互相打架。**问题不在 AI 写代码，而在代码之外的那些东西没人管。**

## 传统做法，为什么都不太行

最常见的答案是：写个脚本，到点 `rm -rf`。

这太粗暴了。AI 的下一轮迭代，可能恰恰需要那个看起来「已经废弃」的文件。删掉的不只是一个文件，还有它的来龙去脉——什么时候产生的、为什么被放弃、还能不能复用。这相当于把可能有营养的中间产物直接烧掉。

另一种做法是「什么都不删」。结果就是工作区持续腐烂，Agent 的上下文越来越脏，每轮循环越来越慢。

还有人选择「每轮都从干净沙盒重来」——成本极高，而且把最有价值的历史也一起扔了。

至于「什么都往 git 里塞」——版本库会变成另一个垃圾场。

**清理是必要的，但「直接删除」不是答案。**

## 我的提议：Agentic Metabolic Engineering

我提出一个框架，叫 **Agentic Metabolic Engineering（智能体代谢工程）**——用生物学的「代谢」来理解 AI 工作区：它不是一堆文件的静态存放处，而是一个有生命、有容量上限的系统，需要的是**消化**，而不是简单的**删除**。

它由四个阶段构成：

| 阶段 | 命令 | 做什么 |
| --- | --- | --- |
| 分解代谢 Catabolism | `wm audit` | 体检：扫描工作区，给废弃草稿、重复缓存、半成品贴上「营养标签」，只诊断不破坏 |
| 隔离消化 Sequestration | `wm clean` | 把确认过期的内容移入回收区，**绝不直接删除**——今天看着没用的，下一轮可能就用上了 |
| 校验 Verification | `wm verify` | 哈希链审计日志：每个文件何时产生、何时被移动，全程可追溯，篡改会被发现 |
| 合成再生 Anabolism | `wm rollback` | 当新的迭代发现旧方案其实更好时，把回收区的内容重新注入工作区——废料变成原料 |

整套机制的基石是**策略即代码**：一份 JSON 策略文件给每个路径分级（G1 永不触碰 / G2 只优化 / G3 审批+引用检查 / G4 自动），工具只做策略允许的事，绝不多做。

说明一下：这个比喻不是我们发明的（「信息代谢」60 年代就有人提出，「代谢工程」是合成生物学的成熟学科）。我们做的是把这个比喻用到 AI 工作区治理这个具体场景，并给它一个可审计的工具。**我们认领的是框架，不是这几个字。**

## 它在 AI 工程栈里的位置

这几年，AI 编程领域出现了一套工程范式：

| 层级 | 范式 | 核心问题 |
| --- | --- | --- |
| L1 | Prompt Engineering | 怎么跟模型说话？ |
| L2 | Context Engineering | 给模型看什么？ |
| L3 | Harness Engineering | 怎么让 Agent 稳定可靠？ |
| L4 | Loop Engineering | 怎么让 Agent 自己持续跑下去？ |
| **L5** | **Agentic Metabolic Engineering** | **每一轮循环之后，工作区剩下了什么？** |

如果说 Harness 是 Agent 的骨架，Loop 是它的心跳，那么代谢系统就是它的**消化系统**——处理 Agent 吃进去和排出来的东西，让工作区能活到下一轮。

一个没有代谢的 Loop，是无限产出废物的系统；一个没有代谢的 Harness，是装满自身碎屑的笼子。

## 一个新词：代谢债（Metabolic Debt）

大家都很熟悉「技术债」（technical debt）——仓促代码的代价。我想提出它的孪生概念：**代谢债（Metabolic Debt）**——无人管理的副产物累积成的代价。

代谢债和技术债一样，需要被看见、被分级、被偿还：

| 代谢债概念 | 工具对应 |
| --- | --- |
| 债务体检 | `wm audit`：工作区多大、有什么候选、磁盘告警 |
| 债务分级 | G1–G4：什么永不碰，什么可以回收 |
| 债务展期 | 回收区：不立即销毁，保留期到了再说 |
| 债务偿还 | `wm rollback`：新循环发现旧方案有用，重新取回 |

工作区腐烂（workspace rot）就是代谢债违约的后果。而它的反面不是「空」，是「对」——对的文件，在对的时间，带着可验证的历史。

## 工具：workspace-metabolism

这个框架的参考实现是一个零依赖的 Python 命令行工具，`workspace-metabolism`：

```bash
pip install workspace-metabolism
wm --help
```

体检是它的核心动作，而且输出机器可读：

```bash
wm audit --json | jq '.summary.growth_mb, .summary.recycle_ratio_pct, .summary.journal_chain_ok'
```

```json
{
  "files": 2, "size_mb": 0.0, "growth_mb": null,
  "candidates": 2, "candidates_g4_mb": 0.0, "candidates_g3_mb": 0.0,
  "unregistered": 0, "disk_alert": false,
  "recycle_files": 0, "recycle_mb": 0.0, "recycle_ratio_pct": 0.0,
  "journal_entries": 1, "journal_chain_ok": true
}
```

仓库：https://github.com/metabolism-tools/workspace-metabolism

PyPI：https://pypi.org/project/workspace-metabolism/

文档：完整的哲学定义在 docs/philosophy.md，完整叙事在 docs/narrative.md（英文）。

## 最后

我提出这个框架，不是为了证明自己正确，而是想开启一场对话：**当 AI 编程成为常态，那些副产物到底应该被怎样对待？**

如果你有更好的比喻、更好的做法，欢迎来 Issue 里讨论。工具是参考实现，范式比工具大——它值得被更多人一起定义。

---

*（草稿结束。发布前请通读一遍，把「我提出」改成你舒服的措辞；文末可加一句个人介绍，比如「一个在 AI 编程时代折腾工具的普通人」。）*
