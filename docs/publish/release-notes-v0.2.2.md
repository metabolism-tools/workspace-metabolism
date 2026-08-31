# workspace-metabolism v0.2.2 — 发布说明草稿

> 上传 PyPI 需要 token。本机没有 pypi-token.txt，发布时按文末步骤操作。

## 本次变更（自 v0.2.1）

- **MCP 工具定义全面重写**（TDQS 规范）：5 个工具（`wm_audit` / `wm_health` /
  `wm_explain` / `wm_verify` / `wm_clean`）的描述现在完整说明"做什么、返回什么、
  何时用、何时不用"，所有参数都有说明——Glama 质量分 70% 取决于工具定义质量，
  评分已在审核队列中
- **新增 `mcp.json`**：Claude Code / Cursor 等客户端可直接发现 stdio 服务器
- **新增 `Dockerfile` + `.dockerignore`**：容器化构建与检查（Glama 评估用），
  也可用于自托管
- **README 徽章**：PyPI 版本 / Python 版本 / CI / License / 零依赖

## 发布步骤

```powershell
# 1. 把 pyproject.toml 的 version 改为 0.2.2
# 2. 构建
python -m pip install --upgrade build twine
python -m build
# 3. 上传（需要 PyPI token，即 .gitignore 里的 pypi-token.txt）
twine upload dist/*
# 4. 打 GitHub release
git tag v0.2.2
git push origin v0.2.2
```

## 验证

- `pip install workspace-metabolism==0.2.2` 可安装
- `wm mcp` 的 `tools/list` 返回新描述（本机已实测 80+88 测试全绿）
