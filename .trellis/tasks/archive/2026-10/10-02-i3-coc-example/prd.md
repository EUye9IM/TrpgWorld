# I3: CoC 7e 规则系统与车卡阶段端到端示例

## Goal

实现 **CoC 7e 规则系统**的可运行子集与 **`examples/soup`**，并在 agent 上跑通 **车卡（character creation）阶段**的端到端冒烟，验证协议机制（channel 编排、上下文投影、git 步进/tag）在内联降级模式下可用。

> **范围收窄（用户决定）**：本任务**只做「车卡」阶段**；导入/扮演/战斗/结团等后续阶段留给后续任务。模组**不做精细编译**——`examples/soup` 用 scaffold 通用产物即可。

## Background（已确认事实）

- I1 协议文档就绪（`docs/`）；I2 通用工具与脚手架就绪（`tools/`、`templates/adventure/`，AC1.1–AC1.9 通过）。
- 旧实现 `src/systems/coc/`（dice/skills/character/rules/prompts）已删除，保留在 git 历史 `ed80ff4`，可作规则数据/车卡逻辑参考。
- 运行前提：`uv 0.7.12`、`python3`、`git`、`flock` 可用。
- 权威契约：`docs/tooling.md`、`docs/visibility.md`、`docs/directory.md`、`.trellis/spec/backend/protocol-contract.md`。

## 已定决策

- [x] **D-a 端到端验证方法：有界冒烟（内联降级）**，本任务只覆盖**车卡阶段**。
  - 由 agent 按 `examples/soup/AGENTS.md` + `flow/` 执行车卡：master 编排一个「车卡频道」，PL 生成角色并在频道内讨论/提交，master 收卡后交给 KP。
  - 产出真实 `channels/`、`roles/*/context.jsonl`、`git` 提交与 tag。
  - **AC5 就是此路径**（无 sub-agent，内联扮全部角色）。真·独立上下文不在本任务范围。
- [x] **D-b 大成功判定**：**大成功 = 骰值 1–5**（记为规则参数，可在 system 配置中调整）。
  - `check resolve` 的完整实现**推迟**到「扮演/战斗」阶段的后续任务（车卡阶段不需要判定结算）。本任务只在规则文档中固化大成功阈值等参数。
- [x] **D-c `flow/` 格式**：纯 markdown，`flow/flow.md`（阶段索引）+ `flow/phases/NN-slug.md`；本任务只定义 `01-character-creation.md`，其余阶段在索引中标记为「后续待补」。
- [x] **D-d 车卡实现**：由 flow「车卡」阶段驱动，agent 依 `systems/coc7e/rules/` + 现有 `dice` 工具完成；角色卡写 `roles/<id>/sheet.md`（人读）+ `sheet.json`（机读）；**不新增专用 character 工具**。
- [x] **D-e `examples/soup` 深度**：`scaffold` 通用产物（模组不做精细拆分/补秘密）。
- [x] **D-f 规则系统入包**：`scaffold` 新增 `--system <name>`：从 `systems/<name>/` 带入 `flow/`、`rules/`，并复制 `systems/<name>/tools/*` 到冒险 `tools/`；内嵌副本与源**逐字节一致**。

## Requirements

- **R1 `systems/coc7e/rules/character-creation.md`**：CoC 7e 车卡规则——属性生成（`3d6×5`×8）、派生值（HP/MP/SAN/DB/Build/MOV/幸运）、职业与技能点分配、背景；含大成功 `1–5` 等参数说明。
- **R2 `systems/coc7e/flow/`**：`flow.md` 阶段索引 + `phases/01-character-creation.md`（车卡：目标/进入条件/参与角色/适用规则/退出条件/产出）。
- **R3 `scaffold --system`**：带入 system 的 `flow/`、`rules/`，复制 `systems/<name>/tools/*` 到冒险 `tools/`。
- **R4 `examples/soup/`**：`scaffold new --module modules/soup.md --system coc7e` 产物（含 coc7e flow/rules）。
- **R5 车卡冒烟**：内联降级模式下完成车卡（含车卡 channel、PL 生成角色、提交 KP），产出真实工件与 git 历史。
- **R6 契约一致**：产物目录树与 `docs/directory.md` 一致；`scaffold --system` 行为与 `docs/tooling.md` 一致。

## Acceptance Criteria

- [ ] **AC2（车卡部分）** 读 `examples/soup/AGENTS.md` 后，agent 能完成车卡阶段（生成角色、写 `sheet.md`/`sheet.json`、提交 KP），编排不依赖框架硬编码代码。
- [ ] **AC4** 冒烟产生 `phase/character-creation` 等 tag；`git checkout` 到任一提交后可继续。
- [ ] **AC5** 整个冒烟在**内联降级模式**（无 sub-agent）下跑通。
- [ ] **AC6** `systems/coc7e/` + `examples/soup/` 与 `docs/` 契约一致（目录树、flow 阶段、`scaffold --system` 行为）。
- [ ] **AC7** 车卡 channel 的工件隔离成立：未参与该 channel 的角色，其 `context.jsonl` 不含车卡频道内容（`context build` 按 participants 过滤）。

> **延后（不在 I3）**：AC2 的「→结团」、AC3（秘密场景/秘密骰隔离，已在 I2 做工具级验证）、导入/扮演/战斗/理智/结团阶段、`check resolve`、独立上下文的角色子代理。

## Out of Scope

- 导入/扮演/战斗/理智/结团阶段；`check resolve` 完整实现。
- 精细模组编译（毒湯专属秘密、倒计时 hooks）。
- 独立上下文角色子代理 / 编排驱动 / Pi·dsh 适配（后续任务）。
- 人类担任角色、replay。

## Open Questions（阻塞规划）

（无）
