# ICSE 2027 NIER 投稿清单（Submission Checklist）

> 首次投稿专用。所有日期均来自 [ICSE 2027 官方页面](https://conf.researchr.org/track/icse-2027/icse-2027-new-ideas-and-emerging-results--nier-) 与 [会议主页](https://conf.researchr.org/home/icse-2027)（2026-08-18 核实）。
> 配套文档：投稿稿 [nier-icse2027.md](nier-icse2027.md)｜LaTeX [nier-icse2027.tex](nier-icse2027.tex)｜参考文献 [nier-references.bib](nier-references.bib)｜期刊版 [agentic-metabolic-engineering-paper-v2.md](agentic-metabolic-engineering-paper-v2.md)｜arXiv 公开版 [nier-icse2027-public.tex](nier-icse2027-public.tex)。

> **进度更新（2026-09-02，AI 侧已完成项）**：
> - ✅ A4 内容终检：引用编号 15/15 按首次出现顺序与 .bib 一一对应（tex 与 md 均已核）；摘要数字一致（2 vs 242 / 93.5% / 78% / 14–18%）；Future Plans 章节存在；四阶段表、结果表完整
> - ✅ A2 双盲扫描：tex 无作者名/邮箱/个人路径；真实仓库 URL 已注释（`% Restore for camera-ready`）；参考文献全为他人作品（zclean/agent-gc 属第三方，不泄露身份）
> - ✅ 篇幅估算：主文约 1500 词 + 2 表格，acmart sigconf 4 页限制内无风险
> - ✅ arXiv 公开版已生成：`nier-icse2027-public.tex`（去 anonymous、实名占位、恢复仓库链接、acks + AI 披露占位）
> - ✅ 卫生：`workspace-metabolism/workspace-metabolism/` 旧嵌套克隆已删除（不影响匿名镜像）
> - ⏳ 待办：本机无 LaTeX 工具链（pdflatex/bibtex 均未安装）——**编译需在有网环境用 Overleaf 或安装 MiKTeX/TeX Live 完成**

## 关键日期（北京时间约 +8h，AoE 截止按 UTC-12 换算，实际以官方为准）

| 事件 | 日期 | 状态 |
|---|---|---|
| 投稿截止 | **Fri 2026-10-23, AoE (UTC-12h)** | ⏳ 距现在约 2 个月 |
| 接收通知 | Fri 2026-12-18 | |
| Camera-ready 截止 | Wed 2027-01-20 | |
| 会议 | 2027-04-25 ~ 05-01，爱尔兰都柏林（Convention Centre Dublin） | |

提交系统：**https://icse2027-nier.hotcrp.com**

---

## 阶段 A：提交前（现在 → 10/16，提前一周完成）

### A1. 编译环境（本周）
- [ ] 安装 MiKTeX（或 TeX Live）+ 编辑器（VS Code + LaTeX Workshop / TeXstudio）
- [ ] 在 `docs/paper/` 下编译：`pdflatex nier-icse2027 && bibtex nier-icse2027 && pdflatex nier-icse2027 && pdflatex nier-icse2027`
- [ ] **主文 ≤ 4 页（含图表表格）**，参考文献单独 ≤ 1 页
  - 超页处理：压缩 II 节（现有方案不足）或 V 节（Related Work）措辞；两个表格改为紧凑格式
- [ ] 无编译警告级错误（undefined citation / overfull box 尽量清零）

### A2. 双盲匿名化（官方要求 "make a reasonable effort to anonymize"）
- [ ] 仓库匿名镜像：用 anonymous.4open.science 上传，论文里只放匿名链接（tex 中已注释真实 URL，恢复处见 `% Restore for camera-ready`）
- [ ] 清除 PDF 元数据中的作者/编译者信息（pdftk / exiftool / 在线工具检查）
- [ ] 正文、致谢、图表、文件名无作者姓名与可识别组织
- [ ] 参考文献无作者自己的论文（当前 15 条均为他人文献 ✅）
- [ ] 引用保留第三方工具链接（zclean/agent-gc 属他人作品，不泄露身份 ✅）

### A3. AI 使用披露（ACM Policy on Authorship 强制）
- [ ] 确认 AI 未列为作者
- [ ] 按提交表单要求如实披露 AI 辅助写作
- [ ] 作者对全部内容（尤其引用真实性）负最终责任——本项目引用已逐条核实 ✅

### A4. 内容终检
- [ ] 摘要与正文数字一致（2 vs 242、93.5%、78%、14–18%）
- [ ] 四阶段表、结果表、引用编号 [1]–[15] 与参考文献一一对应
- [ ] Future Plans 章节存在（NIER 强制要求）
- [ ] 通读一遍英文（可请人润色；AI 润色需与 A3 披露一致）

### A5. 作者与提交材料
- [ ] 作者名单确认（实质贡献者；AI 不算；第一作者 = 你）
- [ ] 通讯作者邮箱（用机构/常用邮箱，别用会暴露身份的个人昵称邮箱）
- [ ] 提前注册 HotCRP 账号（https://icse2027-nier.hotcrp.com）

### A6. 备份与提交（10/16 前）
- [ ] 论文文件全部 commit（建议单独分支 `paper-submission`）
- [ ] 最终 PDF 存档（文件名带日期，如 `nier-icse2027-final-20261016.pdf`）
- [ ] 提前 1 周提交（HotCRP 截止日拥堵/网络问题高发）

---

## 阶段 B：提交后（10/23 → 12/18）

- [ ] 确认 HotCRP 收到（提交状态显示完成）
- [ ] 可挂 arXiv 预印本（**不得**注明 "under submission to ICSE 2027"）
- [ ] **不得**同时投其他会议/期刊（一稿多投 = 学术不端）
- [ ] 并行推进期刊版：开始收集真实 agent loop 数据（Future Plans 第 1 项承诺的实验）
  - 计划：真实 coding agent 跑 N 轮循环 → 测文件增长 / 回收 / 回滚恢复 / 任务完成时间
- [ ] 若身份公开风险：暂缓公开宣传工具（评审期内）

---

## 阶段 C：12/18 收到通知后

### 若录用
- [ ] 通读审稿意见，逐条修改（写 rebuttal 不必——NIER 一般直接给决定；按意见改 camera-ready）
- [ ] 1/20 前提交 camera-ready：
  - [ ] 签署 ACM 版权表（ACM copyright form）
  - [ ] 恢复真实仓库链接
  - [ ] 致谢 + AI 披露声明
  - [ ] CCS 分类元数据（tex 中已含占位）
- [ ] 注册会议（作者注册费约 $500–900/人，学生便宜；查 ACM SIGSOFT CAPS 学生资助）
- [ ] 预订都柏林机票/酒店（会议期间尽早订）+ **爱尔兰签证**（中国护照需签证，材料提前 2–3 个月准备）
- [ ] 准备 10–15 分钟口头报告 + 海报（NIER 通常有 poster session）

### 若拒稿（常态，接收率约 20–25%）
- [ ] 记录全部审稿意见（免费专家咨询）
- [ ] 路径 1：修改后改投 FSE 2027 Ideas/Visions/Reflections 或 ASE
- [ ] 路径 2：推进期刊版投 IEEE TSE（v3 已备好，补真实数据后投；TSE 长度政策投稿前查官方指南）

---

## 新手十大坑（对照自查）

- [ ] 幻觉引用（✅ 已清理，投稿前再扫一遍）
- [ ] 双盲泄露：PDF 元数据 / 仓库链接 / 致谢名字
- [ ] 超页数（4 页硬限制，不可购页）
- [ ] 忘写 Future Plans（NIER 强制）
- [ ] 一稿多投 / 公开声称"在投 ICSE"
- [ ] 不披露 AI 辅助写作
- [ ] 截止日当天才提交
- [ ] 引用格式不统一（用 ACM-Reference-Format + .bib）
- [ ] 忘作者注册、签证、差旅预算
- [ ] 不备份、不 commit

---

## 提交包内容（10/16 前齐备）

| 文件 | 用途 |
|---|---|
| `nier-icse2027.tex` | 主稿源码（acmart sigconf + anonymous） |
| `nier-references.bib` | 15 条参考文献 |
| `nier-icse2027-final-YYYYMMDD.pdf` | 编译产物（匿名） |
| 匿名仓库链接 | anonymous.4open.science 镜像 |
| HotCRP 表单信息 | 标题/摘要/关键词/作者/披露声明 |

---

## 附录：arXiv 发布指南（2026-01 认证新政版）

> 依据 [arXiv 官方认证说明](https://info.arxiv.org/help/endorsement.html) 与 [2026-01-21 新政公告](https://blog.arxiv.org/2026/01/21/attention-authors-updated-endorsement-policy/)（2026-08-18 核实）。

### A. 时机决策（与双盲投稿的关系）

- arXiv 是**永久公开、实名**的档案系统（与 ICSE 双盲直接冲突）。
- **推荐路径**：**12/18 录用通知后**再发（或 1/20 camera-ready 前后）。评审期间匿名性最安全。
- 若坚持投稿当天发：ICSE 官方 FAQ 允许公开 arXiv（但**不得**写 "under submission to ICSE 2027"）；代价是审稿人可能搜到作者身份，双盲形同虚设。新手不推荐。
- arXiv v1 **不可删除**（只能撤稿，撤稿记录仍在）——发布前确认内容无误。

### B. 认证（endorsement）——2026 年 1 月新政

新用户向 cs.SE 提交**必须认证**，两条路径：

- **路径一（自动）**：① arXiv 账号绑定**机构邮箱**（学术/研究机构）② 在目标领域**已有认领的论文**。首次投稿者通常不满足。
- **路径二（人工背书）**：找一位在 cs.SE 领域的 **established arXiv author** 给你背书。
  - 找谁：你引用论文的作者最合适——arXiv 摘要页底部有 **"Which authors of this paper are endorsers?"** 链接，可查看候选背书人（如 Waseem、Tang 等作者）；或你的导师/学术界同事。
  - 怎么操作：注册 arXiv → 开始提交、选择 cs.SE → 系统生成 **endorsement request 邮件（含链接）** → 把链接发给背书人 → 对方登录 arXiv 批准。
  - 规则：一个类别一个正面背书即可；**不要群发骚扰**；arXiv 工作人员**不能**帮你背书；背书人需在相关领域有足够发文记录。

### C. 提交步骤（约 10 分钟）

1. 注册 arXiv 账号（arxiv.org，**实名**，建议关联 ORCID）。
2. 处理认证：按 B 找背书人。
3. 生成**公开版** `nier-icse2027-public.tex`：
   - 去掉 `anonymous` 选项（`\documentclass[sigconf]{acmart}`）
   - 填真实作者与单位（arXiv 显示真名）
   - 恢复仓库链接与致谢
4. 打开 https://arxiv.org/submit，上传 **.tex + .bib**（arXiv 自己编译，**不要**上传编译好的 PDF；无图片时这两个文件即可）。
5. 填写元数据：标题 / 作者（与 ORCID 一致）/ 摘要 / Comments（录用后可写 "To appear at ICSE 2027 (NIER)"；评审期间**不要**写 "under submission"）/ Subjects（**cs.SE**，可加 cs.AI）/ 许可。
6. 预览 arXiv 编译生成的 PDF → 确认无误 → 发布。
7. 记录 **arXiv ID**（如 arXiv:26xx.xxxxx），补进论文与 README。

### D. 许可与版权时序（ACM 关键）

- **许可**：推荐 arXiv 默认 "perpetual, non-exclusive license"；CC BY 4.0 亦可。
- **时序**：在 camera-ready 签署 **ACM 版权表之前**发布 arXiv v1（用录用稿版本）——完全合规，之后无需再处理版权问题。
- 若已签版权表：按 ACM 政策可发布 "accepted author manuscript"（带 DOI），但流程较绕，新手走"先发 arXiv 再签版权表"最省心。
- 录用后可用 **v2 更新** arXiv 版本并补 Journal Reference 字段。

### E. 注意事项

- arXiv 是预印本、非同行评审——发布后在论文和 README 中标注 "preprint"。
- 2026 年起 arXiv 对 AI 辅助论文明显收紧（新政目的即"stemming the flood of low-quality submissions"）：我们的论文引用已逐条人工核实、内容真实，符合预期；发布时如实即可。
- 若 ICSE 拒稿：arXiv 预印本依然有效（确立优先权），可继续改投。

### F. 候选背书人（2026-08-18 按作者名单推荐）

> 资格确认方法：登录 arXiv → 打开对应论文摘要页 → 点击底部 "Which authors of this paper are endorsers?" → 名单里出现的人即有资格（该功能需登录）。以下按推荐顺序排列，一次联系 2–3 位即可。

**首选（按顺序）：**

| # | 候选 | 出处（arXiv） | 推荐理由 |
|---|---|---|---|
| 1 | **Pekka Abrahamsson**（坦佩雷大学教授） | Vibe Coding in Practice, 2512.11922 | 资深教授，cs.SE 极多产作者，背书资格几乎必然；论文主题（vibe coding + 技术债）与本文引用直接相关 |
| 2 | **Muhammad Waseem**（第一作者） | Vibe Coding in Practice, 2512.11922 | AI 辅助软件工程方向多产作者；第一作者联系最自然（"我引用了你的论文"） |
| 3 | **Zirui Tang**（第一作者） | Workspace-Bench 1.0, 2605.03596 | 主题契合度最高（agent 工作区）；可能偏年轻，若名单无资格则改问该篇资深合著者（22 位作者中 Liu Jiashuo、Kang Jihua 等可能为教授） |

**备选：**

| # | 候选 | 出处（arXiv） | 说明 |
|---|---|---|---|
| 4 | **Fan Jianping**（末位作者） | LemonHarness, 2606.24311 | 主题相关（工作区状态漂移）；资深学者（UNC Charlotte），资格大概率满足 |
| 5 | **Kai-Kristian Kemell** | Vibe Coding in Practice, 2512.11922 | 同组第三选择 |
| 6 | **Jules White / Marine Carpuat / Philip Resnik** | The Prompt Report, 2406.06608 | 极资深但偏 NLP 且非常忙，最后备选 |

**联系策略**：先发 Abrahamsson + Waseem（2 位）；3–5 个工作日无回应，再发 Tang / Fan；避免群发。邮件模板见聊天记录（arxiv 附录正文模板）。

> **此方法有成功先例且是官方推荐路径**：arXiv 官方帮助页明确写道 "If your article has citations to recent papers in arXiv, look for those papers in arXiv to find an endorser... Contact eligible endorsers and send them the endorsement request email"（[官方文档](https://info.arxiv.org/help/endorsement.html)）；Academia Stack Exchange 上 ["Should I endorse someone on arXiv who emailed me randomly?"](https://academia.stackexchange.com/questions/201716/should-i-endorse-someone-on-arxiv-who-emailed-me-randomly)（65 分高票答案）证实：资深作者**经常收到陌生人的背书请求**，社区共识是"请求真诚、工作认真就值得背书"。现实预期：著名大牛（如 Prompt Report 的资深作者）常忽略；中青年作者（Abrahamsson/Waseem 这类）响应率更高；部分背书人会要求先看论文——模板里附 ORCID/论文链接正是为此。3–5 位候选按序联系，多数情况 1–3 封邮件内成功。
