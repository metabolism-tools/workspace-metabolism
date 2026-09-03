# workspace-metabolism v0.5.0 — 引导式治理

## 本次变更（自 v0.4.0）

### 1. `wm doctor --residue` —— 引导式首次运行（本版主打）

新手不再需要从零手写 policy：

```bash
wm doctor --residue                  # 只读：列出 policy 未治理的常见代理残留
wm doctor --residue --apply-policy   # 采纳建议条目（无 policy 时自动创建）
```

- 内置 9 类残留知识库（`.cursor` / `.claude` / `node_modules/.cache` /
  `__pycache__` / `.pytest_cache` / `.vite` / `.next/cache` / `.turbo` / `*.log`）
- 每个命中给出**可直接采纳的 policy 条目**（G4 auto 30d 缓存 / G3 approve 60d 保守类）
- 已治理/空目录/.git 自动跳过；`**/x` 与 `x` 条目去重；合并前全量校验
- **哲学不变**：只做建议，用户确认后才进 policy——工具依然从不未经 policy 动手

### 2. 边界与叙事收尾

- README 重构为"痛苦 → 30 秒上手 → 诚实边界"顺序；状态行更新为事实
  （v0.5.0、Glama A、已发布 PyPI；保留"无大规模生产部署"的诚实声明）
- `wm gate` 启动打印醒目实验性横幅；`--help` 首屏边界声明（观测层非沙箱）

## 影响

- 120 测试全过（+5 残留扫描/策略追加回归测试）
- Glama 92 A 档不受影响（工具面未变；doctor 是 CLI 能力）

## 发布

```powershell
python -m build
twine upload dist/workspace_metabolism-0.5.0-*
git tag v0.5.0 && git push origin v0.5.0
```
