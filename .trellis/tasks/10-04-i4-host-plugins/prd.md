# I4: 宿主插件——角色运行时契约与 Pi/dsh 适配

## Goal

1. 产出**角色运行时契约 v2** 并写入 `docs/capabilities.md`：**三层隔离模型** + 能力表 C1–C17，明确标注**已实现 / 预留**。
2. 提供**最小 Pi 插件**参考实现：让 master 能以独立上下文运行角色；**隔离先用 prompt 约束**。
3. **预留（本任务不实现）**：机制化隔离（注入面关闭 + 金丝雀测试）、C11–C17、dsh 适配。

## Background

- 批判性审查报告：`.trellis/tasks/10-04-i4-host-plugins/research/plugin-capability-review.md`（结论：方向对，但 C9a「工具限制就够」是虚假安全感；真正泄漏面是宿主自动注入）。
- 已发布代码存在 4 个已确认缺陷，由**单独的 bugfix 任务**修复（不在本任务）。

## 决策（用户确认）

- **D1 契约 v2 先写不实现**：C11–C17（模型路由/超时/成本/递归上限/受限读取/频道绑定/金丝雀）作为**预留条款**写入文档，不落地。
- **D2 隔离用「prompt 约束 + 不给 fs/bash」**：插件**整段替换** system prompt、**只授予 `trpg_dice`**（无 fs/bash/state/context/step）、不开 `AGENTS.md` 注入。因为角色没有文件工具，它**只能看到插件注入的内容** → 可见性由**插件/协议侧自己管理**（注入什么由我们决定）。机制化金丝雀验收与干净配置目录延后。
- **D3 已确认缺陷另修**：`flag fail-open mask` / `compact↔build 重放膨胀` / `context build 泄漏 worldPaths` / `dice 无 secret 模式` → 独立 bugfix 任务。

## Requirements

- **R1 契约 v2 文档**：`docs/capabilities.md` 升级为「角色运行时契约」，含三层隔离模型（上下文注入面 / 工具门控 / 会话边界）、C1–C17 能力表、Pi/dsh 原语映射、降级矩阵、已知边界（L10 模型先验无解），并标注实现状态。
- **R2 最小 Pi 插件**：`.pi/extensions/trpg/index.ts` + `.pi/agents/trpg-role.md`：
  - `trpg_role({ role_id, channel_id, instruction? })`：调 `context build` 取该角色投影 → `pi -p --no-session`（prompt 约束隔离）→ 返回角色回复。
  - `trpg_dice({ expr, seed? })`：角色唯一被允许的能力（转调 `tools/dice.py`）。
- **R3 一致性/回归**：插件不修改协议 CLI；`context build` 仍为投影唯一来源；插件不解析目录结构（仅调用 CLI）。
- **R4 预留标注**：文档明确 v2 中未实现项，避免虚假保证。

## Acceptance Criteria

- [ ] **AC1** `docs/capabilities.md` 含契约 v2 全部内容，且逐条标注「已实现 / 预留」，与审查报告结论不矛盾。
- [ ] **AC2** Pi 插件可加载：`pi -e .pi/extensions/trpg/index.ts` 能注册 `trpg_role` / `trpg_dice` 且 `--help` 可查。
- [ ] **AC3** `trpg_role` 调用了 `context build`，注入内容来自该角色投影（fake agent 可断言）。
- [ ] **AC4** 插件对协议 core 无副作用；`git status` 仅新增插件与文档。
- [ ] **AC5** 文档声明「prompt 约束隔离为**临时**手段」，并列出机制化隔离的预留项。

## Out of Scope

- 机制化三层隔离落地、金丝雀测试（C17）、C11–C17 实现。
- dsh 适配。
- 已确认缺陷修复（另开 bugfix 任务）。
- 并发（C5）、人类暂停（C7）、沙箱兜底（C9b）。
