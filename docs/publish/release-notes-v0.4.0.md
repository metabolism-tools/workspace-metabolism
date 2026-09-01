# workspace-metabolism v0.4.0 — AI 治理即代码

## 本次变更（自 v0.3.1）

### 1. `wm gate` —— MCP 治理代理（核心新功能）

把任意 MCP stdio 服务器包进治理层：每个 `tools/call` 先过策略裁决，**拒绝的调用
永远不会到达目标服务器**，所有决策（allow/deny）带 `decision_id` 写入哈希链
journal。

```bash
wm gate --target "python -m my_mcp_server"
```

- 工具名 → AI 动作映射：`ai_governance.tool_patterns`（glob，如 `"fs_*": "write"`），
  未匹配默认 `execute`
- 调用参数带 `"preview": true` 可满足 `requires_preview`
- 路径类参数启发式提取（path/file/dir/uri 等）
- **定位声明**：这是治理与审计层，**不是沙箱**——管自觉的 agent，管不了绕过
  代理直连的恶意 agent

### 2. `decision_id` 执行链（intent → decision → execution）

- `wm govern` 返回 `decision_id` 并写入 journal
- `wm clean` / `wm rollback` / `wm slim` 接受 `--decision-id`（CLI + MCP
  `wm_clean` 参数）
- journal 现在能完整回答："agent 声称做什么 → 策略裁决什么 → 实际执行了什么"，
  每个环节都带策略哈希、可验证、可回滚

### 3. 配套

- schema：`ai_governance.tool_patterns` 字段
- 示例 policy 更新（`wm_*`/`fs_*`/`shell_*` 映射示例）
- README：AI governance 章节重写（gate 用法、preview 工作流、decision_id 链、
  沙箱边界）
- 测试 115 个全过（gate 全流程：放行/拦截/preview/未知工具/journal 链 +
  decision_id 闭环）

## 用法速览

```bash
pip install --upgrade workspace-metabolism
wm init                          # 生成策略文件
# metabolism.json 里配 ai_governance.tool_patterns + actions
wm govern write --path src/main.py          # 先问策略（决策入 journal）
wm gate --target "python -m my_server"      # 或直接包在代理后面强制执行
wm clean --grades G4 --yes --decision-id govern-20260901-...   # 执行链闭环
```

## 发布

```powershell
python -m build
twine upload dist/workspace_metabolism-0.4.0-*
git tag v0.4.0 && git push origin v0.4.0
```
