# I5: 协议 core 缺陷修复（mask / compact / 投影 / 秘密骰）

## Goal

修复已确认的协议 core 缺陷，使 `tools/` 的投影与随机在其上构建的插件（I4）之前达到正确、安全、可预期。

## Background（证据）

由 I4 批判性审查报告发现，已核对源码：

| # | 缺陷 | 证据 | 判定 |
|---|---|---|---|
| **F1** | mask **fail-open**：`world/visibility.json` 缺失/非法时返回 `{"default": "public"}` | `tools/_lib.py` `read_visibility` | **安全缺陷**（真） |
| **F2** | `compact ↔ build` **重放膨胀**：`context build` 对参与频道**始终拼接全量 transcript**；`compact` 只截角色文件 → 压缩后被 build 重放 | `tools/context.py` `build_messages` / `load_channels` | 正确性/成本缺陷（真） |
| **F3** | `context build` stdout 输出 `worldPaths` | `tools/context.py` `cmd_build`（只含**可见**路径） | **卫生问题**（非泄漏，审查者高估） |
| **F4** | 可见性靠逐工具的 `--secret` 特例，不通用 | `tools/dice.py` 无可见性参数 | **设计缺陷**（应改为通用原则） |

## 范围

- **本任务**：修复 F1–F4（含必要文档同步）。
- **不属于**：插件（I4）、机制化隔离、`check resolve` 实现。

## 已定方向（待评审细节）

- **F1 fail-closed**：缺/非法 `visibility.json` 时，`default = 空受众`（任何角色都看不到 world 状态），并输出显式警告；不得退化为全公开。
- **F2 频道状态驱动投影**：`context build` 对 **open** 频道用全量 transcript，对 **closed** 频道只用其 `outcome` 摘要 → 停止重放膨胀；`compact` 职责收敛为「角色私有记忆摘要」。
- **F3 卫生**：从默认 stdout 移除 `worldPaths`，改由 `--debug` 输出。
- **F4 工具结果可见性（通用原则，替代 `--secret` 特例）**：采用 **「工具不管理可见性」**——结果只回调用者 + 写系统审计 `log/`（永不投影）；要可见必须由 master/角色**显式写入** `channels/`/`roles/`/`world/`，**可见性 = 写入位置**。秘密骰 = 不写入公共频道。本任务只**文档化**该原则，并断言 `context build` 不以 `log/` 为来源。

## Requirements

- **R1** F1 fail-closed，并有测试覆盖「缺文件时无人可见」。
- **R2** F2 投影按频道状态取 transcript/outcome，并保证 `compact` 后 build **不重放**。
- **R3** F3 `--debug` 才输出 `worldPaths`。
- **R4 工具结果可见性通用原则**：文档化「工具不管理可见性 / 位置即权限」；**不引入逐工具的 `--secret` 参数**；保证 `log/` 不被任何投影读取（`context build` 的来源仅 personas/roles、`world/`（masked）、`channels/`（participants））。
- **R5** 文档同步：`docs/visibility.md`（fail-closed 语义、频道状态驱动投影、秘密骰受限位置）、`docs/tooling.md`（dice `--secret`、context `--debug`）。
- **R6** 回归：I2/I3 既有行为（非缺陷部分）、内嵌工具逐字节一致。

## Acceptance Criteria

- [ ] **AC1** 删除 `world/visibility.json` 后，`context build --role <r>` 的投影**不含**任何 world 状态；`state mask` 显示全部隐藏；有警告输出。
- [ ] **AC2** 关闭频道（`status: closed` + `outcome`）后，`context build` 的该频道内容为 outcome 摘要而非全量 transcript；多次 build 体积不随已关闭频道线性增长。
- [ ] **AC3** `context build` 默认 stdout 不含 `worldPaths`；`--debug` 时含。
- [ ] **AC4** `docs/` 含「工具不管理可见性 / 位置即权限」原则；断言 `context build` 不读取 `log/` 作为投影来源（秘密骰不外泄由「不写入公共频道」保证）。
- [ ] **AC5** `docs/` 同步，`cmp` 内嵌工具逐字节一致。

## Out of Scope

- I4 插件、机制化隔离、`check resolve`。
