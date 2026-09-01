# workspace-metabolism v0.3.1 — 发布说明

## 本次变更（自 v0.3.0，三个修复）

1. **slim 策略匹配精确化**（`1055e90`）：路径段精确匹配 + 最长匹配优先——泛条目
   （如 `data`）不再遮蔽具体条目（如 `data/app.db`）的 `db_slim` 配置；同时修掉
   了 `p in rel` 任意子串误匹配的问题
2. **registry 自动发现容错**（`dc5923c`）：策略目录不可读时 `verify`/`slim`
   不再崩溃
3. **全策略引擎的最具体条目优先**（`56f420c`）：`wm explain` 之前返回列表第一个
   匹配条目（泛条目遮蔽具体条目，实测复现 G2/never 遮蔽 G4/auto）；`wm clean`
   的规划阶段现在会拦截"泛 G4 目录候选包含更具体 never 子路径"的情况，避免把
   策略保护的文件扫进回收站。新增 2 个回归测试，共 106 个测试全过

## 影响

- CLI / MCP 行为：`explain` 的营养标签现在永远指向最具体的策略条目；clean 规划
  更保守（宁可拦截，不碰 protected 路径）
- Glama 同步后重评不受影响（修复不改变工具面）

## 发布

```powershell
python -m build
twine upload dist/workspace_metabolism-0.3.1-*
git tag v0.3.1 && git push origin v0.3.1
```
