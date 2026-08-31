# workspace-metabolism v0.2.3 — 发布说明

## 本次变更（自 v0.2.2）

- **MCP 新增 `wm_init` 和 `wm_rollback` 工具**（Glama Server Coherence 评审点名的两个缺口）：
  - `wm_init`：像 `git init` 一样为工作区生成 `metabolism.json` 策略文件（安全默认：源码/文档/密钥/dotfiles 永不清除）
  - `wm_rollback`：把之前 `wm_clean` 回收的条目按 SHA-256 校验后还原回原位（dry-run 默认）
  - 策略文件调用时自动发现：`wm_init` 之后同一 MCP 会话内 `wm_audit` 立即可用
- 两个新工具均按 TDQS 规范编写描述（Glama 实测：`wm_rollback` 4.9/5、`wm_init` 4.7/5）
- README 更新 Agents 章节

## Glama 影响

- 服务器评分 17 → 67 → **92（Quality A）**，评估基于 GitHub 源码，已生效
- PyPI 0.2.2 → 0.2.3：让 pip 用户也拿到新工具

## 发布步骤

```powershell
python -m build
twine upload dist/workspace_metabolism-0.2.3-*   # 需要 pypi-token.txt
git tag v0.2.3 && git push origin v0.2.3
```
