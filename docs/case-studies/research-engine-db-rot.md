# Case Study: Taming Database Rot in a Research Engine with `wm slim`

> **案例研究 · 中文为主，附英文摘要**
> 时间：2026-08-31 ~ 2026-09-01（两天）
> 涉及版本：workspace-metabolism v0.3.0（`wm slim` 由此案例诞生）
> 脱敏说明：以下均为真实发生的数字与序列，但隐去项目名、服务器信息、账号、密钥与 IM 机器人细节。

---

## Abstract

A production research engine (an 8-core / 32 GB cloud box running a
minute-by-minute "factor factory") suffered three distinct failure modes in
two days: a stall/recover cycle caused by deterministically-dead work units,
minute-long query stalls caused by a 20.7 GB work-ledger database, and
silently-dead scheduled jobs nobody consumed. This case study records how we
fixed each mode, why the database needed a first-class "slim" operation
instead of another cron hack, and — most importantly — what we found when we
used our own tool (`wm slim`) to verify the fix: the policy was stripping the
wrong (empty) JSON field while 98 % of each row's size sat in two fields the
policy never touched, plus two path-matching bugs that only real usage
exposed. The result is `wm slim` in workspace-metabolism v0.3.0, a
policy-driven, journaled, dry-run-by-default in-place SQLite trimming
operation.

---

## 1. 背景：一个跑在云上的研究引擎

一个量化研究引擎以分钟级 tick 在云端跑"因子工厂"：每个 tick 认领一批
"工作单元"（work unit），在 7 个 worker 上计算候选因子，把结果写进一个
SQLite 工作台账（work ledger）。日积月累，台账里存着每个工作单元的评估
结果 JSON（checkpoint）。这套系统的运行窗口是傍晚到次日清晨，白天停机。

两天里它出现了三种完全不同的"卡死"，逐一记录如下。

## 2. 故障一：每个纪元尾巴上的"停滞→恢复"循环（死单元）

**症状**：监控每 15 分钟报一次"研究停滞"，几十分钟后又自己"恢复"；一个
晚上重复 2~4 次。

**根因**：候选网格里有一批固定的 (分片, 种子) 位置，其证据段在整份数据
归档里都没有任何行情——它们**每个纪元都确定性失败**（评估器返回
"IC 观测不足"）。观测事实：

- 连续 12+ 个纪元，**每个纪元恰好 807 个**工作单元 `failed_permanent`；
- 同一个失败位置曾被重试 **251 次**（跨纪元累积）；
- 当夜间回填把某个纪元"排干"到只剩这些死单元时，每一批认领（64~256 个）
  全部失败 → 停滞监控连续 15 分钟零成功 → 告警；随后新纪元注册进新鲜
  单元 → "恢复"。如此循环。

**修法**（注册层排除）：在注册工作单元前，从台账学习"最近 3 个纪元中 ≥2
次 failed_permanent 的位置"，直接不注册它们。实测：精确学到 **807 个**、
零误伤、零泄漏；修后当夜"连续零成功批次"计数恒为 0，循环消失。

> 启示：**监控告警的是症状（停滞），不是病因（死单元进网格）**。把
> 确定性失败从源头排除，比任何告警都便宜。

## 3. 故障二：20.7 GB 的账本数据库（膨胀）

**症状**：一个 tick 的内核 IO 等待持续 25 分钟（进程 D 状态），停滞告警
再次触发；磁盘 IO 长期 120+ MB/s；引擎"恢复"后 tick p95 达 **1832 秒**。

**根因**：工作台账 SQLite 膨胀到 **20.7 GB**。实测单条 checkpoint：

| 字段 | 大小 | 占比 |
|---|---|---|
| `ic_by_session`（逐 session 的 IC 序列） | ~21.3 KB | 61% |
| `point_in_time_scores`（逐代码 PIT 分值） | ~13.1 KB | 38% |
| 其余全部字段（指标、公式、哈希…） | ~2 KB | <2% |

而架构早就知道这两个字段重：裁决管线把它们列为"重字段"，只在纪元**自身
关窗**时按需重读（轻量投影明确排除）。**但没有任何保留策略处理它们**——
旧纪元关闭后这些字段永远躺在库里，无人再读。

**修法分两层**：

1. **写入侧**：新 checkpoint 不再存持久化后无读取方的字段（本次案例里
   `factor_observations` 是空字段，直接剥离——虽然事后证明它本来就为空）。
2. **存量侧（关键）**：需要一个"库内瘦身"操作——不是删文件（台账里
   work_ledger 是 `cleanup: never`，文件本身不删），而是**在库里剥离旧行
   的重字段并回收页**。

正是这第二个需求，催生了 `wm slim`（见第 6 节）。

## 4. 故障三：静默死掉的定时任务（无人消费）

**症状**：一项周日 21:30 的"全市场股票冗余周报"连续 10 天零产出，**没有任何
东西因此异常**——直到审计才发现它死了。

**根因**：它的日志文件被 root 占用（644），cron 每次触发即静默退出；它的
输出没有任何消费方（池卫生早已被构建器内建保证），唯一"消费"它的是链内
兄弟步骤。它死了，系统用沉默证明了它不再被需要。

**修法**：停用 cron，代码保留按需手动；并把"输出无人消费检测"做成常态
巡检（每周自动扫一遍研究数据集，检查每个输出是否有代码消费方）。

> 启示：**这套系统对"新增"有严格门禁，对"退役"没有任何机制**——cron
> 一旦上线，除非显式裁决停用，否则永远空转。第一次系统性"无人消费"
> 审计就裁掉了 4 项这样的任务。

## 5. 对策一：研究层心跳（监控）

三起事故暴露的共同盲区：现有停滞监控只覆盖"锁被持有但 15 分钟无批次"，
覆盖不了"引擎整体缺席"和"数据库慢读风险"。于是加了一个轻量心跳：

- 研究窗口内每 15 分钟一次；
- 读取全部**有界**（SQLite pragma 元数据、索引计数、日志尾部——绝不触发
  全表扫描，这是 20 GB 库的教训）；
- 输出：引擎进程数、锁龄、待处理单元、**DB 尺寸与增长**、tick p95、
  末次 tick 时间；
- 告警阈值：DB ≥8 GB 预警 / ≥15 GB 临界、日均增长 ≥3 GB、tick p95 > 600 s、
  引擎缺席 >30 分钟。

**效果立竿见影**：上线当晚心跳同时触发 `db_size_critical`（20.8 GB）与
`tick_slow`（p95 1832 s）两条告警——恰好复现了事故模式，证明监控真的
在看着数据库。

## 6. 对策二：`wm slim`——把数据库瘦身变成一等公民

项目本来就有开源的文件代谢工具 `workspace-metabolism`（策略驱动、回收区、
哈希链审计、零依赖）。数据库膨胀发生后，正确的做法不是再写一个平行的
repo 内脚本，而是**把"库内瘦身"做进现有工具**：

- **`wm slim`**（v0.3.0）：策略（`db_slim`）驱动的 SQLite 库内修剪——
  不删行、不删文件，只重写一个 JSON blob 列、剥离策略列出的键；
- **keep_recent**：参考列最新 N 个不同值对应的行不动（如最新 3 个纪元）；
- **VACUUM**：可回收量超过阈值才回收页；
- **默认 dry-run，执行必须 `--yes`；每步进哈希链审计**（`wm verify` 可验）；
- 零依赖、CLI 覆盖每个策略字段、标识符按数据库 schema 校验（无自由 SQL）。

部署形态：每天维护窗口（引擎停机后）跑一次
`wm slim --db <work-ledger> --registry <policy> --yes`。

## 7. 用自己工具的回报：检测效果时发现三个真问题

第 6 节上线后，我们按流程"检测一下效果"——结果这轮检测本身就是案例里
最值钱的部分：

### 7.1 监控立即证明自己
心跳上线当晚即报出两条临界告警（见第 5 节）。

### 7.2 策略剥错了字段
抽查真实 checkpoint 之前，strip_keys 里只有 `factor_observations`——但
**marathon 路径的 checkpoint 里根本没有这个字段**（它从来是空列表）。
实测单行 34.9 KB 中 **98% 是 `ic_by_session` + `point_in_time_scores`**，
而这两个字段正是"关窗后无人读"的重字段。修正策略后，预计剥离 ~13 万
旧行 × ~33 KB ≈ **5~13 GB** 回收量。**不实测，永远不知道自己在剥什么。**

### 7.3 两个策略匹配 bug（只有真实使用才会暴露）
- **遮蔽 bug**：通用条目 `data` 以子串命中，先于精确条目 `data/app.db`
  返回 → 拿到默认空策略；
- **目录形态 bug**：真实部署的条目是**父目录**（`data/research/work_ledger`），
  而匹配逻辑只查了"文件路径的后缀"——父目录条目永远匹配不上。单元测试
  只覆盖了文件形态，所以全绿也漏了它。

两个 bug 都以"段级后缀匹配（文件 + 父目录双基准）+ 最长条目优先"修复，
并补上了真实部署形态的回归测试（107 全过）。

> 启示：**"用起来怎么样"和"真的在生产里用"是两回事**。让工具先在自己的
> 事故里跑一遍，比任何 code review 都能更快暴露边角。

## 8. 数据与时间线（脱敏）

| 时间 | 事件 | 关键数字 |
|---|---|---|
| D1 凌晨 | 死单元停滞循环第 N 次复发 | 807 死单元 / 纪元；重试 251 次 |
| D1 晚 | DB 膨胀事故：tick D 状态 25 分钟 | DB 20.7 GB；tick p95 1832 s |
| D1 晚 | 写入侧剥离 + 心跳上线 | 心跳当晚双告警 |
| D2 | `wm slim` v0.3.0 落地并部署 | 107 测试全过 |
| D2 | 效果检测：剥错字段 + 2 个匹配 bug | 实测 98% 重字段；修正后预计回收 5~13 GB |

## 9. 教训

1. **告警的是症状，修的是病因**：死单元从注册层排除，比任何监控便宜。
2. **数据库也会烂**：文件代谢管不了库内的腐化——需要 `slim` 这样的一等
   公民操作（不删文件、策略驱动、审计留痕）。
3. **监控要有"缺席"和"健康"信号**：不止"出事了没有"，还要"它还在不在"、
   "它是不是正在变慢"。
4. **没有退役机制的系统会积累死任务**：把"输出无人消费检测"做成常态。
5. **用自己工具的回报大于预期**：效果检测发现了剥错字段与两个匹配 bug——
   真实使用是最终测试。

---

*This case study is published in the repository that grew the fix. The
numbers are real; the names are not.*
